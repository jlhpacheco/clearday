# Focus test for the Nov 26 Fixes 1-2 (extractors + grounding + reply path).
# Same helpers and assertion style as smoke_test.py; every network read retries
# so a Sprite loopback stall cannot kill the run. Run INSIDE the Sprite:
#   python3 -u focus_test.py
import urllib.request, urllib.parse, urllib.error, json, sys, smtplib, time
from email.message import EmailMessage
BASE = "http://localhost:8080"
MP = "http://127.0.0.1:8025/mailpit"
fails = []
count = [0]
def check(name, cond):
    count[0] += 1
    print(("PASS" if cond else "FAIL"), "-", name, flush=True)
    if not cond: fails.append(name)
def _open(req, timeout=60):
    last = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors="replace")
        except Exception as e:
            last = e; time.sleep(3)
    raise last
def get(path, base=BASE):
    return _open(base + path)
def post(path, data, base=BASE):
    body = urllib.parse.urlencode(data).encode()
    return _open(urllib.request.Request(base + path, data=body))
def mp_get(url):
    last = None
    for _ in range(4):
        try:
            return urllib.request.urlopen(url, timeout=20).read()
        except Exception as e:
            last = e; time.sleep(3)
    raise last
def mp_list():
    return json.loads(mp_get(MP + "/api/v1/messages?limit=50"))
def mp_delete_all():
    req = urllib.request.Request(MP + "/api/v1/messages", method="DELETE")
    last = None
    for _ in range(4):
        try:
            urllib.request.urlopen(req, timeout=20).read(); return
        except Exception as e:
            last = e; time.sleep(3)
    raise last
def find_id(subject):
    for m in mp_list()["messages"]:
        if m["Subject"] == subject:
            return m["ID"]
    return ""
def send_mail(frm, subject, body):
    m = EmailMessage(); m["From"] = frm; m["To"] = "you@clearday.demo"; m["Subject"] = subject; m.set_content(body)
    s = smtplib.SMTP("127.0.0.1", 1025, timeout=15); s.send_message(m); s.quit()

# ---------- Fix 1: extractor formats land in the DATES + NUMBERS box ----------
send_mail("Pat Lee <pat@example.org>", "Room booking", "Room 412 holds 37 people. The cost is $1,250.50 total. Please reply to confirm the booking.")
pid = find_id("Room booking")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FAKE-DATA: numbers land in the DATES + NUMBERS box itself ($1,250.50, 412, 37 in the big-type rows)", "font-size:26px'><b>$1,250.50</b>" in ppage and "font-size:26px'><b>412</b>" in ppage and "font-size:26px'><b>37</b>" in ppage)
send_mail("Pat Lee <pat@example.org>", "Form due date", "The form is due 11/24/2026. Please reply to confirm the form.")
pid = find_id("Form due date")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FORMATS: numeric date 11/24/2026 lands in the DATES + NUMBERS box", code == 200 and "font-size:26px'><b>11/24/2026</b>" in ppage)
send_mail("Pat Lee <pat@example.org>", "Deadline formats", "The deadline is 2026-11-30. See you November 27th at 17:30. Please reply.")
pid = find_id("Deadline formats")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FORMATS: ISO 2026-11-30 + ordinal November 27th + 24h time 17:30 all land in the box", code == 200 and "font-size:26px'><b>2026-11-30</b>" in ppage and "font-size:26px'><b>November 27th</b>" in ppage and "font-size:26px'><b>17:30</b>" in ppage)
send_mail("Pat Lee <pat@example.org>", "No dates here", "Hello, just checking in. Please reply when you can.")
pid = find_id("No dates here")
code, ppage = get("/inbox/clear?id=" + pid + "&lang=en")
check("FAKE-DATA: a dateless email shows NO dates box entries (nothing invented)", code == 200 and "font-size:26px" not in ppage)

# ---------- Fix 2: grounding filter (unit, direct import) ----------
sys.path.insert(0, "/home/sprite/clearday")
import clearday as _cd
_allowed = _cd._allowed_tokens("Lunch is on March 3. The room holds 40 people.", "en")
_cleaned = _cd._strip_ungrounded("Pay $999 by January 40, or confirm March 3 for 40 people, not 41, at 9:99 PM", _allowed, "en")
check("GROUNDING: model-invented $999 / January 40 / 41 / 9:99 PM are stripped in code; real March 3 / 40 stay", "$999" not in _cleaned and "January 40" not in _cleaned and "41" not in _cleaned and "9:99" not in _cleaned and "March 3" in _cleaned and "40 people" in _cleaned)

# ---------- Reply flow still works end to end after grounding ----------
mp_delete_all()
code, fresh = post("/inbox/fresh", {})
mid = find_id("Board meeting moved")
check("REPLY PREP: fresh sample seeded for the reply flow", bool(mid))
code, cpage = get("/inbox/clear?id=" + mid + "&lang=en")
code, draft = post("/reply", {"mid": mid, "lang": "en"})
check("REPLY: draft page first - editable box + Send button + AI/rules pill, nothing sent yet", code == 200 and "YOUR REPLY DRAFT" in draft and "<textarea" in draft and "Send this reply" in draft and ("AI: live model" in draft or "Rules: instant" in draft))
import re as _re
mto = _re.search(r'name="to" value="([^"]+)"', draft)
to_addr = mto.group(1) if mto else ""
edited = "Thank you, Maria. I confirm I will be there on Tuesday. - Jose Luis"
code, sent = post("/reply/send", {"mid": mid, "to": to_addr, "text": edited, "lang": "en"})
time.sleep(2)
texts = ""
for m in mp_list()["messages"]:
    if m["Subject"].startswith("Re:"):
        texts = json.loads(mp_get(MP + "/api/v1/message/" + m["ID"]))["Text"]
        break
check("REPLY: Send delivers the EDITED words into the same Mailpit box", code == 200 and "I confirm I will be there on Tuesday" in texts)
code, fol = get("/followups")
check("REPLY: follow-up for that email is closed after sending", code == 200 and "Board meeting moved" not in fol)

print("FOCUS TOTAL:", count[0] - len(fails), "of", count[0], "PASS")
if fails:
    print("FAILURES:", fails); sys.exit(1)
