"""ClearDay web app - stdlib only, runs anywhere incl. a Fly Sprite (port 8080).
Persistent memory: follow-ups are stored in memory.json on the Sprite's
persistent disk, so the agent remembers across sleeps and follows up.
Connector use (Hacksgiving rule): on a Sprite, set CLEARDAY_MODEL_URL to a
Sprites Connector gateway URL (Anthropic / OpenRouter) and/or receive mail
via the AgentMail connector inbox and forward it to POST /inbox.
"""
import json, os, html
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from clearday import transform
from render import render_page, render_form

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

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
        elif self.path.startswith("/followups"):
            items = load_memory()
            rows = "".join(f"<div style='font-size:22px;padding:10px;'>&#9679; {html.escape(str(i['what']))} — no reply yet — I will nudge {html.escape(str(i['sender']))}</div>" for i in items) or "<div style='font-size:22px;padding:10px;'>No follow-ups waiting.</div>"
            self._send(render_form(f"<h2 style='font-size:28px;'>Follow-ups I remember</h2><p class='big'><b>Demo entries — made from sample text pasted by visitors.</b></p>{rows}"))
        else:
            self._send(render_form())
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if n > 50000:
            self._send(render_form("<p class='big'><b>That message is too long for the demo. Please paste a shorter sample.</b></p>")); return
        data = parse_qs(self.rfile.read(n).decode())
        text = (data.get("text") or [""])[0]; sender = (data.get("sender") or [""])[0]; subject = (data.get("subject") or [""])[0]
        if not text.strip():
            self._send(render_form("<p style='font-size:22px;'><b>Paste a message first.</b></p>")); return
        page = transform(text, sender, subject)
        items = load_memory(); items.append({"what": page["what"], "sender": page["sender"]}); save_memory(items[-20:])
        self._send(render_page(page))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"ClearDay on {port}")
    HTTPServer(("0.0.0.0", port), H).serve_forever()
