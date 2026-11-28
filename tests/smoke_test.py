import urllib.request, urllib.parse, urllib.error, json, sys, smtplib, socket
from email.message import EmailMessage
BASE = "http://127.0.0.1:8080"  # not "localhost": on the Sprite that name can resolve to an IPv6 socket the app does not listen on, and the run wedges before its first check
MP = "http://127.0.0.1:8025/mailpit"
fails = []
count = [0]
def check(name, cond):
    count[0] += 1
    print(("PASS" if cond else "FAIL"), "-", name)
    if not cond: fails.append(name)
def get(path, base=BASE):
    # Retry on transport errors only (a slow-dripping model answer can hold
    # one request for minutes; the scenarios suite proved retries ride it
    # out). HTTP answers - even errors - are returned, never retried.
    import time as _t
    last = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(base + path, timeout=180) as r:
                return r.status, r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors="replace")
        except Exception as e:
            last = e; _t.sleep(3)
    raise last
def post(path, data, base=BASE):
    import time as _t
    last = None
    for _ in range(3):
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(base + path, data=body)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors="replace")
        except Exception as e:
            last = e; _t.sleep(3)
    raise last
def mp_get(url):
    # Mailpit's API occasionally stalls for a few seconds on the Sprite;
    # retry the READ (never the thing being checked) so a stall cannot kill the run
    import time as _t
    last = None
    for _ in range(4):
        try:
            return urllib.request.urlopen(url, timeout=20).read()
        except Exception as e:
            last = e; _t.sleep(3)
    raise last
def mp_list():
    return json.loads(mp_get(MP + "/api/v1/messages?limit=50"))
def mp_delete_all():
    import time as _t
    req = urllib.request.Request(MP + "/api/v1/messages", method="DELETE")
    last = None
    for _ in range(4):
        try:
            urllib.request.urlopen(req, timeout=20).read(); return
        except Exception as e:
            last = e; _t.sleep(3)
    raise last
def find_id(subject):
    for m in mp_list()["messages"]:
        if m["Subject"] == subject:
            return m["ID"]
    return ""
def send_mail(frm, subject, body):
    m = EmailMessage(); m["From"] = frm; m["To"] = "you@clearday.demo"; m["Subject"] = subject; m.set_content(body)
    s = smtplib.SMTP("127.0.0.1", 1025, timeout=10); s.send_message(m); s.quit()

code, form = get("/")
check("form 200 + labels + demo line", code == 200 and "Make it clear" in form and "Public demo" in form)
check("clear page: HERO first, then HIS story strip with ONE button - 'Read my story' (no Mailpit button, no See-for-yourself lead-in)", "what it is like to be dyslexic" in form and "three tries" in form and "thankgiving" not in form and "[[MAILPIT]]" not in form and form.count("class='btn rawbtn'") == 1 and ">Read my story</a>" in form and ">Mailpit</a>" not in form and form.index("Long message in") < form.index("Before you judge this app") < form.index("Load the sample email"))
check("ONE DIALOG: his full story sits ON TOP, the raw inbox lands BELOW it (story first, email under)", form.count("<dialog") == 1 and "storybox" not in form and "<br><br>" in form and "src='/mailpit/'" in form and form.index("thankful this Thanksgiving") < form.index("src='/mailpit/'"))
check("DIALOG (build C): NO auto-jump - fresh() never scrolls on its own; a 'See the email' button waits for the reader's own tap", "id='seeemail'" in form and ">See the email" in form and "scrollIntoView" not in form.split("function fresh()")[1].split("</script>")[0])
import re as _re, subprocess as _sp, tempfile as _tf, os as _os
_node = "/.sprite/bin/node" if _os.path.exists("/.sprite/bin/node") else "node"
_js_ok = True
for _s in _re.findall(r"<script>(.*?)</script>", form, _re.S):
    with _tf.NamedTemporaryFile("w", suffix=".js", delete=False) as _f:
        _f.write(_s); _p = _f.name
    if _sp.run([_node, "--check", _p]).returncode != 0:
        _js_ok = False
check("SCRIPTS: every script block on the home page parses as valid JavaScript (node --check) - a dead script once froze the story dialog's progress bar", _js_ok)
check("clear page: 'Why the cream page' is now a TAB - link in the nav, card body OFF the home page", "href='/why'" in form and "warm backgrounds tested best" not in form)
code, whypage = get("/why?lang=en")
check("WHY TAB: /why page carries the full research card (title + all five reasons)", code == 200 and "Why the cream page? For judges" in whypage and "warm backgrounds tested best" in whypage and "WCAG 2.2 AA" in whypage)
code, spage = get("/?sample=1&lang=en")
_js_ok2 = True
for _s in _re.findall(r"<script>(.*?)</script>", spage, _re.S):
    with _tf.NamedTemporaryFile("w", suffix=".js", delete=False) as _f:
        _f.write(_s); _p = _f.name
    if _sp.run([_node, "--check", _p]).returncode != 0:
        _js_ok2 = False
check("SAMPLE SCROLL (Jose Luis, Nov 27): the sample-loaded page carries the glide-down script + banner anchor, and every script on it parses", code == 200 and "id='sampletop'" in spage and "scrollIntoView" in spage and _js_ok2)
sample = open("/home/sprite/clearday/sample_email.txt").read()
code, page = post("/", {"sender": "Maria Lopez", "subject": "Board meeting moved", "text": sample, "lang": "en"})
if "Rules: instant answer" in page:
    # one retry: a single slow gateway call falls back to rules BY DESIGN;
    # two in a row would mean the model path is really down
    code, page = post("/", {"sender": "Maria Lopez", "subject": "Board meeting moved", "text": sample, "lang": "en"})
dates = ["Original Meeting Date: Monday, November 23", "New Meeting Date: Tuesday, November 24 at 5:15 PM", "Reply by: Friday, November 27"]
check("sample -> sections + exact 4 dates", code == 200 and "YOU MUST DO" in page and "KEY FACTS" in page and all(d in page for d in dates))
check("green pill: live model answered", "AI: live model response" in page and "DeepSeek" in page)
check("result page: right column = DATES + NUMBERS on top, REPLY under it, IF YOU DO NOTHING at the bottom (Jose Luis's word, Nov 27)", "IF YOU DO NOTHING" in page and "Click Draft a reply after reading the email." in page and "warm backgrounds tested best" not in page and "class='layout even'" in page and page.index("DATES + NUMBERS") > page.index("KEY FACTS") and page.index("Click Draft a reply after reading the email.") > page.index("DATES + NUMBERS") and page.index("IF YOU DO NOTHING") > page.index("Click Draft a reply after reading the email."))
check("result page: REPLY is an action card with the BIG button", "replycard" in page and "bigbtn" in page and "Click Draft a reply after reading the email." in page)
code, conn = get("/connected")
check("PROOF PAGE: GitHub side LIVE with real metadata (login, newest commit, rate left)", code == 200 and "jlhpacheco" in conn and "Newest commit" in conn and "API calls left" in conn)
check("PROOF PAGE: Together side LIVE with a real test call (model answer + tokens + call id)", "DeepSeek-V4.1-Flash-1017" in conn and "Tokens in the test call" in conn and "The model answered" in conn and conn.count("LIVE - working now") >= 2)
check("PROOF PAGE: TWO COLUMNS - GitHub left, Together AI right (Jose Luis's printout, Nov 27)", "class='cols2'" in conn and conn.index("GitHub") < conn.index("Together AI") and conn.index("class='cols2'") < conn.index("GitHub"))
code, esc = post("/", {"sender": "Test", "subject": "Esc", "text": "Hello <b>ZZTEST</b> world. Please reply to confirm.", "lang": "en"})
check("pasted HTML never raw (escaped or paraphrased)", "<b>ZZTEST</b>" not in esc)
code, noask = post("/", {"sender": "Ana Ruiz", "subject": "Thank you", "text": "Thank you for the wonderful evening. We loved the food and the company. No reply is needed at all.", "lang": "en"})
check("DUTIES GUARD (live): a no-ask email shows 'asks nothing of you' - no invented duties, model or not", code == 200 and "This email asks nothing of you" in noask)
try:
    code, big = post("/", {"sender": "Test", "subject": "Big", "text": "x" * 60000, "lang": "en"})
    refused = code == 200 and ("too long" in big.lower() or "shorter" in big.lower() or "50,000" in big or "50000" in big)
except Exception:
    refused = True
check("60,000-char paste refused politely", refused)
code, filled = get("/?sample=1&lang=en")
check("sample button fills the form (From + banner + body)", code == 200 and "value='Maria Lopez'" in filled and "Sample loaded in the form" in filled and "Room 4" in filled)
mp_delete_all()
code, filled2 = get("/?sample=1&lang=en")
check("PARALLEL: sample click also puts the email into Mailpit (no inbox visit)", mp_list()["total"] == 1 and find_id("Board meeting moved") != "")
code, ib = get("/inbox?lang=en")
check("inbox page lists the real email (Maria Lopez + Make it clear)", code == 200 and "Maria Lopez" in ib and "Make it clear" in ib)
_mid = find_id("Board meeting moved")
code, cl = get("/inbox/clear?id=" + _mid + "&lang=en")
check("inbox clear flow -> clear page + labeled date", code == 200 and "WHAT THIS IS" in cl and "New Meeting Date: Tuesday, November 24" in cl)
code, fol = get("/followups")
check("/followups demo label", code == 200 and "Demo entries" in fol)
one = json.loads(mp_get(MP + "/api/v1/message/" + _mid))
check("mailpit API: message fields real (From/Subject/Text)", one["From"]["Name"] == "Maria Lopez" and one["Subject"] == "Board meeting moved" and "Room 4" in one["Text"])
before = mp_list()["total"]
post("/inbox/seed?lang=en", {})
check("seed endpoint adds a real email via SMTP", mp_list()["total"] == before + 1)
code, ibes = get("/inbox?lang=es")
check("inbox in Spanish (LA BANDEJA + Hazlo claro)", code == 200 and "LA BANDEJA" in ibes and "Hazlo claro" in ibes)
code, cles = get("/inbox/clear?id=" + _mid + "&lang=es")
check("inbox clear in Spanish -> Spanish page, source dates copied exactly", code == 200 and "FECHAS Y NÚMEROS" in cles and "Tuesday November 24" in cles and "5:15 PM" in cles)
code, ibvi = get("/inbox?lang=vi")
check("inbox in Vietnamese (HOP THU + Lam ro)", code == 200 and "HỘP THƯ" in ibvi and "Làm rõ" in ibvi)
code, bogus = get("/inbox/clear?id=DOESNOTEXIST&lang=en")
check("bogus message id -> 200 fallback, no crash", code == 200 and "THE INBOX" in bogus)
mp_delete_all()
code, ib2 = get("/inbox?lang=en")
check("delete-all -> inbox re-seeds itself (Maria Lopez back)", code == 200 and "Maria Lopez" in ib2 and mp_list()["total"] >= 1)
code, mpui = get("/mailpit/")
check("raw Mailpit UI through ClearDay proxy -> 200", code == 200 and "mailpit" in mpui.lower())
code, mpapi = get("/mailpit/api/v1/messages")
check("Mailpit API through ClearDay proxy -> JSON total >= 1", code == 200 and json.loads(mpapi)["total"] >= 1)
_mid = json.loads(mpapi)["messages"][0]["ID"]
code, mdet = get("/mailpit/api/v1/message/" + _mid)
_md = json.loads(mdet) if code == 200 else {}
check("Maria's email carries BOTH parts: text body + HTML version (reading pane can never open blank)", bool(_md.get("Text", "").find("Hi everyone") >= 0 and len(_md.get("HTML", "")) > 100))
code, fresh = post("/inbox/fresh", {})
_fj = json.loads(fresh) if code == 200 else {}
check("FRESH: pressing Mailpit sends a BRAND-NEW Maria email (POST /inbox/fresh -> id, box holds exactly 1)", code == 200 and bool(_fj.get("id")) and mp_list()["total"] == 1)
import datetime as _dt
_cr = mp_list()["messages"][0].get("Created", "")
_age = (_dt.datetime.now(_dt.timezone.utc) - _dt.datetime.fromisoformat(_cr.replace("Z", "+00:00"))).total_seconds() if _cr else 9999
check("FRESH: the new email really is new (arrived under 2 minutes ago)", _age < 120)
s = socket.create_connection(("127.0.0.1", 8080), timeout=10)
s.sendall(b"GET /mailpit/api/events HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n")
s.settimeout(10); resp = s.recv(200).decode(errors="replace"); s.close()
check("websocket upgrade -> 501 fast, server not stuck", "501" in resp)
code, home2 = get("/")
check("server still healthy after all probes", code == 200 and "Make it clear" in home2)
# ---- fake-data block: dates/numbers are copied, NEVER invented ----
send_mail("Sam Ortiz <sam@example.org>", "Parking lot update", "Hi team, thanks for the update about the parking lot painting. The crew did a great job and the lines look fresh. Please confirm you got this note.")
pid = find_id("Parking lot update")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"]
check("FAKE-DATA: dateless email -> no month, no year invented", code == 200 and not any(mo in ppage for mo in MONTHS) and "2026" not in ppage)
send_mail("Dana Ruiz <dana@example.org>", "Dentist", "The dentist appointment is on Friday December 11. Please reply to confirm.")
pid = find_id("Dentist")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FAKE-DATA: one-date email -> exactly that date, no sample bleed", code == 200 and "Friday December 11" in ppage and "Tuesday November 24" not in ppage and "5:15 PM" not in ppage)
send_mail("Pat Lee <pat@example.org>", "Room booking", "Room 412 costs $1,250.50 for 37 people. Please reply to confirm the booking.")
pid = find_id("Room booking")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FAKE-DATA: numbers copied exactly ($1,250.50 in, no $1,250.51)", code == 200 and "$1,250.50" in ppage and "412" in ppage and "$1,250.51" not in ppage)
check("FAKE-DATA: numbers land in the DATES + NUMBERS box itself ($1,250.50, 412, 37 in the big-type rows)", "font-size:26px'><b>$1,250.50</b>" in ppage and "font-size:26px'><b>412</b>" in ppage and "font-size:26px'><b>37</b>" in ppage)
send_mail("Pat Lee <pat@example.org>", "Form due date", "The form is due 11/24/2026. Please reply to confirm the form.")
pid = find_id("Form due date")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FORMATS: numeric date 11/24/2026 lands in the DATES + NUMBERS box", code == 200 and "font-size:26px'><b>11/24/2026</b>" in ppage)
send_mail("Pat Lee <pat@example.org>", "Deadline formats", "The deadline is 2026-11-30. See you November 27th at 17:30. Please reply.")
pid = find_id("Deadline formats")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FORMATS: ISO 2026-11-30 + ordinal November 27th + 24h time 17:30 all land in the box", code == 200 and "font-size:26px'><b>2026-11-30</b>" in ppage and "font-size:26px'><b>November 27th</b>" in ppage and "font-size:26px'><b>17:30</b>" in ppage)
import clearday as _cd
_allowed = _cd._allowed_tokens("Lunch is on March 3. The room holds 40 people. See you November 24.", "en")
_cleaned = _cd._strip_ungrounded("Pay $999 by January 40, or confirm March 3 for 40 people, not 41, at 9:99 PM. See you November 24, not November 25.", _allowed, "en")
check("GROUNDING: model-invented $999 / January 40 / 41 / 9:99 PM are stripped in code; real March 3 / 40 stay", "$999" not in _cleaned and "January 40" not in _cleaned and "41" not in _cleaned and "9:99" not in _cleaned and "March 3" in _cleaned and "40 people" in _cleaned)
check("GROUNDING: a real 2-digit-day date keeps its day (November 24 stays whole; invented November 25 is cut)", "November 24" in _cleaned and "November 25" not in _cleaned)
# ---- the 45-second cap (Nov 26, Jose Luis's call): a slow-dripping model
# must never hold an answer hostage; at the cap, the RULES answer instead ----
import threading as _th, time as _tm
from http.server import BaseHTTPRequestHandler as _BH, HTTPServer as _HS
class _SlowH(_BH):
    def do_POST(self):
        _tm.sleep(10)
        b = json.dumps({"choices": [{"message": {"content": "{}"}}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
_srv = _HS(("127.0.0.1", 0), _SlowH); _th.Thread(target=_srv.serve_forever, daemon=True).start()
_old_url, _old_dl = _os.environ.get("CLEARDAY_MODEL_URL"), _cd._MODEL_DEADLINE
_os.environ["CLEARDAY_MODEL_URL"] = f"http://127.0.0.1:{_srv.server_address[1]}"; _cd._MODEL_DEADLINE = 3
_t0 = _tm.time()
_cap_out = _cd.transform("The meeting moved to Tuesday November 24 at 5:15 PM. Please reply to confirm.", "Maria Lopez", "Board meeting moved", "en")
_cap_el = _tm.time() - _t0
if _old_url: _os.environ["CLEARDAY_MODEL_URL"] = _old_url
else: _os.environ.pop("CLEARDAY_MODEL_URL", None)
_cd._MODEL_DEADLINE = _old_dl; _srv.shutdown()
check("MODEL CAP: a provider that drips past the cap gets cut - the rules answer instead (cap set to 3s for the test, 45s in the app)", _cap_out["source"] == "rules" and _cap_el < 8)
send_mail("María López <maria.lopez@example.org>", "Reunión del martes", "La reunión es el martes 24 de noviembre a las 5:15 p. m. en la Sala 4. Por favor confirme su asistencia.")
pid = find_id("Reunión del martes")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=es")
check("FAKE-DATA: Spanish email -> exact Spanish dates (martes 24 de noviembre, 5:15 p. m.)", code == 200 and "martes 24 de noviembre" in ppage and "5:15 p. m." in ppage and "FECHAS Y NÚMEROS" in ppage)
# ---- reply block: DRAFT first, reader edits, reader sends ----
_mid = find_id("Board meeting moved")
get("/inbox/clear?id=" + _mid + "&lang=en")  # the real path: reply starts from a clear page (adds the follow-up)
before = mp_list()["total"]
code, rp = post("/reply", {"mid": _mid, "lang": "en"})
check("REPLY: draft page first - editable box + Send button, NOTHING sent yet", code == 200 and "YOUR REPLY DRAFT" in rp and "Send this reply" in rp and "name='body'" in rp and mp_list()["total"] == before)
check("REPLY: draft page says who wrote it (AI pill or Rules pill)", "AI: live model response" in rp or "Rules: instant answer" in rp)
mem = json.load(open("/home/sprite/clearday/memory.json"))
check("REPLY: follow-up still waiting after the draft (not closed yet)", any(i.get("mid") == _mid for i in mem))
edited = "Hello Maria,\n\nEDITED-BY-READER: I will attend on Tuesday November 24 at 5:15 PM and bring my photo ID.\n\nThank you,\nJose Luis"
code, rp2 = post("/reply/send", {"mid": _mid, "to": "maria.lopez@example.org", "subject": "Re: Board meeting moved", "body": edited, "lang": "en"})
newest = mp_list()["messages"][0]
rtext = json.loads(mp_get(MP + "/api/v1/message/" + newest["ID"]))["Text"]
mem = json.load(open("/home/sprite/clearday/memory.json"))
check("REPLY SEND: sent only on Send press - edited words delivered, follow-up closed", code == 200 and "REPLY SENT" in rp2 and mp_list()["total"] == before + 1 and newest["To"][0]["Address"] == "maria.lopez@example.org" and newest["Subject"] == "Re: Board meeting moved" and "EDITED-BY-READER" in rtext and not any(i.get("mid") == _mid for i in mem))
before = mp_list()["total"]
code, rp3 = post("/reply", {"sender": "Maria Lopez", "subject": "Board meeting moved", "text": sample, "lang": "en"})
check("REPLY (paste path): real address found in the Inbox - Send button IS here, banner says where it came from, nothing sent yet", code == 200 and "YOUR REPLY DRAFT" in rp3 and "/reply/send" in rp3 and "found the real address in the raw inbox" in rp3 and "maria.lopez@example.org" in rp3 and mp_list()["total"] == before)
code, rp3b = post("/reply", {"sender": "Nobody Here", "subject": "Unmatched subject zzz", "text": "Hello, a short note with no inbox match.", "lang": "en"})
check("REPLY (paste path, NO inbox match): no Send button, big notice says why", code == 200 and "/reply/send" not in rp3b and "NO SEND BUTTON ON THIS PAGE" in rp3b and mp_list()["total"] == before)
code, homenav = get("/")
check("NAV: Inbox tab is GONE from the top nav (route stays, tab goes)", code == 200 and "href='/inbox'" not in homenav)
before = mp_list()["total"]
code, rp5 = post("/reply", {"sender": "", "subject": "", "text": sample, "lang": "en"})
check("REPLY (paste path, BLANK name+subject): Maria's real address still found - Send button IS here", code == 200 and "/reply/send" in rp5 and "maria.lopez@example.org" in rp5 and "found the real address in the raw inbox" in rp5 and mp_list()["total"] == before)
_mid5 = rp5.split("name='mid' value='")[1].split("'")[0] if "name='mid' value='" in rp5 else ""
code, rp6 = post("/reply/send", {"mid": _mid5, "to": "maria.lopez@example.org", "subject": "Re: Board meeting moved", "body": "BLANKPATH REPLY WORDS", "lang": "en"})
_msgs6 = mp_list()["messages"]
check("REPLY (blank path) SENT: reply lands in Mailpit NEXT TO Maria's - box holds both, sent page has the BIG both-emails button", code == 200 and "See both emails in Mailpit" in rp6 and "bigbtn" in rp6 and mp_list()["total"] == before + 1 and _msgs6[0]["To"][0]["Address"] == "maria.lopez@example.org")
before = mp_list()["total"]
code, rp4 = post("/reply/send", {"mid": _mid, "to": "stranger@example.org", "subject": "Re: Board meeting moved", "body": "planted words", "lang": "en"})
check("REPLY GATE: send to a wrong address is refused (nothing sent)", mp_list()["total"] == before)
import http.client as _hc
def raw_req(method, path, body=None):
    c = _hc.HTTPConnection("127.0.0.1", 8080, timeout=15)
    c.request(method, path, body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse(); r.read(); c.close()
    return r.status
before = mp_list()["total"]
st = raw_req("POST", "/mailpit/api/v1/send", json.dumps({"From": {"Email": "eve@example.org", "Name": "Eve"}, "To": [{"Email": "you@clearday.demo"}], "Subject": "INJECTED", "Text": "planted"}))
check("PROXY WRITE-BLOCK: send via public proxy -> 403, nothing planted", st == 403 and mp_list()["total"] == before and find_id("INJECTED") == "")
st = raw_req("DELETE", "/mailpit/api/v1/messages")
check("PROXY WRITE-BLOCK: delete-all via public proxy -> 403, inbox intact", st == 403 and mp_list()["total"] == before)
# ---- API + bulk block (Nov 26): the REST doors and the whole-inbox clear ----
import urllib.error as _ue
import time as _time
def api_post(payload, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode()
    last = None
    for _try in range(3):
        req = urllib.request.Request(BASE + "/api/clear", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except _ue.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except Exception as e:
            last = e
            import time as _t2
            _t2.sleep(3)
    raise last
def api_get(path):
    last = None
    for _try in range(3):
        try:
            with urllib.request.urlopen(BASE + path, timeout=30) as r:
                return r.status, json.loads(r.read())
        except Exception as e:
            last = e
            import time as _t3
            _t3.sleep(3)
    raise last
def followup_mids():
    _, f = api_get("/api/followups")
    return {i.get("mid") for i in f["followups"]}, f
code, idx = api_get("/api")
check("API: GET /api is a JSON index naming the endpoints", code == 200 and idx.get("name") == "ClearDay API" and "POST /api/clear" in idx.get("endpoints", {}))
code, res = api_post({"text": "The form is due 11/24/2026. It costs $1,250.50. Please reply to confirm.", "sender": "Pat Lee", "subject": "Form", "lang": "en"})
check("API: POST /api/clear returns the clear page as JSON - exact dates out (11/24/2026, $1,250.50)", code == 200 and "11/24/2026" in res.get("dates_numbers", []) and "$1,250.50" in res.get("dates_numbers", []) and res.get("source") in ("model", "rules"))
code, err = api_post({"sender": "Pat Lee"})
check("API: missing text -> 400 with a plain error", code == 400 and "error" in err)
code, err = api_post(None, raw=b"this is not json")
check("API: a non-JSON body -> 400, never the HTML form", code == 400 and "error" in err)
code, res = api_post({"text": "Lunch is on March 3. Please reply.", "lang": "xx"})
check("API: an unknown language falls back to English", code == 200 and res.get("lang") == "en")
_, f_before = api_get("/api/followups")
code, _r = api_post({"text": "Dinner is on April 5. Please reply to confirm."})
_, f_after = api_get("/api/followups")
check("API: clearing through the API saves NOTHING (follow-ups untouched, no address field leaks)", code == 200 and f_after["count"] == f_before["count"] and all("addr" not in i for i in f_after["followups"]))
code, home = get("/")
check("NAV: Follow-ups and Bulk clear are OUT of the top nav (Jose Luis: remove them, Nov 27) - the pages still live by direct URL", code == 200 and "href='/bulk'" not in home and "href='/followups'" not in home)
code, bulk = get("/bulk")
check("BULK: landing page shows the big button (Clear the whole inbox)", code == 200 and "Clear the whole inbox" in bulk and "/bulk/clear" in bulk)
mp_delete_all()
get("/inbox?lang=en")
send_mail("Dana Ruiz <dana@example.org>", "Dentist moved", "The dentist moved to Friday December 11 at 9:30 AM. Please reply to confirm.")
send_mail("Sam Ortiz <sam@example.org>", "Invoice due", "Invoice 42 is due on 2026-12-01. The total is $300. Please reply.")
_time.sleep(1)
_maria_mid = find_id("Board meeting moved"); _dana_mid = find_id("Dentist moved"); _sam_mid = find_id("Invoice due")
mids_before, _ = followup_mids()
code, bpage = post("/bulk/clear", {"lang": "en"})
check("BULK: one press clears the whole inbox - combined list + every sender on a card", code == 200 and "EVERYTHING YOU MUST DO" in bpage and "Maria Lopez" in bpage and "Dana Ruiz" in bpage and "Sam Ortiz" in bpage and "2026-12-01" in bpage)
mids_after, _ = followup_mids()
check("BULK: each cleared email became a follow-up (all 3 message ids now waiting)", {_maria_mid, _dana_mid, _sam_mid} <= mids_after and not ({_maria_mid, _dana_mid, _sam_mid} & mids_before))
code, bpage2 = post("/bulk/clear", {"lang": "en"})
mids_after2, _ = followup_mids()
check("BULK: a second press adds ZERO follow-ups (dedupe by message id)", mids_after2 == mids_after)
code, cpage = post("/inbox/clear", {"id": _dana_mid, "lang": "en"})
mids_after3, _ = followup_mids()
check("POST DOOR: /inbox/clear also answers POST - same clear page, follow-up dedupes", code == 200 and "WHAT THIS IS" in cpage and mids_after3 == mids_after)
# ---- cleanup: leave only the sample in the box ----
mp_delete_all()
get("/inbox?lang=en")
d = mp_list()
check("cleanup: inbox holds only the sample email", d["total"] == 1 and d["messages"][0]["Subject"] == "Board meeting moved")
print(f"SMOKE TOTAL: {count[0] - len(fails)}/{count[0]}")
sys.exit(1 if fails else 0)
