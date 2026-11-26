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
check("BULK: the nav on the home page carries the Bulk clear link", code == 200 and "href='/bulk'" in home)
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

