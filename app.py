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
from clearday import transform, draft_reply
from render import render_page, render_form, render_inbox, render_reply_sent, render_reply_draft, S

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

def mp_messages():
    try:
        data = mp_api("/api/v1/messages?limit=20")
        return data.get("messages", []), True
    except Exception:
        return [], False

def load_memory():
    try:
        return json.load(open(MEMORY_FILE))
    except Exception:
        return []

def save_memory(items):
    json.dump(items, open(MEMORY_FILE, "w"), indent=2)

class H(BaseHTTPRequestHandler):
    def _send(self, html, code=200):
        b = html.encode(); self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
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
        if self.path.startswith("/connected"):
            gw = os.environ.get("CLEARDAY_GITHUB_GATEWAY", "")
            msg = "GitHub connector is not set on this Sprite."
            if gw:
                try:
                    import urllib.request
                    data = json.load(urllib.request.urlopen(gw + "/user", timeout=10))
                    msg = f"Connected through the Sprites GitHub connector as GitHub user: {data.get('login')}"
                except Exception as e:
                    msg = f"GitHub connector call failed: {e}"
            self._send(render_form(f"<h2 style='font-size:28px;'>Connector check</h2><div style='font-size:22px;padding:10px;'>{msg}</div>"))
        elif self.path.startswith("/mailpit"):
            self._proxy_mailpit()
        elif self.path.startswith("/inbox/clear"):
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            mid = (q.get("id") or [""])[0]
            try:
                msg = mp_api("/api/v1/message/" + mid)
                frm = msg.get("From") or {}
                sender = frm.get("Name") or frm.get("Address") or ""
                result = transform(msg.get("Text") or "", sender, msg.get("Subject") or "", lang)
                result["_text"] = msg.get("Text") or ""
                result["_mid"] = mid
                result["_addr"] = frm.get("Address") or ""
                result["_subject"] = msg.get("Subject") or ""
                items = load_memory()
                items.append({"what": result["what"], "sender": result["sender"],
                              "lang": result.get("lang", lang), "mid": mid,
                              "addr": frm.get("Address") or ""})
                save_memory(items[-20:])
                self._send(render_page(result))
            except Exception:
                msgs, up = mp_messages()
                self._send(render_inbox(msgs, lang, down=True))
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
            items = load_memory(); items.append({"what": page["what"], "sender": page["sender"], "lang": page.get("lang", lang)}); save_memory(items[-20:])
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
            self._send(render_form(f"<h2 style='font-size:28px;'>{en['followups_title']}</h2><p class='big'><b>{en['demo_entries']}</b></p>{rows}"))
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
                try:
                    msgs3, up3 = mp_messages()
                    if up3:
                        for m3 in msgs3:
                            frm3 = m3.get("From") or {}
                            if (m3.get("Subject") or "") == subject and frm3.get("Address"):
                                mid = m3.get("ID") or mid
                                addr = frm3["Address"]
                                sender = frm3.get("Name") or sender
                                found = True
                                break
                except Exception:
                    pass
            dates = transform(text, sender, subject, lang)["dates_numbers"] if text else []
            draft, dsrc = draft_reply(text, sender, subject, lang, dates)
            rsubject = subject if subject.lower().startswith("re:") else "Re: " + subject
            # DRAFT ONLY. Nothing is sent here - the reader sees the draft
            # first and sends it with a separate, explicit press (/reply/send).
            self._send(render_reply_draft(addr or sender, rsubject, draft, lang, mid=mid, addr=addr,
                                          source=dsrc, model_name=os.environ.get("CLEARDAY_MODEL", "") if dsrc == "model" else "",
                                          found=found))
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
            sent = False
            if mid and to and draft:
                try:
                    # Gate: the To must be the real sender of that inbox message.
                    msg = mp_api("/api/v1/message/" + mid)
                    real_addr = (msg.get("From") or {}).get("Address") or ""
                    if real_addr and real_addr == to:
                        m = EmailMessage()
                        m["From"] = "Jose Luis (ClearDay) <you@clearday.demo>"
                        m["To"] = to
                        m["Subject"] = rsubject
                        m.set_content(draft)
                        s2 = smtplib.SMTP("127.0.0.1", 1025, timeout=10)
                        s2.send_message(m)
                        s2.quit()
                        sent = True
                        items = [i for i in load_memory() if i.get("mid") != mid]
                        save_memory(items)
                except Exception:
                    sent = False
            self._send(render_reply_sent(to, rsubject, draft, sent, lang))
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
        items = load_memory(); items.append({"what": page["what"], "sender": page["sender"], "lang": page.get("lang", lang)}); save_memory(items[-20:])
        self._send(render_page(page))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"ClearDay on {port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
