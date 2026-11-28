"""ClearDay web app - stdlib only, runs anywhere incl. a Fly Sprite (port 8080).
Persistent memory: follow-ups are stored in memory.json on the Sprite's
persistent disk, so the agent remembers across sleeps and follows up.
Connector use (Hacksgiving rule): on a Sprite, set CLEARDAY_MODEL_URL to a
Sprites Connector gateway URL (Anthropic / OpenRouter) and/or receive mail
via the AgentMail connector inbox and forward it to POST /inbox.
"""
import json, os, html, http.client, smtplib, urllib.request, threading
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from clearday import transform, draft_reply, connector_proof, heuristic_transform, detect_lang, translate_reply
from render import render_page, render_form, render_inbox, render_reply_sent, render_reply_draft, render_why, render_connected, render_bulk, render_followups_page, S

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
MP = "http://127.0.0.1:8025/mailpit"  # Mailpit on the same Sprite (webroot /mailpit)
SEED_LOCK = threading.Lock()

def mp_api(path):
    req = urllib.request.Request(MP + path, headers={"User-Agent": "ClearDay/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def mp_seed_if_missing():
    try:
        msgs, up = mp_messages()
        if up and not any(m.get("Subject") == "Board meeting moved" for m in msgs):
            mp_seed()
            return True
    except Exception:
        pass
    return False

def mp_seed():
    """Send the sample board email into the Mailpit inbox by real SMTP."""
    text = open(os.path.join(os.path.dirname(__file__), "sample_email.txt")).read()
    m = EmailMessage()
    m["From"] = "Maria Lopez <maria.lopez@example.org>"
    m["To"] = "you@clearday.demo"
    m["Subject"] = "Board meeting moved"
    m.set_content(text)
    paras = "".join(
        f"<p style='margin:0 0 2px 0;'>{html.escape(line) if line.strip() else '&nbsp;'}</p>"
        for line in text.splitlines())
    m.add_alternative(
        "<html><body style='font-family:Arial,sans-serif;font-size:13px;"
        f"color:#666;line-height:1.35;'>{paras}</body></html>", subtype="html")
    s = smtplib.SMTP("127.0.0.1", 1025, timeout=10)
    s.send_message(m)
    s.quit()

def mp_fresh():
    """Wipe the box and deliver ONE brand-new Maria email, right now.
    Returns the new message ID (or '')."""
    import time
    with SEED_LOCK:
        try:
            req = urllib.request.Request(MP + "/api/v1/messages", method="DELETE")
            urllib.request.urlopen(req, timeout=10).read()
        except Exception:
            pass
        try:
            mp_seed()
        except Exception:
            return ""
        for _ in range(12):
            msgs, up = mp_messages()
            for m in msgs:
                if m.get("Subject") == "Board meeting moved":
                    return m.get("ID", "")
            time.sleep(0.25)
    return ""

def mp_messages():
    try:
        data = mp_api("/api/v1/messages?limit=20")
        return data.get("messages", []), True
    except Exception:
        return [], False

MEM_LOCK = threading.Lock()

def _read_memory_file(path):
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

def load_memory():
    """Follow-ups survive a crash (technical lens, Nov 28): save_memory
    writes a temp file and renames it over the old one, and keeps the last
    good state as .bak - a torn main file falls back to the backup
    instead of silently emptying the list."""
    with MEM_LOCK:
        try:
            return _read_memory_file(MEMORY_FILE)
        except Exception:
            try:
                return _read_memory_file(MEMORY_FILE + ".bak")
            except Exception:
                return []

def save_memory(items):
    with MEM_LOCK:
        tmp = MEMORY_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(items, f, indent=2)
        os.replace(tmp, MEMORY_FILE)
        try:
            with open(MEMORY_FILE + ".bak", "w") as f:
                json.dump(items, f, indent=2)
        except Exception:
            pass

def remember(items, what, sender, lang, mid="", subject="", addr="", force=False):
    """The ONE follow-up writer (simplicity lens, Nov 28): every door -
    paste, inbox, bulk - saves through here, in ONE record shape.
    Dedupe: a row with a message id is keyed by that id (skipped when
    already waiting, unless force - the GET inbox door's documented
    behavior); a row without one is keyed by sender + subject, and
    re-clearing refreshes its one row instead of stacking a copy.
    Returns (items, added)."""
    row = {"what": what, "sender": sender, "lang": lang,
           "mid": mid, "subject": subject, "addr": addr}
    if mid:
        if not force and any(i.get("mid") == mid for i in items):
            return items[-20:], False
        items.append(row)
        return items[-20:], True
    key = ((sender or "").strip().lower(), (subject or "").strip().lower())
    items = [i for i in items if i.get("mid") or
             ((i.get("sender") or "").strip().lower(), (i.get("subject") or "").strip().lower()) != key]
    items.append(row)
    return items[-20:], True



API_LOCK = threading.Lock()
API_CALLS = []

def api_rate_ok():
    """Public API guard: at most 60 clears a minute (each one can spend a
    model call). The model itself is also capped demo-wide by a semaphore
    in clearday.py - together they keep a script from stalling the demo."""
    import time
    now = time.time()
    with API_LOCK:
        API_CALLS[:] = [t for t in API_CALLS if now - t < 60]
        if len(API_CALLS) >= 60:
            return False
        API_CALLS.append(now)
        return True

class H(BaseHTTPRequestHandler):
    def _send(self, html, code=200):
        b = html.encode(); self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _clear_one(self, mid, lang, dedupe=False):
        """Clear ONE inbox message into a clear page + a follow-up.
        The GET door keeps the original behavior; the POST door and bulk
        dedupe by message id, so the same email never stacks follow-ups."""
        try:
            msg = mp_api("/api/v1/message/" + mid)
            frm = msg.get("From") or {}
            sender = frm.get("Name") or frm.get("Address") or ""
            result = transform(msg.get("Text") or "", sender, msg.get("Subject") or "", lang)
            result["_text"] = msg.get("Text") or ""
            result["_mid"] = mid
            result["_addr"] = frm.get("Address") or ""
            result["_subject"] = msg.get("Subject") or ""
            items, added = remember(load_memory(), result["what"], result["sender"],
                                    result.get("lang", lang), mid=mid,
                                    subject=msg.get("Subject") or "",
                                    addr=frm.get("Address") or "", force=not dedupe)
            if added:
                save_memory(items)
            return render_page(result)
        except Exception:
            msgs, up = mp_messages()
            return render_inbox(msgs, lang, down=True)
    def _do_bulk(self, lang):
        """Clear up to 10 waiting inbox emails at once. Snapshots the box
        first; skips my own replies; follow-ups dedupe by message id; the
        page reports cleared / skipped / failed counts - never invents one."""
        try:
            data = mp_api("/api/v1/messages?limit=50")
            msgs = data.get("messages", [])
        except Exception:
            return render_bulk(lang, up=False)
        own = 0
        eligible = []
        for m in msgs:
            addr = (m.get("From") or {}).get("Address") or ""
            if addr == "you@clearday.demo":
                own += 1
            else:
                eligible.append(m)
        batch = eligible[:10]
        remaining = len(eligible) - len(batch)
        items = load_memory()
        have = {i.get("mid") for i in items}
        results, dupe, failed = [], 0, 0
        for m in batch:
            mid = m.get("ID") or ""
            try:
                msg = mp_api("/api/v1/message/" + mid)
                frm = msg.get("From") or {}
                sender = frm.get("Name") or frm.get("Address") or ""
                r = transform(msg.get("Text") or "", sender, msg.get("Subject") or "", lang)
                results.append({"sender": sender, "subject": msg.get("Subject") or "",
                                "what": r.get("what", ""), "actions": r.get("actions", []),
                                "dates_numbers": r.get("dates_numbers", []),
                                "dates_labeled": r.get("dates_labeled", []), "mid": mid})
                items, added = remember(items, r["what"], r["sender"], r.get("lang", lang),
                                        mid=mid, subject=msg.get("Subject") or "",
                                        addr=frm.get("Address") or "")
                if added:
                    have.add(mid)
                else:
                    dupe += 1
            except Exception:
                failed += 1
        save_memory(items[-20:])
        counts = {"own": own, "dupe": dupe, "failed": failed, "remaining": remaining}
        return render_bulk(lang, results=results, counts=counts)
    def _proxy_mailpit(self):
        """Pass /mailpit* through to Mailpit on localhost - its real UI, unmodified.
        READ-ONLY for the public: the demo inbox can be looked at, never written
        to or emptied through this door (red-team finding, Nov 24)."""
        if self.command in ("POST", "PUT", "DELETE", "PATCH"):
            self._send("<html><body style='font-family:Arial;font-size:21px'>This demo inbox is read-only. To try sending, use ClearDay's own Inbox page.</body></html>", 403)
            return
        if (self.headers.get("Upgrade") or "").lower() == "websocket":
            self._send("<html><body>Live updates are off in this demo view. Refresh to see new mail.</body></html>", 501)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except Exception:
            length = 0
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "connection", "content-length")}
        conn = http.client.HTTPConnection("127.0.0.1", 8025, timeout=30)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ("connection", "transfer-encoding", "content-length"):
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self._send("<html><body style='font-family:Arial;font-size:21px'>Mailpit inbox is resting. ClearDay still works - use the paste form.</body></html>", 502)
        finally:
            conn.close()

    def do_GET(self):
        if self.path.startswith("/reply"):
            self._send("Not found", 404)
            return
        if self.path.startswith("/connected"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            from datetime import datetime, timezone
            try:
                from zoneinfo import ZoneInfo
                checked = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%A, %B %d, %Y - %I:%M %p PT")
            except Exception:
                checked = datetime.now(timezone.utc).strftime("%A, %B %d, %Y - %I:%M %p UTC")
            self._send(render_connected(connector_proof(), lang, checked))
        elif self.path.startswith("/why"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            self._send(render_why(lang))
        elif self.path.startswith("/api/followups"):
            items = load_memory()
            safe = [{"what": i.get("what", ""), "sender": i.get("sender", ""),
                     "lang": i.get("lang", "en"), "mid": i.get("mid", "")} for i in items]
            self._send_json({"count": len(safe), "followups": safe})
        elif self.path.startswith("/api"):
            if urlparse(self.path).path in ("/api", "/api/"):
                self._send_json({
                    "name": "ClearDay API", "version": 1,
                    "endpoints": {
                        "POST /api/clear": "Send JSON {sender, subject, text, lang} - get the clear page back as JSON. Dates and numbers are copied exactly from the text, never invented. The API saves nothing.",
                        "GET /api/followups": "The follow-ups the agent is remembering (names only - never email addresses).",
                        "GET /bulk": "The bulk page: clear the whole demo inbox at once.",
                        "POST /bulk/clear": "Run the bulk clear and get the combined page.",
                    },
                    "example": "curl -X POST https://clearday-bnjwz.sprites.app/api/clear -H 'Content-Type: application/json' -d '{\"text\": \"The meeting moved to Tuesday November 24 at 5:15 PM. Please reply to confirm.\", \"sender\": \"Maria Lopez\", \"subject\": \"Board meeting moved\", \"lang\": \"en\"}'",
                })
            else:
                self._send_json({"error": "Not found"}, 404)
        elif self.path.startswith("/bulk"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            try:
                data = mp_api("/api/v1/messages?limit=50")
                msgs = data.get("messages", [])
                waiting = sum(1 for m in msgs if ((m.get("From") or {}).get("Address") or "") != "you@clearday.demo")
                self._send(render_bulk(lang, waiting=waiting))
            except Exception:
                self._send(render_bulk(lang, up=False))
        elif self.path.startswith("/mailpit"):
            self._proxy_mailpit()
        elif self.path.startswith("/inbox/clear"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            mid = (q.get("id") or [""])[0]
            self._send(self._clear_one(mid, lang))
        elif self.path.startswith("/inbox"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            msgs, up = mp_messages()
            if up and not msgs:
                with SEED_LOCK:
                    msgs, up = mp_messages()  # re-check inside the lock (no double seed)
                    if up and not msgs:
                        try:
                            mp_seed()
                            msgs, up = mp_messages()
                        except Exception:
                            pass
            self._send(render_inbox(msgs, lang, down=not up))
        elif self.path.startswith("/sample"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            try:
                text = open(os.path.join(os.path.dirname(__file__), "sample_email.txt")).read()
            except Exception:
                text = ""
            page = transform(text, "Maria Lopez", "Board meeting moved", lang)
            page["_text"] = text; page["_mid"] = ""; page["_addr"] = ""; page["_subject"] = "Board meeting moved"
            _items, _added = remember(load_memory(), page["what"], page["sender"], page.get("lang", lang), subject="Board meeting moved")
            save_memory(_items)
            self._send(render_page(page))
        elif self.path.startswith("/followups"):
            items = load_memory()
            def row(i):
                s = S(i.get("lang", "en"))
                btn = ""
                if i.get("mid"):
                    btn = (f" <form method='post' action='/reply' style='display:inline'>"
                           f"<input type='hidden' name='mid' value='{html.escape(str(i['mid']))}'>"
                           f"<input type='hidden' name='lang' value='{html.escape(str(i.get('lang', 'en')))}'>"
                           f"<button type='submit'>{s['followups_reply']}</button></form>")
                return f"<div style='font-size:22px;padding:10px;'>&#9679; {html.escape(str(i['what']))} — {s['nudge']} {html.escape(str(i['sender']))}{btn}</div>"
            en = S("en")
            rows = "".join(row(i) for i in items) or f"<div style='font-size:22px;padding:10px;'>{en['no_followups']}</div>"
            self._send(render_followups_page(rows))
        elif "sample=1" in self.path:
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            # Parallel workflow (Jose Luis's spec, Nov 24): loading the sample
            # ALSO puts the same email into the Mailpit inbox - if it is not
            # already there. The form fills at the same time, below.
            mp_seed_if_missing()
            try:
                text = open(os.path.join(os.path.dirname(__file__), "sample_email.txt")).read()
            except Exception:
                text = ""
            self._send(render_form("", lang, {"sender": "Maria Lopez", "subject": "Board meeting moved", "text": text}))
        else:
            mp_seed_if_missing()
            self._send(render_form())
    def _other_method(self):
        if self.path.startswith("/mailpit"):
            self._proxy_mailpit()  # its guard answers 403 for writes
        else:
            self._send("Not found", 404)
    do_DELETE = _other_method
    do_PUT = _other_method
    do_PATCH = _other_method

    def do_POST(self):
        if self.path.startswith("/mailpit"):
            self._proxy_mailpit()
            return
        if self.path.startswith("/reply/translate"):
            length = int(self.headers.get("Content-Length") or 0)
            f = parse_qs(self.rfile.read(length).decode(errors="replace")) if length else {}
            def one0(k):
                return (f.get(k) or [""])[0]
            lang = one0("lang") or "en"
            if lang not in ("en", "es", "vi"):
                lang = "en"
            mid, to, rsubject, body, orig = one0("mid"), one0("to"), one0("subject"), one0("body"), one0("orig")
            if orig not in ("en", "es", "vi"):
                orig = ""
            translated, ok = translate_reply(body, orig) if orig else (None, False)
            if ok:
                self._send(render_reply_draft(to, rsubject, translated, lang, mid=mid, addr=to, orig=orig,
                                              mode="translated", source="model", orig_body=body,
                                              model_name=os.environ.get("CLEARDAY_MODEL", "")))
            else:
                self._send(render_reply_draft(to, rsubject, body, lang, mid=mid, addr=to, orig=orig, mode="failed"))
            return
        if self.path.startswith("/reply") and not self.path.startswith("/reply/send"):
            length = int(self.headers.get("Content-Length") or 0)
            if length > 60000:
                self._send(render_form("<p class='big'><b>That message is too long. Please paste a shorter one.</b></p>"))
                return
            f = parse_qs(self.rfile.read(length).decode(errors="replace")) if length else {}
            def one(k):
                return (f.get(k) or [""])[0]
            lang = one("lang") or "en"
            if lang not in ("en", "es", "vi"):
                lang = "en"
            mid, sender, subject, text = one("mid"), one("sender"), one("subject"), one("text")
            addr = ""
            if mid:
                try:
                    msg = mp_api("/api/v1/message/" + mid)
                    frm = msg.get("From") or {}
                    sender = frm.get("Name") or frm.get("Address") or sender
                    addr = frm.get("Address") or ""
                    subject = msg.get("Subject") or subject
                    text = msg.get("Text") or text
                except Exception:
                    pass
            found = False
            if not addr:
                # Paste path: the form gave a NAME, not an address. Jose Luis's
                # rule (Nov 24): if this sender's REAL address is sitting in
                # the demo inbox, the draft page gets a Send button too - and
                # says where the address came from. No match, no button.
                # Match order: exact subject, then sender name, then - only
                # when the paste gave NO name and NO subject at all - the
                # newest real email in the box (the demo's Maria email).
                try:
                    msgs3, up3 = mp_messages()
                    if up3:
                        def usable(m3):
                            a3 = (m3.get("From") or {}).get("Address") or ""
                            return bool(a3) and a3 != "you@clearday.demo"
                        pick = None
                        for m3 in msgs3:
                            if usable(m3) and (m3.get("Subject") or "") == subject and subject:
                                pick = m3; break
                        if pick is None and sender.strip():
                            for m3 in msgs3:
                                nm3 = (m3.get("From") or {}).get("Name") or ""
                                if usable(m3) and nm3.strip().lower() == sender.strip().lower():
                                    pick = m3; break
                        if pick is None and not sender.strip() and not subject.strip():
                            for m3 in msgs3:
                                if usable(m3):
                                    pick = m3; break
                        if pick is not None:
                            mid = pick.get("ID") or mid
                            addr = (pick.get("From") or {}).get("Address") or ""
                            sender = (pick.get("From") or {}).get("Name") or sender
                            if not subject.strip():
                                subject = pick.get("Subject") or subject
                            if not text.strip():
                                try:
                                    text = mp_api("/api/v1/message/" + mid).get("Text") or text
                                except Exception:
                                    pass
                            found = True
                except Exception:
                    pass
            dates = heuristic_transform(text, sender, subject, lang)["dates_numbers"] if text else []
            draft, dsrc = draft_reply(text, sender, subject, lang, dates)
            rsubject = subject if subject.lower().startswith("re:") else "Re: " + subject
            orig = detect_lang(text) if text else lang
            # DRAFT ONLY. Nothing is sent here - the reader sees the draft
            # first and sends it with a separate, explicit press (/reply/send).
            self._send(render_reply_draft(addr or sender, rsubject, draft, lang, mid=mid, addr=addr,
                                          source=dsrc, model_name=os.environ.get("CLEARDAY_MODEL", "") if dsrc == "model" else "",
                                          found=found, orig=orig))
            return
        if self.path.startswith("/reply/send"):
            length = int(self.headers.get("Content-Length") or 0)
            f = parse_qs(self.rfile.read(length).decode(errors="replace")) if length else {}
            def one2(k):
                return (f.get(k) or [""])[0]
            lang = one2("lang") or "en"
            if lang not in ("en", "es", "vi"):
                lang = "en"
            mid, to, rsubject, draft = one2("mid"), one2("to"), one2("subject"), one2("body")
            orig = one2("orig")
            if orig not in ("en", "es", "vi"):
                orig = ""
            already = one2("translated") == "1"
            notranslate = one2("notranslate") == "1"
            sent = False
            send_body, wrote, did_trans = draft, "", False
            if mid and to and draft:
                try:
                    # Gate: the To must be the real sender of that inbox message.
                    msg = mp_api("/api/v1/message/" + mid)
                    real_addr = (msg.get("From") or {}).get("Address") or ""
                    if real_addr and real_addr == to:
                        if orig and orig != lang and not already and not notranslate:
                            # The round trip: his words go back in the language
                            # the email arrived in. If the translation does not
                            # come back clean, NOTHING is sent - he chooses.
                            t_body, t_ok = translate_reply(draft, orig)
                            if not t_ok:
                                self._send(render_reply_draft(to, rsubject, draft, lang, mid=mid, addr=to,
                                                              orig=orig, mode="failed"))
                                return
                            send_body, wrote, did_trans = t_body, draft, True
                        m = EmailMessage()
                        m["From"] = "Jose Luis (ClearDay) <you@clearday.demo>"
                        m["To"] = to
                        m["Subject"] = rsubject
                        m.set_content(send_body)
                        s2 = smtplib.SMTP("127.0.0.1", 1025, timeout=10)
                        s2.send_message(m)
                        s2.quit()
                        sent = True
                        items = [i for i in load_memory() if i.get("mid") != mid]
                        save_memory(items)
                except Exception:
                    sent = False
            if not did_trans and already and orig and orig != lang and sent:
                wrote_field = one2("wrote")
                if wrote_field:
                    wrote, did_trans = wrote_field, True
            self._send(render_reply_sent(to, rsubject, send_body, sent, lang,
                                         wrote=wrote if did_trans else "",
                                         sent_lang=orig if did_trans else ""))
            return
        if self.path.startswith("/api/clear"):
            if not api_rate_ok():
                self._send_json({"error": "Too many calls. Wait a minute and try again."}, 429)
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > 60000:
                self._send_json({"error": "That message is too long for the demo."}, 400)
                return
            raw = self.rfile.read(length).decode(errors="replace") if length else ""
            try:
                data = json.loads(raw)
            except Exception:
                data = None
            if not isinstance(data, dict):
                self._send_json({"error": "Body must be JSON."}, 400)
                return
            text = str(data.get("text") or "")
            if not text.strip():
                self._send_json({"error": "Field 'text' is required."}, 400)
                return
            if len(text) > 50000:
                self._send_json({"error": "That message is too long for the demo (50,000 characters max)."}, 400)
                return
            lang = str(data.get("lang") or "en")
            if lang not in ("en", "es", "vi"):
                lang = "en"
            r = transform(text, str(data.get("sender") or ""), str(data.get("subject") or ""), lang)
            self._send_json({"what": r.get("what", ""), "actions": r.get("actions", []),
                             "facts": r.get("facts", {}), "steps": r.get("steps", []),
                             "risk": r.get("risk", ""), "dates_numbers": r.get("dates_numbers", []),
                             "dates_labeled": r.get("dates_labeled", []),
                             "sender": r.get("sender", ""), "subject": str(data.get("subject") or ""),
                             "lang": r.get("lang", lang), "source": r.get("source", "rules"),
                             "model_name": r.get("model_name", "")})
            return
        if self.path.startswith("/api"):
            self._send_json({"error": "Not found"}, 404)
            return
        if self.path.startswith("/bulk/clear"):
            length = int(self.headers.get("Content-Length") or 0)
            f = parse_qs(self.rfile.read(length).decode(errors="replace")) if length else {}
            lang = (f.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            self._send(self._do_bulk(lang))
            return
        if self.path.startswith("/inbox/clear"):
            length = int(self.headers.get("Content-Length") or 0)
            f = parse_qs(self.rfile.read(length).decode(errors="replace")) if length else {}
            lang = (f.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            mid = (f.get("id") or [""])[0]
            self._send(self._clear_one(mid, lang, dedupe=True))
            return
        if self.path.startswith("/inbox/fresh"):
            mid = mp_fresh()
            body = json.dumps({"id": mid}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/inbox/seed"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            try:
                mp_seed()
            except Exception:
                pass
            self.send_response(303)
            self.send_header("Location", "/inbox?lang=" + lang)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        if n > 50000:
            self._send(render_form("<p class='big'><b>That message is too long for the demo. Please paste a shorter sample.</b></p>")); return
        data = parse_qs(self.rfile.read(n).decode())
        text = (data.get("text") or [""])[0]; sender = (data.get("sender") or [""])[0]; subject = (data.get("subject") or [""])[0]
        lang = (data.get("lang") or ["en"])[0]
        if lang not in ("en", "es", "vi"):
            lang = "en"
        if not text.strip():
            self._send(render_form("<p style='font-size:22px;'><b>Paste a message first.</b></p>", lang)); return
        page = transform(text, sender, subject, lang)
        page["_text"] = text; page["_mid"] = ""; page["_addr"] = ""; page["_subject"] = subject
        _items, _added = remember(load_memory(), page["what"], page["sender"], page.get("lang", lang), subject=subject)
        save_memory(_items)
        self._send(render_page(page))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"ClearDay on {port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
