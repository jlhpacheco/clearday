"""ClearDay web app - stdlib only, runs anywhere incl. a Fly Sprite (port 8080).
Persistent memory: follow-ups are stored in memory.json on the Sprite's
persistent disk, so the agent remembers across sleeps and follows up.
Connector use (Hacksgiving rule): on a Sprite, set CLEARDAY_MODEL_URL to a
Sprites Connector gateway URL (Anthropic / OpenRouter) and/or receive mail
via the AgentMail connector inbox and forward it to POST /inbox.
"""
import json, os, html, http.client, smtplib, urllib.request
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from clearday import transform
from render import render_page, render_form, render_inbox, S

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
MP = "http://127.0.0.1:8025/mailpit"  # Mailpit on the same Sprite (webroot /mailpit)

def mp_api(path):
    req = urllib.request.Request(MP + path, headers={"User-Agent": "ClearDay/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def mp_seed():
    """Send the sample board email into the Mailpit inbox by real SMTP."""
    text = open(os.path.join(os.path.dirname(__file__), "sample_email.txt")).read()
    m = EmailMessage()
    m["From"] = "Maria Lopez <maria.lopez@example.org>"
    m["To"] = "you@clearday.demo"
    m["Subject"] = "Board meeting moved"
    m.set_content(text)
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
        """Pass /mailpit* through to Mailpit on localhost - its real UI, unmodified."""
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
                items = load_memory()
                items.append({"what": result["what"], "sender": result["sender"],
                              "lang": result.get("lang", lang)})
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
            items = load_memory(); items.append({"what": page["what"], "sender": page["sender"], "lang": page.get("lang", lang)}); save_memory(items[-20:])
            self._send(render_page(page))
        elif self.path.startswith("/followups"):
            items = load_memory()
            def row(i):
                s = S(i.get("lang", "en"))
                return f"<div style='font-size:22px;padding:10px;'>&#9679; {html.escape(str(i['what']))} — {s['nudge']} {html.escape(str(i['sender']))}</div>"
            en = S("en")
            rows = "".join(row(i) for i in items) or f"<div style='font-size:22px;padding:10px;'>{en['no_followups']}</div>"
            self._send(render_form(f"<h2 style='font-size:28px;'>{en['followups_title']}</h2><p class='big'><b>{en['demo_entries']}</b></p>{rows}"))
        elif "sample=1" in self.path:
            q = parse_qs(urlparse(self.path).query)
            lang = (q.get("lang") or ["en"])[0]
            if lang not in ("en", "es", "vi"):
                lang = "en"
            try:
                text = open(os.path.join(os.path.dirname(__file__), "sample_email.txt")).read()
            except Exception:
                text = ""
            self._send(render_form("", lang, {"sender": "Maria Lopez", "subject": "Board meeting moved", "text": text}))
        else:
            self._send(render_form())
    def do_POST(self):
        if self.path.startswith("/mailpit"):
            self._proxy_mailpit()
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
        items = load_memory(); items.append({"what": page["what"], "sender": page["sender"], "lang": page.get("lang", lang)}); save_memory(items[-20:])
        self._send(render_page(page))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"ClearDay on {port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
