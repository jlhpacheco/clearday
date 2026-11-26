#!/usr/bin/env python3
"""ClearDay 100-scenario suite - designed in tests/scenarios-plan.md.
60 unit scenarios (import clearday, no network) + 40 live scenarios
(HTTP against the app on 127.0.0.1:8080 + Mailpit, inside the Sprite).

Determinism rule: assertions sit ONLY on rules-owned or structural ground -
exact dates_numbers lists, JSON shape, status codes, page markers, Mailpit
totals, follow-up store contents. Never on model wording.

Documented deviations from the plan (built contract wins, safety wins):
- GET /api/followups returns {"count": n, "followups": [...]} (an object,
  not a bare list), and its items NEVER carry the "addr" field - real email
  addresses are not published by the API (risk memo, Nov 26). L16 asserts
  the mid matches and that "addr" is absent.
- U34: an empty email yields actions == [] (verified behavior; the
  "Read the key facts below" fallback appears only for non-empty text, U59).
- L20: with an empty inbox the bulk landing shows the empty note and no
  button (by design) - asserted as such.

Run inside the Sprite:  python3 tests/scenarios.py [unit|live|all]
State control: the live part resets the box and the follow-up store at the
start and leaves the standing clean state (1 sample email, no follow-ups).
"""
import json, os, smtplib, sys, time, urllib.error, urllib.parse, urllib.request
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
sys.path.insert(0, APP_DIR)
import clearday as cd

BASE = "http://127.0.0.1:8080"
MP = "http://127.0.0.1:8025/mailpit"
count = [0]
fails = []

def check(sid, name, cond):
    count[0] += 1
    print(("PASS " if cond else "FAIL ") + sid + " " + name, flush=True)
    if not cond:
        fails.append(sid + " " + name)

def dn(text, lang="en", sender="", subject=""):
    return cd.heuristic_transform(text, sender, subject, lang)["dates_numbers"]

# ============================ UNIT (60) ============================
def unit():
    # Dates - English formats (U01-U14)
    check("U01", "weekday month day", dn("The meeting is on Tuesday November 24.") == ["Tuesday November 24"])
    check("U02", "moved-from pair, in order, nothing else", dn("The meeting moved from Monday November 23 to Tuesday November 24.") == ["Monday November 23", "Tuesday November 24"])
    check("U03", "reply-before date", dn("Please reply before Friday November 27.") == ["Friday November 27"])
    check("U04", "US slash date", dn("The form is due 11/24/2026.") == ["11/24/2026"])
    check("U05", "ISO date", dn("The deadline is 2026-11-30.") == ["2026-11-30"])
    check("U06", "ordinal + 24h time", dn("See you November 27th at 17:30.") == ["November 27th", "17:30"])
    check("U07", "month day, year", dn("Meet on March 3, 2026 at noon.") == ["March 3, 2026"])
    check("U08", "US dash date", dn("The visit is on 11-24-2026.") == ["11-24-2026"])
    check("U09", "AM/PM one token; single-digit room skipped", dn("It starts at 5:15 PM in Room 4.") == ["5:15 PM"])
    check("U10", "midnight AM", dn("Call at 12:00 AM if needed.") == ["12:00 AM"])
    check("U11", "bare time", dn("The train leaves at 5:15.") == ["5:15"])
    check("U12", "impossible date copied verbatim (rules never validate)", dn("Payment due February 30, 2026.") == ["February 30, 2026"])
    sample = open(os.path.join(APP_DIR, "sample_email.txt")).read()
    check("U13", "the real sample email", dn(sample) == ["Monday November 23", "Tuesday November 24", "5:15 PM", "Friday November 27"])
    check("U14", "same date twice -> once (dedupe)", dn("Meet March 3. Again: March 3 works.") == ["March 3"])
    # Money & numbers (U15-U24)
    check("U15", "money with cents", dn("The cost is $1,250.50 total.") == ["$1,250.50"])
    check("U16", "single-digit money counts", dn("Tickets are $5 each.") == ["$5"])
    check("U17", "room + people", dn("Room 412 holds 37 people.") == ["412", "37"])
    check("U18", "decimal hours", dn("It takes 3.5 hours.") == ["3.5"])
    check("U19", "comma-grouped people", dn("About 1,250 people came.") == ["1,250"])
    check("U20", "money then people, source order", dn("The fee is $25 and the room holds 40 people.") == ["$25", "40"])
    check("U21", "bare year is a plain number", dn("We meet in 2026 to plan.") == ["2026"])
    check("U22", "single digits only -> nothing", dn("Room 4 is on floor 2.") == [])
    r = dn("Meet March 3, April 4, and May 5. Room 412 holds 37 people. It costs $25 and $30. Call 5551234.")
    check("U23", "cap of 6, dates first", len(r) == 6 and r[:3] == ["March 3", "April 4", "May 5"])
    check("U24", "two prices, exactly as written", dn("Pay $1,250.50, not $1,250.51.") == ["$1,250.50", "$1,250.51"])
    # Guards (U25-U32)
    check("U25", "phone number never extracted", dn("Call 415-555-0132 today.") == [])
    check("U26", "a range is not a date", dn("Open from 10-12 on weekdays.") == [])
    check("U27", "a fraction is not a slash date", dn("Use 1/2 cup of sugar.") == [])
    check("U28", "day inside a date is not listed twice", dn("On November 24 the office closes.") == ["November 24"])
    check("U29", "ISO vs bare year separated by spans", dn("In 2026-11-30 we met.") == ["2026-11-30"] and dn("In 2026 we met.") == ["2026"])
    check("U30", "dash fragment rejected", dn("The code is 555-0132.") == [])
    check("U31", "day-first form: only the number, no invented date", dn("See you on the 27th of November.") == ["27"])
    check("U32", "long digit run is a number", dn("Order #12345 shipped.") == ["12345"])
    # No invention (U33-U38)
    check("U33", "dateless hello -> nothing", dn("Hello, just checking in. Hope you are well.") == [])
    r = cd.heuristic_transform("", "", "")
    check("U34", "empty input -> no dates, no actions (nothing invented)", r["dates_numbers"] == [] and r["actions"] == [])
    r = cd.heuristic_transform("Please reply.", "", "")
    check("U35", "no subject -> what falls back to the sentence", r["dates_numbers"] == [] and r["what"] == "Please reply.")
    check("U36", "'tomorrow' is never turned into a date", dn("Can we talk tomorrow?") == [])
    check("U37", "relative weekday is not a date", dn("The meeting is next Friday.") == [])
    r = cd.heuristic_transform("A plain note.", "", "")
    check("U38", "no sender -> Unknown sender", r["sender"] == "Unknown sender" and r["dates_numbers"] == [])
    # Spanish (U39-U44)
    check("U39", "es weekday date", dn("La reunión es el martes 24 de noviembre.", "es") == ["martes 24 de noviembre"])
    check("U40", "es full date with year", dn("El plazo es el 24 de noviembre de 2026.", "es") == ["24 de noviembre de 2026"])
    check("U41", "es time with p. m.", "5:15 p. m." in dn("A las 5:15 p. m. en el salón.", "es"))
    check("U42", "es date, no English phantom", dn("Por favor responda antes del 28 de noviembre.", "es") == ["28 de noviembre"])
    r = cd.heuristic_transform("Hola, solo escribo para saludar.", "", "", "es")
    check("U43", "es dateless", r["dates_numbers"] == [] and r["lang"] == "es")
    r = cd.heuristic_transform("Hola, la reunión es el martes.", "", "", "es")
    check("U44", "es facts keys + es steps", list(r["facts"].keys()) == ["Quién", "Qué"] and r["steps"] == cd.CORE["es"]["steps"])
    # Vietnamese (U45-U49)
    check("U45", "vi date", dn("Cuộc họp vào ngày 24 tháng 11.", "vi") == ["ngày 24 tháng 11"])
    check("U46", "vi full date with year", dn("Hạn chót là ngày 24 tháng 11 năm 2026.", "vi") == ["ngày 24 tháng 11 năm 2026"])
    check("U47", "vi word time", dn("Lúc 17 giờ 15 tại phòng họp.", "vi") == ["17 giờ 15"])
    check("U48", "vi colon time", dn("Bắt đầu lúc 5:15.", "vi") == ["5:15"])
    r = cd.heuristic_transform("Xin chào, tôi chỉ kiểm tra.", "", "", "vi")
    check("U49", "vi dateless", r["dates_numbers"] == [] and r["lang"] == "vi")
    # Grounding filter (U50-U57)
    a = cd._allowed_tokens("Lunch is on March 3. The room holds 40 people.", "en")
    out = cd._strip_ungrounded("Pay $999 by January 40, or confirm March 3 for 40 people, not 41, at 9:99 PM", a, "en")
    check("U50", "invented $999 / January 40 / 41 / 9:99 cut; real kept", "$999" not in out and "January 40" not in out and "41" not in out and "9:99" not in out and "March 3" in out and "40 people" in out)
    a = cd._allowed_tokens("The fee costs $25 today.", "en")
    out = cd._strip_ungrounded("Pay $25 today, not $26", a, "en")
    check("U51", "grounded $25 kept, invented $26 cut", "$25" in out and "$26" not in out)
    a = cd._allowed_tokens("See you November 24.", "en")
    out = cd._strip_ungrounded("See you November 24 or November 25", a, "en")
    check("U52", "real 2-digit-day date keeps its day; invented date cut", "November 24" in out and "November 25" not in out)
    out = cd._strip_ungrounded("Thank you for your message", {"march 3"}, "en")
    check("U53", "a sentence with no tokens passes unchanged", out == "Thank you for your message")
    out = cd._strip_ungrounded("Meet March 3 at 5:15 PM, room 412", set(), "en")
    check("U54", "empty allowed set -> no digits survive", not any(c.isdigit() for c in out))
    check("U55", "ordinal normalized in allowed tokens", cd._allowed_tokens("See you November 27th", "en") == {"november 27"})
    check("U56", "$ and comma normalized in allowed tokens", cd._allowed_tokens("$1,250.50 fee", "en") == {"1250.50"})
    a = cd._allowed_tokens("La cita es el 24 de noviembre.", "es")
    out = cd._strip_ungrounded("el 24 de noviembre o el 25 de noviembre", a, "es")
    check("U57", "es: real date keeps its day; invented es date cut", "24 de noviembre" in out and "25" not in out)
    # Transform structure (U58-U60)
    r = cd.heuristic_transform("Please reply. Please confirm. Please bring ID. Please send the form.", "Ana", "Note")
    check("U58", "max 3 actions at rules level", len(r["actions"]) == 3)
    r = cd.heuristic_transform("Just a plain note with nothing special.", "Ana", "Note")
    check("U59", "no hints -> fallback action + fixed steps", r["actions"] == ["Read the key facts below"] and r["steps"] == cd.CORE["en"]["steps"])
    r = cd.heuristic_transform("The meeting is on March 3.", "Ana", "Note", "fr")
    check("U60", "unsupported lang falls back to English, no crash", r["lang"] == "en" and r["dates_numbers"] == ["March 3"])

# ============================ LIVE (40) ============================
def _open(req, timeout=120, tries=3):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode(errors="replace"), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors="replace"), e.headers
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(3)
    raise last

def get(path, timeout=120):
    code, body, _ = _open(urllib.request.Request(BASE + path), timeout=timeout)
    return code, body

def post(path, fields, timeout=180):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    code, body, _ = _open(req, timeout=timeout)
    return code, body

def api_post(payload, raw=None, timeout=180):
    body = raw if raw is not None else json.dumps(payload).encode()
    req = urllib.request.Request(BASE + "/api/clear", data=body, headers={"Content-Type": "application/json"})
    code, text, _ = _open(req, timeout=timeout)
    try:
        return code, json.loads(text)
    except Exception:
        return code, {}

def api_followups():
    code, body, hdr = _open(urllib.request.Request(BASE + "/api/followups"), timeout=30)
    return code, json.loads(body), hdr

def mp_list():
    for _ in range(4):
        try:
            req = urllib.request.Request(MP + "/api/v1/messages?limit=50", headers={"User-Agent": "ClearDay/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2)
    raise RuntimeError("mailpit list failed")

def mp_delete_all():
    for _ in range(4):
        try:
            req = urllib.request.Request(MP + "/api/v1/messages", method="DELETE")
            urllib.request.urlopen(req, timeout=20).read()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("mailpit delete failed")

def find_id(subject):
    for m in mp_list()["messages"]:
        if m.get("Subject") == subject:
            return m["ID"]
    return ""

def send_mail(frm, subject, text):
    m = EmailMessage()
    m["From"] = frm; m["To"] = "you@clearday.demo"; m["Subject"] = subject
    m.set_content(text)
    s = smtplib.SMTP("127.0.0.1", 1025, timeout=15)
    s.send_message(m); s.quit()

def reset_state():
    try:
        os.remove(os.path.join(APP_DIR, "memory.json"))
    except Exception:
        pass
    mp_delete_all()
    get("/inbox?lang=en")  # re-seeds Maria
    time.sleep(1)

def live():
    reset_state()
    maria = find_id("Board meeting moved")
    # Followups API (L15-L18) - store starts empty by reset
    code, f, hdr = api_followups()
    check("L15", "followups: empty store -> count 0, empty list", code == 200 and f.get("count") == 0 and f.get("followups") == [])
    check("L18", "followups: Content-Type is JSON", "application/json" in (hdr.get("Content-Type") or ""))
    get("/inbox/clear?id=" + maria + "&lang=en")
    code, f, _ = api_followups()
    mine = [i for i in f["followups"] if i.get("mid") == maria]
    check("L16", "followups: cleared email appears by mid; NO address field is published", len(mine) == 1 and "addr" not in mine[0])
    code, spage = post("/reply/send", {"mid": maria, "to": "maria.lopez@example.org", "subject": "Re: Board meeting moved", "body": "Scenario suite reply - confirmed, thank you.", "lang": "en"})
    code, f, _ = api_followups()
    check("L17", "followups: sending the reply closes the follow-up", all(i.get("mid") != maria for i in f["followups"]))
    # API happy paths (L01-L08)
    sample = open(os.path.join(APP_DIR, "sample_email.txt")).read()
    code, r = api_post({"text": sample, "sender": "Maria Lopez", "subject": "Board meeting moved", "lang": "en"})
    check("L01", "api: the sample email, exact 4 dates", code == 200 and r.get("dates_numbers") == ["Monday November 23", "Tuesday November 24", "5:15 PM", "Friday November 27"])
    code, r = api_post({"text": "The form is due 11/24/2026. Please reply."})
    check("L02", "api: slash date", code == 200 and r.get("dates_numbers") == ["11/24/2026"])
    code, r = api_post({"text": "Hello, just checking in. Hope you are well."})
    check("L03", "api: dateless -> empty list", code == 200 and r.get("dates_numbers") == [])
    code, r = api_post({"text": "La reunión es el martes 24 de noviembre.", "lang": "es"})
    check("L04", "api: Spanish date + lang es", code == 200 and r.get("dates_numbers") == ["martes 24 de noviembre"] and r.get("lang") == "es")
    code, r = api_post({"text": "Cuộc họp vào ngày 24 tháng 11.", "lang": "vi"})
    check("L05", "api: Vietnamese date + lang vi", code == 200 and r.get("dates_numbers") == ["ngày 24 tháng 11"] and r.get("lang") == "vi")
    code, r = api_post({"text": "Please reply to confirm."})
    check("L06", "api: no sender/subject -> Unknown sender, all keys present", code == 200 and r.get("sender") == "Unknown sender" and all(k in r for k in ("what", "actions", "facts", "dates_numbers", "source", "lang")))
    code, r = api_post({"text": "Room 412 holds 37 people. The cost is $1,250.50."})
    check("L07", "api: numbers in text order", code == 200 and r.get("dates_numbers") == ["412", "37", "$1,250.50"])
    code, r = api_post({"text": "Call 415-555-0132. Open 10-12."})
    check("L08", "api: phone + range guards hold", code == 200 and r.get("dates_numbers") == [])
    # API errors (L09-L14)
    code, r = api_post({})
    check("L09", "api: no text field -> 400 JSON error", code == 400 and "error" in r)
    code, r = api_post({"text": ""})
    check("L10", "api: empty text -> 400", code == 400 and "error" in r)
    code, r = api_post(None, raw=b"text=hello")
    check("L11", "api: non-JSON body -> 400, never a stack page", code == 400 and "error" in r)
    code, r = api_post({"text": "x" * 60000})
    check("L12", "api: 60,000 chars -> 4xx, no clear page", code in (400, 413))
    code, _b = get("/api/clear")
    check("L13", "api: GET on the POST door -> 404", code == 404)
    code, r = api_post({"text": "Please reply.", "lang": "fr"})
    check("L14", "api: unknown lang -> English fallback", code == 200 and r.get("lang") == "en" and r.get("dates_numbers") == [])
    # Bulk (L19-L26)
    mp_delete_all(); time.sleep(1)
    code, bpage = post("/bulk/clear", {"lang": "en"})
    check("L19", "bulk: empty inbox -> 200, 0 cleared, no crash", code == 200 and "<b>0</b>" in bpage)
    code, bpage = get("/bulk")
    check("L20", "bulk: empty inbox landing shows the empty note (no button to press)", code == 200 and "The inbox is empty" in bpage)
    post("/inbox/fresh", {}); time.sleep(1)
    code, bpage = post("/bulk/clear", {"lang": "en"})
    cards = bpage.split("class='box blue'")
    check("L21", "bulk: 1 email -> exactly 1 summary card naming Maria + subject + her date", code == 200 and len(cards) - 1 == 1 and "Maria Lopez" in bpage and "Board meeting moved" in bpage and "Tuesday November 24" in bpage)
    check("L22", "bulk: combined list heading + Maria's other dates on her card", "EVERYTHING YOU MUST DO" in bpage and "5:15 PM" in bpage and "Friday November 27" in bpage)
    send_mail("Dana Ruiz <dana@example.org>", "Form due", "The form is due 11/24/2026. Please reply to confirm.")
    send_mail("Sam Ortiz <sam@example.org>", "Deadline", "The deadline is 2026-11-30. Please reply.")
    time.sleep(1)
    before = mp_list()["total"]
    code, bpage = post("/bulk/clear", {"lang": "en"}, timeout=300)
    cards = bpage.split("class='box blue'")[1:]
    def card_with(token):
        for c in cards:
            if token in c:
                return c
        return ""
    check("L23", "bulk: 3 emails -> 3 cards, each with ONLY its own date", len(cards) == 3 and "2026-11-30" not in card_with("11/24/2026") and "Tuesday November 24" not in card_with("11/24/2026") and "11/24/2026" not in card_with("2026-11-30") and "11/24/2026" not in card_with("Tuesday November 24") and "2026-11-30" not in card_with("Tuesday November 24"))
    combined = bpage.split("class='box blue'")[0]
    check("L24", "bulk: combined list aggregates actions from all 3 emails", combined.count("&#9654;") >= 3)
    check("L25", "bulk: the inbox itself is untouched (nothing deleted, nothing sent)", mp_list()["total"] == before)
    code, bpage2 = post("/bulk/clear", {"lang": "en"}, timeout=300)
    check("L26", "bulk: a second press shows the same summary count (idempotent)", code == 200 and len(bpage2.split("class='box blue'")) - 1 == 3)
    # Pages regression (L27-L34)
    code, home = get("/")
    check("L27", "home: one Read-my-story button + the hero", code == 200 and home.count("class='btn rawbtn'") == 1 and "Long message in" in home)
    code, page = get("/?sample=1&lang=en")
    check("L28", "sample button fills the form (Maria + Room 4)", code == 200 and "value='Maria Lopez'" in page and "Room 4" in page)
    code, page = post("/", {"sender": "A", "subject": "B", "text": "Hello <b>ZZTEST</b> world", "lang": "en"})
    check("L29", "paste: HTML is escaped, never rendered", code == 200 and "<b>ZZTEST</b>" not in page)
    code, page = post("/", {"sender": "A", "subject": "B", "text": "x" * 60000, "lang": "en"})
    check("L30", "paste: 60,000 chars -> polite too-long refusal", code == 200 and "too long" in page)
    code, page = get("/why")
    check("L31", "why page: research markers", code == 200 and "Why the cream page? For judges" in page and "WCAG 2.2 AA" in page)
    code, page = get("/connected", timeout=180)
    check("L32", "connected: page shape only (LIVE/DOWN is the provider's, not asserted)", code == 200 and "No typed-in numbers" in page)
    try:
        os.remove(os.path.join(APP_DIR, "memory.json"))
    except Exception:
        pass
    code, page = get("/followups")
    check("L33", "followups: clean state shows the empty marker", code == 200 and "No follow-ups waiting" in page)
    import http.client as _hc
    before = mp_list()["total"]
    c = _hc.HTTPConnection("127.0.0.1", 8080, timeout=15)
    c.request("DELETE", "/mailpit/api/v1/messages"); rr = c.getresponse(); rr.read(); c.close()
    check("L34", "proxy: a write through the public Mailpit door -> 403, inbox intact", rr.status == 403 and mp_list()["total"] == before)
    # Reply mechanics (L35-L40)
    maria = find_id("Board meeting moved")
    get("/inbox/clear?id=" + maria + "&lang=en")
    before = mp_list()["total"]
    code, dpage = post("/reply", {"mid": maria, "lang": "en"})
    check("L35", "reply: draft page first - textarea + Send button, NOTHING sent", code == 200 and "YOUR REPLY DRAFT" in dpage and "<textarea" in dpage and "name='body'" in dpage and "Send this reply" in dpage and mp_list()["total"] == before)
    code, spage = post("/reply/send", {"mid": maria, "to": "maria.lopez@example.org", "subject": "Re: Board meeting moved", "body": "Scenario suite edited words - I confirm.", "lang": "en"})
    msgs = mp_list()["messages"]
    delivered = ""
    for m in msgs:
        if (m.get("Subject") or "") == "Re: Board meeting moved":
            req = urllib.request.Request(MP + "/api/v1/message/" + m["ID"], headers={"User-Agent": "ClearDay/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r2:
                delivered = json.loads(r2.read()).get("Text") or ""
            break
    check("L36", "reply send: sent page + both-emails button + edited words delivered", code == 200 and "See both emails in Mailpit" in spage and mp_list()["total"] == before + 1 and "Scenario suite edited words" in delivered)
    before = mp_list()["total"]
    code, spage = post("/reply/send", {"mid": maria, "to": "stranger@example.org", "subject": "Re: Board meeting moved", "body": "planted", "lang": "en"})
    check("L37", "reply gate: a wrong address is refused, nothing sent", mp_list()["total"] == before)
    code, dpage = post("/reply", {"sender": "Nobody Here", "subject": "Unmatched subject", "text": "A note with no date. Please reply.", "lang": "en"})
    check("L38", "reply paste: unmatched sender -> NO SEND BUTTON, no send form", code == 200 and "NO SEND BUTTON" in dpage and "/reply/send" not in dpage)
    mp_delete_all(); get("/inbox?lang=en"); time.sleep(1)
    sample = open(os.path.join(APP_DIR, "sample_email.txt")).read()
    code, dpage = post("/reply", {"sender": "", "subject": "", "text": sample, "lang": "en"})
    check("L39", "reply paste: blank/blank adopts Maria - her address + a send form", code == 200 and "maria.lopez@example.org" in dpage and "/reply/send" in dpage)
    before = mp_list()["total"]
    code, _b = get("/reply/send")
    check("L40", "reply: GET on the send door -> 404, nothing sent", code == 404 and mp_list()["total"] == before)
    # leave the standing clean state
    reset_state()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("unit", "all"):
        unit()
    if mode in ("live", "all"):
        live()
    print(f"SCENARIOS TOTAL: {count[0] - len(fails)}/{count[0]}", flush=True)
    if fails:
        print("FAILED:", "; ".join(fails), flush=True)
    sys.exit(1 if fails else 0)
