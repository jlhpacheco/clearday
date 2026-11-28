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

def dl(text, lang="en", sender="", subject=""):
    return cd.heuristic_transform(text, sender, subject, lang)["dates_labeled"]

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

    # Guards (U61-U66) - Nov 26 evening, on the swarm's word (Technical + Skeptic lenses)
    h = cd.heuristic_transform("We meet Jan. 5 at noon to plan the spring fair.", "Ana Ruiz", "Planning", "en")
    check("U61", "dotted month date extracted: 'Jan. 5' lands in the box", "Jan. 5" in h["dates_numbers"])
    a = cd._allowed_tokens("We meet Jan. 5 at noon.", "en")
    out = cd._strip_ungrounded("Meet Jan. 5 or Jan. 9", a, "en")
    check("U62", "dotted date grounded: real 'Jan. 5' kept, invented 'Jan. 9' cut", "Jan. 5" in out and "Jan. 9" not in out)
    src_t = "The meeting is in Room 412 on Friday. Maria will bring the list."
    f = cd._ground_facts({"Due January 40": "Friday", "importance": "high", "deadline": "matters", "Room": "Room 412"}, cd._allowed_tokens(src_t, "en"), src_t, "en")
    check("U63", "fact KEYS grounded: 'January 40' stripped from a key", all("January 40" not in k for k in f))
    check("U64", "junk fact rows dropped, anchored rows kept", "importance" not in f and "deadline" not in f and f.get("Room") == "Room 412")
    r = cd.transform("Thank you for the wonderful evening. We loved the food and the company. No reply is needed at all.", "Ana Ruiz", "Thank you", "en")
    check("U65", "duties guard: a no-ask email gets the honest line, not invented duties", r["actions"] == ["This email asks nothing of you"])
    r = cd.transform(sample, "Maria Lopez", "Board meeting moved", "en")
    check("U66", "duties guard stays silent when the email asks", r["actions"] != ["This email asks nothing of you"] and len(r["actions"]) >= 1)
    # Labeled dates (U67-U69) - Nov 26 late, Jose Luis's own format
    check("U67", "labeled dates: the sample reads exactly as Jose Luis wrote it", dl(sample, "en", "Maria Lopez", "Board meeting moved") == [
        {"label": "Original Meeting Date", "value": "Monday, November 23"},
        {"label": "New Meeting Date", "value": "Tuesday, November 24 at 5:15 PM"},
        {"label": "Reply by", "value": "Friday, November 27"}])
    check("U68", "labeled dates: pay-by takes its label from the email's own verb", dl("Please pay the invoice by March 5.") == [{"label": "Pay by", "value": "March 5"}])
    check("U69", "labeled dates: no cue words -> NO label is invented", dl("The picnic is on July 4.") == [{"label": "", "value": "July 4"}])
    lab = dl(sample, "en", "Maria Lopez", "Board meeting moved")
    bad = {"Original Meeting Date": "Monday", "New Meeting Date": "Tuesday, at 5:15 PM", "Reply by": "Friday",
           "Location": "Room 4 and Zoom", "When": "November 24"}
    check("U70", "facts guard: date-label rows and bare weekdays can NEVER stand as facts", cd._drop_date_facts(bad, lab) == {"Location": "Room 4 and Zoom"})
    check("U71", "duties guard: a no-ask sentence can NOT erase a real ask in the next one (skeptic P10)", cd._has_ask("No need to reply to this note. But please send me the signed form by March 3 so we can file it on time.", "en") is True)
    check("U72", "duties guard: an English ask is seen even when the picker says Spanish (skeptic P5)", cd._has_ask("The meeting moved to Tuesday, November 24 at 5:15 PM. Please reply before Friday, November 27 to confirm.", "es") is True)
    check("U73", "duties guard: a question mark alone is conversation, not a duty (skeptic P9)", cd._has_ask("Did you see the game last night? What a finish! Best game of the season, easily.", "en") is False)
    check("U74", "duties guard: the noun 'deadline' alone asks nothing (skeptic P6)", cd._has_ask("Hi, the workshop is in Room 412. It matters a lot. This is high priority and very important. The deadline is crucial and the stakes are high.", "en") is False)
    check("U75", "duties guard: Spanish imperative 'confirma' is a real ask (round-4 skeptic)", cd._has_ask("Hola, por favor confirma tu asistencia antes del viernes. Gracias.", "es") is True)
    check("U76", "duties guard: Spanish imperative 'responde' is a real ask even under the English picker (round-4 skeptic)", cd._has_ask("Por favor responde a este mensaje hoy.", "en") is True)
    check("U77", "duties guard: formal 'sirvase firmar' + pronoun tail 'devolverlo' are real asks (round-5 skeptic)", cd._has_ask("Sírvase firmar el documento y devolverlo antes del viernes.", "es") is True)
    check("U78", "duties guard: formal 'tenga a bien remitir' is a real ask (round-5 skeptic)", cd._has_ask("Tenga a bien remitir el pago antes del día 5.", "es") is True)
    check("U79", "duties guard: 'no es necesario que responda' asks nothing - the subjunctive cannot slip past the lift (round-5 skeptic)", cd._has_ask("Solo para su información: la reunión cambió de sala. No es necesario que responda.", "es") is False)
    check("U80", "duties guard: a pronoun tail alone ('devolverlo') is a real ask (round-5 skeptic)", cd._has_ask("El paquete llegó hoy. Devolverlo antes del viernes, por favor.", "es") is True)
    check("U81", "duties guard: accented glued form 'envíelos' is a real ask (round-6 skeptic)", cd._has_ask("Adjunto los dos formularios. Envíelos antes del viernes, por favor.", "es") is True)
    check("U82", "duties guard: accented glued form 'devuélvalo' is a real ask (round-6 skeptic)", cd._has_ask("Devuélvalo a la oficina antes del lunes.", "es") is True)
    check("U83", "duties guard: accented glued forms 'fírmelas' + 'envíelas' are real asks (round-6 skeptic)", cd._has_ask("Fírmelas y envíelas hoy.", "es") is True)
    check("U84", "duties guard: formal English 'kindly requested to remit' is a real ask (round-6 skeptic)", cd._has_ask("You are kindly requested to remit payment of the invoice before Friday.", "en") is True)
    import app as _app, tempfile as _tf, os as _os
    _old_mf = _app.MEMORY_FILE
    try:
        _app.MEMORY_FILE = _os.path.join(_tf.mkdtemp(), "memory.json")
        _app.save_memory([{"what": "x", "sender": "y", "lang": "en"}])
        open(_app.MEMORY_FILE, "w").write("{ torn")
        check("U85", "memory: a torn main file falls back to the .bak - follow-ups survive a crash (round-6 technical)", _app.load_memory() == [{"what": "x", "sender": "y", "lang": "en"}])
    finally:
        _app.MEMORY_FILE = _old_mf
    check("U86", "duties guard: two-pronoun stack 'envíemelos' (send them to me) is a real ask (round-7 skeptic)", cd._has_ask("Le adjunto las dos copias. Envíemelos firmados antes del viernes, por favor.", "es") is True)
    check("U87", "duties guard: se-stacks 'fírmeselo' + 'entrégueselo' are real asks (round-7 skeptic)", cd._has_ask("Fírmeselo y entrégueselo al mensajero hoy.", "es") is True)
    check("U88", "duties guard: gerund glue 'enviándolos' is a real ask (round-7 skeptic)", cd._has_ask("Podrá cerrar el expediente enviándolos antes del viernes.", "es") is True)
    check("U89", "duties guard: formal Vietnamese 'chuyển khoản' (transfer the money) is a real ask (round-7 skeptic)", cd._has_ask("Xin vui lòng chuyển khoản số tiền còn lại trước thứ Sáu.", "vi") is True)
    check("U90", "duties guard: formal Vietnamese 'nộp' (submit) is a real ask (round-7 skeptic)", cd._has_ask("Xin vui lòng nộp lại hồ sơ trước ngày 5.", "vi") is True)
    check("U91", "duties guard: passive 'must be signed and returned by Friday' is a real ask (round-7 skeptic)", cd._has_ask("Please be advised that the enclosed form must be signed and returned by Friday.", "en") is True)
    check("U92", "duties guard: 'no hace falta firmarlo ni enviarlo' asks NOTHING - the no-need phrase governs its glued verbs (round-7 skeptic)", cd._has_ask("No hace falta firmarlo ni enviarlo.", "es") is False)
    check("U93", "duties guard: 'no hace falta firmar' (plain infinitive) asks nothing either (round-7 skeptic family)", cd._has_ask("No hace falta firmar el documento.", "es") is False)
    check("U94", "duties guard: a no-need clause does NOT erase a real duty later in the email (guard stays honest)", cd._has_ask("No hace falta que traigas nada, solo firma aquí.", "es") is True)
    check("U95", "duties guard: tú subjunctive 'que pagues' is a real ask (round-8 skeptic)", cd._has_ask("Te pido que pagues la factura antes del viernes.", "es") is True)
    check("U96", "duties guard: tú subjunctive 'que lo firmes' is a real ask (round-8 skeptic)", cd._has_ask("Quiero que lo firmes hoy mismo.", "es") is True)
    check("U97", "duties guard: decir family stack 'dígamelo' is a real ask (round-8 skeptic)", cd._has_ask("Dígamelo antes del viernes, por favor.", "es") is True)
    check("U98", "duties guard: passive 'must be paid by Friday' is a real ask (round-8 skeptic)", cd._has_ask("Please be advised: the invoice must be paid by Friday.", "en") is True)
    check("U99", "duties guard: passive 'must be sent to our office by Friday' is a real ask (round-8 skeptic)", cd._has_ask("The signed form must be sent to our office by Friday.", "en") is True)
    check("U100", "duties guard: Vietnamese 'phản hồi' (respond) is a real ask (round-8 skeptic)", cd._has_ask("Vui lòng phản hồi email này trước thứ Sáu.", "vi") is True)
    check("U101", "duties guard: the standard 'Do not reply' footer asks NOTHING (round-8 skeptic)", cd._has_ask("This is an automated message. Do not reply.", "en") is False)
    check("U102", "duties guard: 'don't need to reply' asks nothing (round-8 skeptic)", cd._has_ask("You don't need to reply to this email — it is just a receipt.", "en") is False)
    check("U103", "duties guard: 'no es necesario por ahora responder' - an adverb between phrase and verb cannot resurrect a duty (round-8 skeptic)", cd._has_ask("No es necesario por ahora responder a este mensaje.", "es") is False)
    check("U104", "duties guard: 'no hace falta, por ahora, firmar nada' - commas cannot resurrect a duty either (round-8 skeptic)", cd._has_ask("No hace falta, por ahora, firmar nada.", "es") is False)
    check("U105", "duties guard: a curly apostrophe (phones type it) cannot defeat 'don't need to' (round-9 technical note)", cd._has_ask("You don\u2019t need to reply to this email.", "en") is False)
    check("U106", "duties guard: tú imperative glued 'págalo' is a real ask (round-9 skeptic)", cd._has_ask("Págalo antes del viernes, por favor.", "es") is True)
    check("U107", "duties guard: tú imperative 'devuelve' is a real ask (round-9 skeptic)", cd._has_ask("Devuelve el libro a la biblioteca mañana.", "es") is True)
    check("U108", "duties guard: tú imperative 'trae' is a real ask (round-9 skeptic)", cd._has_ask("Trae tu identificación el lunes.", "es") is True)
    check("U109", "duties guard: 'no tienes que responder' asks nothing (round-9 skeptic)", cd._has_ask("No tienes que responder a este mensaje.", "es") is False)
    check("U110", "duties guard: 'don't have to sign' asks nothing (round-9 skeptic)", cd._has_ask("You don't have to sign anything.", "en") is False)
    check("U111", "duties guard: 'no hace falta que lo firmes ni que lo envíes' - the que-chain lifts whole (round-9 skeptic)", cd._has_ask("No hace falta que lo firmes ni que lo envíes.", "es") is False)
    check("U112", "duties guard: vosotros 'firmad... enviadlo' is a real ask (round-9 skeptic)", cd._has_ask("Firmad el documento y enviadlo antes del viernes.", "es") is True)
    check("U113", "duties guard: 'would you mind sending' is a real ask (round-9 skeptic)", cd._has_ask("Would you mind sending the report by Thursday?", "en") is True)
    check("U114", "duties guard: 'favor de no responder' - the formal Latin American do-not-reply - asks NOTHING (round-10 skeptic)", cd._has_ask("Favor de no responder a este correo.", "es") is False)
    check("U115", "duties guard: 'se ruega no responder' asks nothing - the negated twin of a formal ask (round-10 skeptic)", cd._has_ask("Se ruega no responder a este correo.", "es") is False)
    check("U116", "duties guard: 'sin necesidad de firmar nada' asks nothing (round-10 skeptic)", cd._has_ask("Sin necesidad de firmar nada, solo es un aviso informativo.", "es") is False)
    check("U117", "duties guard: Vietnamese 'không cần nộp' asks nothing - the governed lift Spanish and English already had (round-10 skeptic)", cd._has_ask("Không cần nộp hồ sơ, chúng tôi đã có bản sao.", "vi") is False)
    check("U118", "duties guard: Vietnamese 'không cần phải nộp' asks nothing (round-10 skeptic)", cd._has_ask("Bạn không cần phải nộp hồ sơ đâu, chỉ để xem thôi.", "vi") is False)
    check("U119", "duties guard: 'you needn't sign' asks nothing (round-10 skeptic)", cd._has_ask("You needn't sign anything at this stage.", "en") is False)
    check("U120", "duties guard: the POSITIVE 'favor de responder' still asks - the negated lift must not eat real requests (round-10 skeptic control)", cd._has_ask("Favor de responder a este correo antes del viernes.", "es") is True)
    check("U121", "duties guard: 'ni que le respondas' - the chain pronoun set is complete again after the composition rebuild (round-10 simplicity catch)", cd._has_ask("No hace falta que lo firmes ni que le respondas.", "es") is False)
    check("U122", "duties guard: the PLAIN 'por favor no responda' asks nothing (round-11 skeptic)", cd._has_ask("Por favor no responda a este correo.", "es") is False)
    check("U123", "duties guard: 'te pedimos que no respondas' asks nothing (round-11 skeptic)", cd._has_ask("Te pedimos que no respondas a este correo.", "es") is False)
    check("U124", "duties guard: 'se solicita no responder' asks nothing (round-11 skeptic)", cd._has_ask("Se solicita no responder a este correo.", "es") is False)
    check("U125", "duties guard: a general 'do not send' asks nothing - not just 'do not reply' (round-11 skeptic)", cd._has_ask("Please do not send any documents through this channel.", "en") is False)
    check("U126", "duties guard: Vietnamese 'đừng trả lời' asks nothing - the negative imperative has a lift now (round-11 skeptic)", cd._has_ask("Đừng trả lời email này.", "vi") is False)
    check("U127", "duties guard: the stamp 'for information only - no reply expected' asks nothing (round-11 skeptic)", cd._has_ask("For information only — no reply expected.", "en") is False)
    check("U128", "duties guard: an 'o que lo envíes' chain lifts whole, not just 'ni' chains (round-11 skeptic)", cd._has_ask("No es necesario que firmes el documento o que lo envíes.", "es") is False)
    check("U129", "duties guard: 'no hace falta ni que respondas' - 'ni' before the 'que' cannot defeat the lift (round-11 skeptic)", cd._has_ask("No hace falta ni que respondas a este mensaje.", "es") is False)
    check("U130", "duties guard: 'do not forget to sign' still ASKS - the do-not lift cancels only its own verb (round-11 skeptic control)", cd._has_ask("Do not forget to sign the form and return it by Friday.", "en") is True)
    check("U131", "duties guard: 'đừng quên nộp' still ASKS - don't-forget is a real duty in Vietnamese too (round-11 skeptic control)", cd._has_ask("Đừng quên nộp hồ sơ trước thứ Sáu.", "vi") is True)
    check("U132", "duties guard: 'absténgase de responder' asks nothing - the negation hides in the refrain verb (round-12 skeptic)", cd._has_ask("Absténgase de responder a este correo.", "es") is False)
    check("U133", "duties guard: 'se ruega abstenerse de responder' asks nothing (round-12 skeptic)", cd._has_ask("Se ruega abstenerse de responder a este correo.", "es") is False)
    check("U134", "duties guard: 'te ruego que no respondas' asks nothing - the rogar frame the pedir fix missed (round-12 skeptic)", cd._has_ask("Te ruego que no respondas a este correo.", "es") is False)
    check("U135", "duties guard: 'rogamos no responder' asks nothing (round-12 skeptic)", cd._has_ask("Rogamos no responder a este correo.", "es") is False)
    check("U136", "duties guard: 'never reply' asks nothing - negation by adverb (round-12 skeptic)", cd._has_ask("Never reply to this email address.", "en") is False)
    check("U137", "duties guard: 'we ask that you not reply' asks nothing - the negation sits between you and the verb (round-12 skeptic)", cd._has_ask("We ask that you not reply to this email.", "en") is False)
    check("U138", "duties guard: Vietnamese 'không nên trả lời' asks nothing - the should-not modal (round-12 skeptic)", cd._has_ask("Bạn không nên trả lời email này.", "vi") is False)
    check("U139", "duties guard: Vietnamese 'chớ trả lời' asks nothing - the literary don't (round-12 skeptic)", cd._has_ask("Chớ trả lời email này.", "vi") is False)
    check("U140", "duties guard: the Vietnamese no-need lift governs its 'hay' chain too - 'không cần phải nộp hồ sơ hay trả lời' asks nothing (round-12 skeptic)", cd._has_ask("Bạn không cần phải nộp hồ sơ hay trả lời email này.", "vi") is False)
    check("U141", "duties guard: the bare 'no responda' asks nothing - negation with no frame at all (round-13 skeptic)", cd._has_ask("No responda a este correo.", "es") is False)
    check("U142", "duties guard: the bare infinitive 'no enviar documentos' asks nothing (round-13 skeptic)", cd._has_ask("No enviar documentos por este medio.", "es") is False)
    check("U143", "duties guard: 'evite responder' asks nothing - the avoid frame (round-13 skeptic)", cd._has_ask("Evite responder a este correo.", "es") is False)
    check("U144", "duties guard: 'sírvase no responder' asks nothing - the sírvase frame, negated (round-13 skeptic)", cd._has_ask("Sírvase no responder a este correo.", "es") is False)
    check("U145", "duties guard: 'no se moleste en responder' asks nothing - don't-bother is its own phrase (round-13 skeptic)", cd._has_ask("No se moleste en responder a este correo.", "es") is False)
    check("U146", "duties guard: 'se le pide no responder' asks nothing (round-13 skeptic)", cd._has_ask("Se le pide no responder a este correo.", "es") is False)
    check("U147", "duties guard: 'you need not reply' asks nothing - 'need not' beside 'needn't' (round-13 skeptic)", cd._has_ask("You need not reply to this email.", "en") is False)
    check("U148", "duties guard: the stamp 'no reply is necessary' asks nothing (round-13 skeptic)", cd._has_ask("No reply is necessary.", "en") is False)
    check("U149", "duties guard: Vietnamese 'không phải nộp' asks nothing - it-is-not-that-you-must (round-13 skeptic)", cd._has_ask("Bạn không phải nộp hồ sơ này.", "vi") is False)
    check("U150", "duties guard: 'đừng có trả lời' asks nothing - the có particle cannot shield the verb (round-13 skeptic)", cd._has_ask("Đừng có trả lời email này.", "vi") is False)
    check("U151", "duties guard: 'no firmes todavía; firma la versión final' still ASKS - the bare-no lift cancels only its own verb (round-13 skeptic control)", cd._has_ask("No firmes todavía; firma la versión final cuando llegue.", "es") is True)
    check("U152", "duties guard: 'no lo firmes' asks nothing - a loose pronoun before the verb cannot shield it (round-14 technical)", cd._has_ask("No lo firmes.", "es") is False)
    check("U153", "duties guard: 'no firmes ni le respondas' asks nothing - the chain link takes the governed piece too (round-14 technical)", cd._has_ask("No firmes ni le respondas.", "es") is False)
    check("U154", "duties guard: 'no firmes el documento o lo envíes' asks nothing (round-14 technical)", cd._has_ask("No firmes el documento o lo envíes.", "es") is False)
    check("U155", "duties guard: 'no hay que responder' asks nothing - the impersonal no-need lifts before bare-no can nibble 'no hay' (round-14 skeptic)", cd._has_ask("No hay que responder a este correo.", "es") is False)
    check("U156", "duties guard: 'no hay necesidad de responder' asks nothing (round-14 skeptic)", cd._has_ask("No hay necesidad de responder a este correo.", "es") is False)
    check("U157", "duties guard: 'no es obligatorio responder' asks nothing (round-14 skeptic)", cd._has_ask("No es obligatorio responder a este correo.", "es") is False)
    check("U158", "duties guard: Vietnamese 'không cần thiết phải nộp' asks nothing - the frame carries thiết (round-14 skeptic)", cd._has_ask("Không cần thiết phải nộp hồ sơ.", "vi") is False)
    check("U159", "duties guard: 'you are not required to sign' asks nothing - the governed not-required lift (round-14 skeptic)", cd._has_ask("You are not required to sign this form.", "en") is False)
    check("U160", "duties guard: 'se ruega encarecidamente abstenerse de responder' asks nothing - one adverb cannot reopen the refrain frame (round-14 skeptic)", cd._has_ask("Se ruega encarecidamente abstenerse de responder a este correo.", "es") is False)
    check("U161", "duties guard: a six-word object before the 'o' cannot defeat the chain - 'el documento firmado por el notario' lifts whole (round-14 skeptic)", cd._has_ask("No hace falta que firmes el documento firmado por el notario o que lo envíes.", "es") is False)
    check("U162", "duties guard: positive 'hay que firmar' still ASKS - only the negated frame joined the lift (round-14 skeptic control)", cd._has_ask("Hay que firmar el documento antes del viernes.", "es") is True)
    check("U163", "duties guard: 'se ruega no le respondas' asks nothing - the framed lift's verbs take the governed piece too (round-14 technical, sibling fix)", cd._has_ask("Se ruega no le respondas a este mensaje.", "es") is False)
    check("U164", "duties guard: a run-on cannot hide a duty inside a cancelled chain - 'firmes el documento envía el pago o trae' still ASKS via envía (round-15 technical)", cd._has_ask("No hace falta que firmes el documento envía el pago o trae el recibo", "es") is True)
    check("U165", "duties guard: 'muestra tu teléfono en la puerta' ASKS - show is a duty verb now (round-15 skeptic)", cd._has_ask("Muestra tu teléfono en la puerta.", "es") is True)
    check("U166", "duties guard: 'presenta tu identificación' ASKS (round-15 skeptic)", cd._has_ask("Presenta tu identificación en la entrada.", "es") is True)
    check("U167", "duties guard: 'ven a la oficina' ASKS (round-15 skeptic)", cd._has_ask("Ven a la oficina mañana a las diez.", "es") is True)
    check("U168", "duties guard: Vietnamese 'hãy mang thẻ' ASKS - bring is a duty verb now (round-15 skeptic)", cd._has_ask("Hãy mang thẻ sinh viên khi đến trường.", "vi") is True)
    check("U169", "duties guard: 'no es menester responder' asks nothing (round-15 skeptic)", cd._has_ask("No es menester responder a este correo.", "es") is False)
    check("U170", "duties guard: 'no resulta necesario responder' asks nothing (round-15 skeptic)", cd._has_ask("No resulta necesario responder a este correo.", "es") is False)
    check("U171", "duties guard: 'no se precisa responder' asks nothing (round-15 skeptic)", cd._has_ask("No se precisa responder a este correo.", "es") is False)
    check("U172", "duties guard: 'it is not necessary to sign' asks nothing (round-15 skeptic)", cd._has_ask("It is not necessary to sign this form.", "en") is False)
    check("U173", "duties guard: 'you have no obligation to sign' asks nothing (round-15 skeptic)", cd._has_ask("You have no obligation to sign this form.", "en") is False)
    check("U174", "duties guard: Vietnamese 'không nhất thiết phải trả lời' asks nothing (round-15 skeptic)", cd._has_ask("Bạn không nhất thiết phải trả lời email này.", "vi") is False)
    check("U175", "duties guard: Vietnamese 'không bắt buộc phải nộp' asks nothing (round-15 skeptic)", cd._has_ask("Bạn không bắt buộc phải nộp hồ sơ này.", "vi") is False)
    check("U176", "duties guard: 'se ruega muy encarecidamente abstenerse' asks nothing - two adverbs fit the frame now (round-15 skeptic)", cd._has_ask("Se ruega muy encarecidamente abstenerse de responder a este correo.", "es") is False)
    check("U177", "duties guard: 'se ruega encarecidamente no responder' asks nothing - an adverb cannot split the ruega-no frame (round-15 skeptic)", cd._has_ask("Se ruega encarecidamente no responder a este correo.", "es") is False)
    check("U178", "duties guard: the temper refuses only duty words - a clean six-word object still chains whole (round-15 technical control)", cd._has_ask("No es necesario que firmes el formulario de registro general o que lo envíes.", "es") is False)
    check("U179", "duties guard: the bare-no chain is tempered too - 'no firmes el documento envía el pago o trae' still ASKS (round-15 technical)", cd._has_ask("No firmes el documento envía el pago o trae el recibo", "es") is True)
    check("U180", "duties guard: 'show your phone at the door' ASKS - English learned the physical verbs too (round-16 reader)", cd._has_ask("Show your phone at the door.", "en") is True)
    check("U181", "duties guard: 'present your ID' ASKS (round-16 reader)", cd._has_ask("Present your ID at the entrance.", "en") is True)
    check("U182", "duties guard: 'come to the office' ASKS (round-16 reader)", cd._has_ask("Come to the office tomorrow at ten.", "en") is True)
    check("U183", "duties guard: 'se muestra el saldo' asks nothing - the announcement shape is scoped out (round-16 skeptic)", cd._has_ask("Se muestra el saldo en la pantalla principal.", "es") is False)
    check("U184", "duties guard: 'una muestra gratuita' asks nothing - muestra the noun is scoped out (round-16 skeptic)", cd._has_ask("Adjuntamos una muestra gratuita del producto.", "es") is False)
    check("U185", "duties guard: 'se presenta el nuevo portal' asks nothing (round-16 skeptic)", cd._has_ask("Se presenta el nuevo portal de pagos.", "es") is False)
    check("U186", "duties guard: 'se enseña español a los niños' asks nothing - the school teaches, the reader does not (round-16 skeptic)", cd._has_ask("En esta escuela se enseña español a los niños.", "es") is False)
    check("U187", "duties guard: 'muestra tu credencial' still ASKS - scoping spared the reader-directed imperative (round-16 skeptic control)", cd._has_ask("Muestra tu credencial al entrar.", "es") is True)
    check("U188", "duties guard: a gerund inside the span stops the chain now - 'pagando la cuota o trae' still ASKS (round-16 skeptic)", cd._has_ask("No hace falta que firmes el formulario pagando la cuota o trae el recibo.", "es") is True)
    check("U189", "duties guard: a glued form inside the span stops the chain - 'envíalo o trae' still ASKS (round-16 simplicity)", cd._has_ask("No hace falta que firmes el documento envíalo o trae el recibo.", "es") is True)
    check("U190", "duties guard: 'no se requiere responder' asks nothing (round-16 skeptic)", cd._has_ask("No se requiere responder a este correo.", "es") is False)
    check("U191", "duties guard: 'no corresponde enviar' asks nothing (round-16 skeptic)", cd._has_ask("No corresponde enviar documentos por este medio.", "es") is False)
    check("U192", "duties guard: 'you are not obliged to sign' asks nothing (round-16 skeptic)", cd._has_ask("You are not obliged to sign this form.", "en") is False)
    check("U193", "duties guard: Vietnamese 'không việc gì phải trả lời' asks nothing (round-16 skeptic)", cd._has_ask("Bạn không việc gì phải trả lời email này.", "vi") is False)
    check("U194", "duties guard: 'se ruega de manera muy encarecida abstenerse' asks nothing - the frame takes a short phrase now (round-16 skeptic)", cd._has_ask("Se ruega de manera muy encarecida abstenerse de responder a este correo.", "es") is False)
    check("U195", "duties guard: 'se presenta a la oficina mañana' ASKS again - the stamp steps aside when a place follows (round-17 skeptic)", cd._has_ask("Se presenta a la oficina mañana a las nueve.", "es") is True)
    check("U196", "duties guard: 'se presenta a trabajar' ASKS (round-17 skeptic)", cd._has_ask("El lunes se presenta a trabajar a las ocho.", "es") is True)
    check("U197", "duties guard: 'se muestra el documento al guardia' ASKS - show it to the guard is a duty (round-17 skeptic)", cd._has_ask("Se muestra el documento al guardia al entrar.", "es") is True)
    check("U198", "duties guard: 'se enseña el pasaporte en la puerta' ASKS (round-17 skeptic)", cd._has_ask("Se enseña el pasaporte en la puerta.", "es") is True)
    check("U199", "duties guard: 'se presenta el examen en el aula' asks nothing - no place or time follows the verb (round-17 skeptic control)", cd._has_ask("Se presenta el examen en el aula cuatro.", "es") is False)
    check("U200", "duties guard: 'trae la muestra a la oficina' still ASKS - the noun scope never shadows an imperative (round-17 skeptic control)", cd._has_ask("Trae la muestra a la oficina.", "es") is True)
    check("U201", "duties guard: 'your present address is on file' asks nothing - present the adjective is scoped (round-17 technical)", cd._has_ask("Your present address is on file.", "en") is False)
    check("U202", "duties guard: 'at present, the office is closed' asks nothing (round-17 technical)", cd._has_ask("At present, the office is closed on Fridays.", "en") is False)
    check("U203", "duties guard: 'the present policy stays in effect' asks nothing (round-17 technical)", cd._has_ask("The present policy stays in effect.", "en") is False)
    check("U204", "duties guard: 'the show starts at eight' asks nothing - show the noun is scoped (round-17 technical)", cd._has_ask("The show starts at eight.", "en") is False)
    check("U205", "duties guard: 'come Friday, the office closes early' asks nothing - the idiom is scoped (round-17 technical)", cd._has_ask("Come Friday, the office closes early.", "en") is False)
    check("U206", "duties guard: 'come rain or shine, the picnic is on' asks nothing (round-17 technical)", cd._has_ask("Come rain or shine, the picnic is on.", "en") is False)
    check("U207", "duties guard: 'good news will come' ASKS again - 'will come' was dropped in round 18 because it also ate 'you will come' orders; the third-person invention is the accepted cheaper direction (round-18 technical)", cd._has_ask("Good news will come in the spring newsletter.", "en") is True)
    check("U208", "duties guard: 'please show the letter to the guard' still ASKS - scoping spared the imperative (round-17 technical control)", cd._has_ask("Please show the letter to the guard.", "en") is True)
    check("U209", "duties guard: 'se muestra la nueva tabla de tarifas' asks nothing under the guarded stamp (round-17 skeptic control)", cd._has_ask("Se muestra la nueva tabla de tarifas en la página principal.", "es") is False)
    check("U210", "duties guard: 'se enseña el pasaporte a los agentes en la puerta' ASKS - the recipient no longer pushes the gate out of reach (round-18 skeptic)", cd._has_ask("Se enseña el pasaporte a los agentes en la puerta de embarque.", "es") is True)
    check("U211", "duties guard: 'se presenta en la oficina de recursos humanos mañana' ASKS (round-18 skeptic)", cd._has_ask("Se presenta en la oficina de recursos humanos mañana.", "es") is True)
    check("U212", "duties guard: 'se presenta ante el comité' ASKS - the missing shape joined the list (round-18 skeptic)", cd._has_ask("Se presenta ante el comité el lunes.", "es") is True)
    check("U213", "duties guard: 'se muestra su identificación en recepción' ASKS (round-18 skeptic)", cd._has_ask("Se muestra su identificación en recepción.", "es") is True)
    check("U214", "duties guard: 'se muestra el documento, al guardia' ASKS - the clause span crosses the comma (round-18 technical)", cd._has_ask("Se muestra el documento, al guardia.", "es") is True)
    check("U215", "duties guard: 'se presenta el informe anual en la sesión' asks nothing - a display place is not a destination (round-18 skeptic control)", cd._has_ask("Se presenta el informe anual en la sesión del consejo.", "es") is False)
    check("U216", "duties guard: 'se ruega encarecidamente a todos los vecinos no responder' asks nothing - the frame crosses manner plus addressee now (round-18 skeptic)", cd._has_ask("Se ruega encarecidamente a todos los vecinos no responder a este correo.", "es") is False)
    check("U217", "duties guard: 'se ruega firmar el formulario y no responder' still ASKS - the temper stops the frame at the real duty (round-18 skeptic control)", cd._has_ask("Se ruega firmar el formulario y no responder.", "es") is True)
    check("U218", "duties guard: 'la empresa muestra sus productos' asks nothing - a named subject announcing (round-18 skeptic)", cd._has_ask("La empresa muestra sus productos en la feria anual.", "es") is False)
    check("U219", "duties guard: 'el museo presenta una exposición' asks nothing (round-18 skeptic)", cd._has_ask("El museo presenta una exposición nueva.", "es") is False)
    check("U220", "duties guard: 'la profesora enseña matemáticas' asks nothing (round-18 skeptic)", cd._has_ask("La profesora enseña matemáticas a los niños.", "es") is False)
    check("U221", "duties guard: 'present address proof at the counter' ASKS again - the scope carries 'your' now (round-18 technical)", cd._has_ask("Present address proof at the counter.", "en") is True)
    check("U222", "duties guard: 'you will come to the office tomorrow' ASKS again (round-18 technical)", cd._has_ask("You will come to the office tomorrow.", "en") is True)
    check("U223", "duties guard: 'this gift is a present' asks nothing (round-18 skeptic)", cd._has_ask("This gift is a present for the whole team.", "en") is False)
    check("U224", "duties guard: 'come spring, the garden opens' asks nothing (round-18 skeptic)", cd._has_ask("Come spring, the garden opens to visitors.", "en") is False)
    check("U225", "duties guard: 'show times are posted at the door' asks nothing (round-18 skeptic)", cd._has_ask("Show times are posted at the door.", "en") is False)
    check("U226", "duties guard: 'el solicitante presenta los documentos' ASKS - a reader-role subject never stamps (round-19 skeptic)", cd._has_ask("El solicitante presenta los documentos en la ventanilla.", "es") is True)
    check("U227", "duties guard: 'el participante presenta identificación oficial' ASKS (round-19 skeptic)", cd._has_ask("El participante presenta identificación oficial al entrar.", "es") is True)
    check("U228", "duties guard: 'la secretaria presenta su informe' ASKS - the English scope 'a present' no longer eats the Spanish verb (round-19 technical)", cd._has_ask("La secretaria presenta su informe al director.", "es") is True)
    check("U229", "duties guard: 'el museo de arte presenta' asks nothing - two-word subjects stamp now (round-19 skeptic)", cd._has_ask("El museo de arte presenta una exposición.", "es") is False)
    check("U230", "duties guard: 'el nuevo museo presenta' asks nothing - adjective before the noun (round-19 skeptic)", cd._has_ask("El nuevo museo presenta una exposición.", "es") is False)
    check("U231", "duties guard: 'la empresa familiar muestra' asks nothing - adjective after the noun (round-19 skeptic)", cd._has_ask("La empresa familiar muestra sus productos.", "es") is False)
    check("U232", "duties guard: 'se ruega no enviar documentos ni firmar el registro' asks nothing - the refrain chain crosses the object now (round-19 skeptic)", cd._has_ask("Se ruega a los vecinos no enviar documentos ni firmar el registro.", "es") is False)
    check("U233", "duties guard: 'el nuevo solicitante presenta' still ASKS - the role shield guards both subject slots (round-19 skeptic)", cd._has_ask("El nuevo solicitante presenta los documentos.", "es") is True)
    check("U234", "duties guard: 'show the present policy to new hires' still ASKS - boundaries kept the scope, the verb survives (round-19 technical control)", cd._has_ask("Show the present policy to new hires.", "en") is True)
    check("U235", "duties guard: Vietnamese 'không cần trả lời' asks nothing under the bounded stamps (round-19 technical control)", cd._has_ask("Không cần trả lời email này.", "vi") is False)
    check("U236", "duties guard: 'el museo presenta su nueva exposición' ASKS - the tu/su shield's disclosed cost, pinned honestly (round-19 simplicity note)", cd._has_ask("El museo presenta su nueva exposición.", "es") is True)
    check("U237", "duties guard: 'la oficina muestra el nuevo horario' asks nothing - a thing subject announcing (round-19 skeptic)", cd._has_ask("La oficina muestra el nuevo horario en la pantalla.", "es") is False)
    check("U238", "duties guard: 'come winter, the office closes early' asks nothing under the bounded stamps (round-19 control)", cd._has_ask("Come winter, the office closes early.", "en") is False)
    check("U239", "duties guard: 'la empresa presenta tu foto' still ASKS - the shield fires on the reader's own (round-19 judge control)", cd._has_ask("La empresa presenta tu foto en la pantalla.", "es") is True)
    check("U240", "duties guard: 'la empleada presenta la credencial' ASKS - the role shield covers women readers now (round-20 judge)", cd._has_ask("La empleada presenta la credencial al entrar.", "es") is True)
    check("U241", "duties guard: 'la candidata presenta los documentos' ASKS (round-20 judge)", cd._has_ask("La candidata presenta los documentos en la ventanilla.", "es") is True)
    check("U242", "duties guard: 'el contribuyente presenta la declaración' ASKS - tax-office role added (round-20 skeptic)", cd._has_ask("El contribuyente presenta la declaración antes del viernes.", "es") is True)
    check("U243", "duties guard: 'el paciente presenta la receta' ASKS - clinic role added (round-20 skeptic)", cd._has_ask("El paciente presenta la receta al llegar.", "es") is True)
    check("U244", "duties guard: 'el titular muestra el pasaporte' ASKS (round-20 skeptic)", cd._has_ask("El titular muestra el pasaporte al entrar.", "es") is True)
    check("U245", "duties guard: 'un solicitante presenta documentos falsos' asks nothing - an indefinite role subject is a stranger in the news (round-20 skeptic)", cd._has_ask("Un solicitante presenta documentos falsos en la oficina.", "es") is False)
    check("U246", "duties guard: 'una participante presenta una demanda' asks nothing (round-20 skeptic)", cd._has_ask("Una participante presenta una demanda contra la empresa.", "es") is False)
    check("U247", "duties guard: 'favor de no firmar, ni enviar el pago' asks nothing - a comma at the joint cannot flip a refrain into its opposite (round-20 skeptic)", cd._has_ask("Favor de no firmar, ni enviar el pago.", "es") is False)
    check("U248", "duties guard: 'no hace falta firmar, ni enviar el formulario' asks nothing (round-20 skeptic)", cd._has_ask("No hace falta firmar, ni enviar el formulario.", "es") is False)
    check("U249", "duties guard: 'el museo, presenta una exposición' asks nothing - the comma rider (round-20 skeptic)", cd._has_ask("El museo, presenta una exposición nueva.", "es") is False)
    check("U250", "duties guard: a decomposed (NFD) Vietnamese ask still ASKS after entry normalization (round-20 technical)", cd._has_ask(cd.unicodedata.normalize("NFD", "Vui lòng trả lời email này trước thứ sáu."), "vi") is True)
    check("U251", "duties guard: a decomposed (NFD) Vietnamese no-ask still asks nothing (round-20 technical)", cd._has_ask(cd.unicodedata.normalize("NFD", "Không cần trả lời email này."), "vi") is False)
    check("U252", "duties guard: 'la vecina presenta una queja' ASKS (round-20 judge)", cd._has_ask("La vecina presenta una queja en la oficina.", "es") is True)
    check("U253", "duties guard: 'un museo presenta una exposición' still asks nothing - indefinite non-role subjects still stamp (round-20 control)", cd._has_ask("Un museo presenta una exposición nueva.", "es") is False)
    check("U254", "duties guard: no text at all asks nothing - the None contract survives normalization (round-21 technical)", cd._has_ask(None, "es") is False)
    check("U255", "duties guard: 'los solicitantes presentan los documentos' ASKS - the scan sees plural forms now (round-21 skeptic)", cd._has_ask("Los solicitantes presentan los documentos en la ventanilla.", "es") is True)
    check("U256", "duties guard: 'las empleadas presentan la credencial' ASKS (round-21 skeptic)", cd._has_ask("Las empleadas presentan la credencial al entrar.", "es") is True)
    check("U257", "duties guard: 'los alumnos entregan la tarea' ASKS (round-21 skeptic)", cd._has_ask("Los alumnos entregan la tarea el lunes.", "es") is True)
    check("U258", "duties guard: 'es importante que los solicitantes presenten los documentos' ASKS - subjunctive plural too (round-21 skeptic)", cd._has_ask("Es importante que los solicitantes presenten los documentos.", "es") is True)
    check("U259", "duties guard: 'usted presentará los documentos mañana' ASKS - future forms (round-21 skeptic)", cd._has_ask("Usted presentará los documentos mañana.", "es") is True)
    check("U260", "duties guard: 'mañana enviarás el formulario' ASKS (round-21 skeptic)", cd._has_ask("Mañana enviarás el formulario.", "es") is True)
    check("U261", "duties guard: 'los museos presentan exposiciones' still asks nothing - the stamps widened in the same step (round-21 skeptic trap control)", cd._has_ask("Los museos presentan exposiciones nuevas.", "es") is False)
    check("U262", "duties guard: 'el museo presentará una exposición' still asks nothing - future announcement (round-21 skeptic)", cd._has_ask("El museo presentará una exposición nueva.", "es") is False)
    check("U263", "duties guard: 'se presentan los resultados del examen' asks nothing - plural se-announcement (round-21 skeptic)", cd._has_ask("Se presentan los resultados del examen en el tablero.", "es") is False)
    check("U264", "duties guard: 'el jubilado presenta credencial' ASKS - retiree vocabulary added (round-21 skeptic)", cd._has_ask("El jubilado presenta credencial en la ventanilla.", "es") is True)
    check("U265", "duties guard: 'la jubilada presenta credencial' ASKS (round-21 skeptic)", cd._has_ask("La jubilada presenta credencial en la ventanilla.", "es") is True)
    check("U266", "duties guard: 'el derechohabiente presenta la credencial' ASKS - clinic register added (round-21 skeptic)", cd._has_ask("El derechohabiente presenta la credencial en la clínica.", "es") is True)
    check("U267", "duties guard: 'el museo de arte moderno presenta' asks nothing - the de-phrase takes a second word (round-21 skeptic)", cd._has_ask("El museo de arte moderno presenta una exposición.", "es") is False)
    check("U268", "duties guard: 'el titular de la cuenta presenta los documentos' ASKS - the stamp cannot re-anchor inside a role's de-phrase (round-22 skeptic)", cd._has_ask("El titular de la cuenta presenta los documentos.", "es") is True)
    check("U269", "duties guard: 'la titular de la tarjeta presenta la credencial' ASKS (round-22 skeptic)", cd._has_ask("La titular de la tarjeta presenta la credencial.", "es") is True)
    check("U270", "duties guard: 'el beneficiario de la pensión presenta la credencial' ASKS (round-22 skeptic)", cd._has_ask("El beneficiario de la pensión presenta la credencial.", "es") is True)
    check("U271", "duties guard: 'la cuenta presenta un saldo de cero' still asks nothing - the thing subject still stamps (round-22 control)", cd._has_ask("La cuenta presenta un saldo de cero.", "es") is False)
    check("U272", "duties guard: 'preséntenlo en la ventanilla' ASKS - glued plural imperative (round-22 skeptic)", cd._has_ask("Preséntenlo en la ventanilla.", "es") is True)
    check("U273", "duties guard: 'fírmenlo y envíenlo mañana' ASKS (round-22 skeptic)", cd._has_ask("Fírmenlo y envíenlo mañana.", "es") is True)
    check("U274", "duties guard: 'es posible que los datos presenten errores' asks nothing - subjunctive plurals stamp too (round-22 skeptic)", cd._has_ask("Es posible que los datos presenten errores.", "es") is False)
    check("U275", "duties guard: 'el sistema hace que las pantallas muestren el saldo' asks nothing (round-22 skeptic)", cd._has_ask("El sistema hace que las pantallas muestren el saldo actual.", "es") is False)
    check("U276", "duties guard: 'el becario presenta el informe' ASKS - roles round 3 (round-22 skeptic)", cd._has_ask("El becario presenta el informe mensual.", "es") is True)
    check("U277", "duties guard: 'la becaria presenta el informe' ASKS (round-22 skeptic)", cd._has_ask("La becaria presenta el informe mensual.", "es") is True)
    check("U278", "duties guard: 'el pasante presenta el reporte' ASKS (round-22 skeptic)", cd._has_ask("El pasante presenta el reporte semanal.", "es") is True)
    check("U279", "duties guard: 'el arrendatario presenta el contrato' ASKS (round-22 skeptic)", cd._has_ask("El arrendatario presenta el contrato firmado.", "es") is True)
    check("U280", "duties guard: 'su cita es el lunes; viene a la oficina' ASKS - venir's real forms are named now (round-22 skeptic)", cd._has_ask("Su cita es el lunes; viene a la oficina a las nueve.", "es") is True)
    check("U281", "duties guard: 'usted vendrá a la oficina mañana' ASKS (round-22 judge)", cd._has_ask("Usted vendrá a la oficina mañana a las nueve.", "es") is True)
    check("U282", "duties guard: 'cada solicitante viene a la ventanilla' ASKS (round-22 skeptic)", cd._has_ask("Cada solicitante viene a la ventanilla con su credencial.", "es") is True)
    check("U283", "duties guard: 'el solicitante entrega los documentos' ASKS - the generator mints singulars too (round-23 skeptic)", cd._has_ask("El solicitante entrega los documentos en la ventanilla.", "es") is True)
    check("U284", "duties guard: 'el alumno entrega la tarea' ASKS (round-23 skeptic)", cd._has_ask("El alumno entrega la tarea el lunes.", "es") is True)
    check("U285", "duties guard: 'el solicitante remite el pago' ASKS (round-23 skeptic)", cd._has_ask("El solicitante remite el pago a la oficina.", "es") is True)
    check("U286", "duties guard: 'es necesario que el solicitante remita el pago' ASKS (round-23 skeptic)", cd._has_ask("Es necesario que el solicitante remita el pago.", "es") is True)
    check("U287", "duties guard: 'el titular de la cuenta de la sucursal presenta' ASKS - chained modifiers consumed (round-23 skeptic)", cd._has_ask("El titular de la cuenta de la sucursal presenta los documentos.", "es") is True)
    check("U288", "duties guard: 'el titular de la cuenta de ahorros de la sucursal presenta' ASKS (round-23 skeptic)", cd._has_ask("El titular de la cuenta de ahorros de la sucursal presenta los documentos.", "es") is True)
    check("U289", "duties guard: 'el titular de la cuenta en la sucursal presenta' ASKS (round-23 skeptic)", cd._has_ask("El titular de la cuenta en la sucursal presenta los documentos.", "es") is True)
    check("U290", "duties guard: 'la cuenta del titular presenta un saldo' asks nothing - 'del' spans in the stamp (round-23 skeptic + judge)", cd._has_ask("La cuenta del titular presenta un saldo de cero.", "es") is False)
    check("U291", "duties guard: 'el museo del Prado presenta una exposición' asks nothing (round-23 judge)", cd._has_ask("El museo del Prado presenta una exposición nueva.", "es") is False)
    check("U292", "duties guard: 'páguenlo mañana' ASKS - true imperative stems named (round-23 technical)", cd._has_ask("Páguenlo mañana en la ventanilla.", "es") is True)
    check("U293", "duties guard: 'tráiganlo a la oficina' ASKS (round-23 skeptic)", cd._has_ask("Tráiganlo a la oficina.", "es") is True)
    check("U294", "duties guard: 'los niños duermen en la sala' asks nothing - dormir struck from the named set (round-23 judge)", cd._has_ask("Los niños duermen en la sala de espera.", "es") is False)
    check("U295", "duties guard: 'el titular y la directora presentan los documentos' ASKS - coordinated subjects consumed together (round-24 skeptic)", cd._has_ask("El titular y la directora presentan los documentos.", "es") is True)
    check("U296", "duties guard: 'el solicitante y la secretaria presentan los documentos' ASKS (round-24 skeptic)", cd._has_ask("El solicitante y la secretaria presentan los documentos en la ventanilla.", "es") is True)
    check("U297", "duties guard: 'el titular de la cuenta, junto con la directora, presenta' ASKS - the appositive is consumed too (round-24 skeptic)", cd._has_ask("El titular de la cuenta, junto con la directora, presenta los documentos en la ventanilla.", "es") is True)
    check("U298", "duties guard: 'la directora y la secretaria presentan los documentos' still asks nothing - staff plus staff is a description (round-24 control)", cd._has_ask("La directora y la secretaria presentan los documentos.", "es") is False)
    check("U299", "duties guard: 'the summary is on page 3 of the annual report' asks nothing - the false Spanish mint 'page' is struck (round-24 technical)", cd._has_ask("The summary is on page 3 of the annual report.", "en") is False)
    check("U300", "duties guard: 'el titular, la directora y el gerente presentan los documentos' ASKS - a three-person list travels with the role (round-25 skeptic)", cd._has_ask("El titular, la directora y el gerente presentan los documentos.", "es") is True)
    check("U301", "duties guard: 'el titular, la directora, la gerente presentan los documentos' ASKS - a bare comma list travels too (round-25 skeptic)", cd._has_ask("El titular, la directora, la gerente presentan los documentos.", "es") is True)
    check("U302", "duties guard: 'el titular y la directora y la secretaria presentan los documentos' ASKS - y-conjuncts repeat (round-25 skeptic)", cd._has_ask("El titular y la directora y la secretaria presentan los documentos.", "es") is True)
    check("U303", "duties guard: 'el titular o la directora presenta los documentos' ASKS - the o-conjunct travels (round-25 skeptic)", cd._has_ask("El titular o la directora presenta los documentos.", "es") is True)
    check("U304", "duties guard: 'el titular junto con la directora presenta los documentos' ASKS - junto con needs no comma (round-25 skeptic)", cd._has_ask("El titular junto con la directora presenta los documentos.", "es") is True)
    check("U305", "duties guard: 'el titular junto a la directora presenta los documentos' ASKS - junto a travels too (round-25 skeptic)", cd._has_ask("El titular junto a la directora presenta los documentos.", "es") is True)
    check("U306", "duties guard: 'el titular, acompañado de la directora, presenta los documentos' ASKS - the acompañado de appositive travels (round-25 skeptic)", cd._has_ask("El titular, acompañado de la directora, presenta los documentos.", "es") is True)
    check("U307", "duties guard: 'ni el titular ni la directora presentan los documentos' still asks nothing - ni is a negation, never a continuation (round-25 skeptic fence)", cd._has_ask("Ni el titular ni la directora presentan los documentos.", "es") is False)
    check("U308", "duties guard: 'el titular, junto con la directora, presenta los documentos' ASKS - comma junto con without a de-phrase (round-25 skeptic)", cd._has_ask("El titular, junto con la directora, presenta los documentos.", "es") is True)
    check("U309", "duties guard: 'el titular, junto con la directora, y la gerente presentan los documentos' ASKS - a comma before the final y (round-26 skeptic)", cd._has_ask("El titular, junto con la directora, y la gerente presentan los documentos.", "es") is True)
    check("U310", "duties guard: 'el titular, la directora, y el gerente presentan los documentos' ASKS - comma-y closes the list (round-26 skeptic)", cd._has_ask("El titular, la directora, y el gerente presentan los documentos.", "es") is True)
    check("U311", "duties guard: 'el titular y la directora, y la gerente presentan los documentos' ASKS (round-26 skeptic)", cd._has_ask("El titular y la directora, y la gerente presentan los documentos.", "es") is True)
    check("U312", "duties guard: 'el titular, junto con la directora, o la gerente presenta los documentos' ASKS - comma-o after an appositive (round-26 skeptic)", cd._has_ask("El titular, junto con la directora, o la gerente presenta los documentos.", "es") is True)
    check("U313", "duties guard: 'el titular, así como la directora, presenta los documentos' ASKS - así como is a partner too (round-26 skeptic)", cd._has_ask("El titular, así como la directora, presenta los documentos.", "es") is True)
    check("U314", "duties guard: 'el titular así como la directora presenta los documentos' ASKS - así como needs no commas (round-26 skeptic)", cd._has_ask("El titular así como la directora presenta los documentos.", "es") is True)
    check("U315", "duties guard: 'el titular, además de la directora, presenta los documentos' ASKS - además de travels (round-26 skeptic)", cd._has_ask("El titular, además de la directora, presenta los documentos.", "es") is True)
    check("U316", "duties guard: 'el titular acompañado de la directora presenta los documentos' ASKS - acompañado needs no commas (round-26 skeptic)", cd._has_ask("El titular acompañado de la directora presenta los documentos.", "es") is True)
    check("U317", "duties guard: 'los titulares, acompañados de las directoras, presentan los documentos' ASKS - plural acompañado (round-26 skeptic)", cd._has_ask("Los titulares, acompañados de las directoras, presentan los documentos.", "es") is True)
    check("U318", "duties guard: 'las titulares, acompañadas de las directoras, presentan los documentos' ASKS - feminine plural acompañadas (round-26 skeptic)", cd._has_ask("Las titulares, acompañadas de las directoras, presentan los documentos.", "es") is True)
    check("U319", "duties guard: 'el titular de la cuenta y de la tarjeta presenta los documentos' ASKS - a chain link may carry the y (round-26 skeptic)", cd._has_ask("El titular de la cuenta y de la tarjeta presenta los documentos.", "es") is True)
    check("U320", "duties guard: 'el titular, así como la directora de la oficina, presenta los documentos' ASKS - the así como partner keeps her own chain (round-26 skeptic)", cd._has_ask("El titular, así como la directora de la oficina, presenta los documentos.", "es") is True)
    check("U321", "duties guard: 'la directora, así como la secretaria, presenta los documentos' still asks nothing - staff plus staff, así como or not (round-26 skeptic fence)", cd._has_ask("La directora, así como la secretaria, presenta los documentos.", "es") is False)
    check("U322", "duties guard: 'la directora acompañada de la secretaria presenta los documentos' still asks nothing - staff pair, bare acompañado (round-26 skeptic fence)", cd._has_ask("La directora acompañada de la secretaria presenta los documentos.", "es") is False)
    check("U323", "duties guard: 'la cuenta de ahorros y de la tarjeta presenta un saldo' still asks nothing - a thing with two objects is an announcement (round-26 skeptic fence)", cd._has_ask("La cuenta de ahorros y de la tarjeta presenta un saldo.", "es") is False)
    check("U324", "duties guard: 'ni el titular ni la directora, así como la gerente, presentan los documentos' still asks nothing - ni breaks the chain even with así como inside (round-26 skeptic fence)", cd._has_ask("Ni el titular ni la directora, así como la gerente, presentan los documentos.", "es") is False)
    check("U325", "duties guard: 'el titular, en la oficina, presenta los documentos' ASKS - an adjunct between subject and verb travels too (round-27 skeptic)", cd._has_ask("El titular, en la oficina, presenta los documentos.", "es") is True)
    check("U326", "duties guard: 'el titular, según la norma, presenta los documentos' ASKS (round-27 skeptic)", cd._has_ask("El titular, según la norma, presenta los documentos.", "es") is True)
    check("U327", "duties guard: 'el titular, por la mañana, presenta los documentos' ASKS (round-27 skeptic)", cd._has_ask("El titular, por la mañana, presenta los documentos.", "es") is True)
    check("U328", "duties guard: 'el titular, ante la directora, presenta los documentos' ASKS (round-27 skeptic)", cd._has_ask("El titular, ante la directora, presenta los documentos.", "es") is True)
    check("U329", "duties guard: 'el titular, durante la reunión, presenta los documentos' ASKS (round-27 skeptic)", cd._has_ask("El titular, durante la reunión, presenta los documentos.", "es") is True)
    check("U330", "duties guard: 'el titular, con la participación de la directora, presenta los documentos' ASKS - the adjunct swallows its own de-phrase (round-27 skeptic)", cd._has_ask("El titular, con la participación de la directora, presenta los documentos.", "es") is True)
    check("U331", "duties guard: 'el titular por la mañana presenta los documentos' ASKS - a bare adjunct travels on the chain (round-27 skeptic)", cd._has_ask("El titular por la mañana presenta los documentos.", "es") is True)
    check("U332", "duties guard: 'el titular según la norma presenta los documentos' ASKS - bare según (round-27 skeptic)", cd._has_ask("El titular según la norma presenta los documentos.", "es") is True)
    check("U333", "duties guard: 'el titular con la directora presenta los documentos' ASKS - bare con adjunct (round-27 skeptic)", cd._has_ask("El titular con la directora presenta los documentos.", "es") is True)
    check("U334", "duties guard: 'tanto el titular como la directora presentan los documentos' ASKS - tanto...como (round-27 skeptic)", cd._has_ask("Tanto el titular como la directora presentan los documentos.", "es") is True)
    check("U335", "duties guard: 'el titular como la directora presentan los documentos' ASKS - bare como (round-27 skeptic)", cd._has_ask("El titular como la directora presentan los documentos.", "es") is True)
    check("U336", "duties guard: 'el titular, como la directora, presenta los documentos' ASKS - appositive como (round-27 skeptic)", cd._has_ask("El titular, como la directora, presenta los documentos.", "es") is True)
    check("U337", "duties guard: 'el titular y/o la directora presentan los documentos' ASKS - the written y/o (round-27 skeptic)", cd._has_ask("El titular y/o la directora presentan los documentos.", "es") is True)
    check("U338", "duties guard: 'el titular y también la directora presentan los documentos' ASKS - the también slot (round-27 skeptic)", cd._has_ask("El titular y también la directora presentan los documentos.", "es") is True)
    check("U339", "duties guard: 'el titular, así como también la directora, presenta los documentos' ASKS - así como también (round-27 skeptic)", cd._has_ask("El titular, así como también la directora, presenta los documentos.", "es") is True)
    check("U340", "duties guard: 'el titular, asi como la directora, presenta los documentos' ASKS - senders drop the accent (round-27 skeptic)", cd._has_ask("El titular, asi como la directora, presenta los documentos.", "es") is True)
    check("U341", "duties guard: 'el titular, ademas de la directora, presenta los documentos' ASKS - accent dropped (round-27 skeptic)", cd._has_ask("El titular, ademas de la directora, presenta los documentos.", "es") is True)
    check("U342", "duties guard: 'el titular, acompanado de la directora, presenta los documentos' ASKS - accents dropped (round-27 skeptic)", cd._has_ask("El titular, acompanado de la directora, presenta los documentos.", "es") is True)
    check("U343", "duties guard: 'la directora, en la oficina, presenta los documentos' still asks nothing - a staff adjunct is a description (round-27 skeptic fence)", cd._has_ask("La directora, en la oficina, presenta los documentos.", "es") is False)
    check("U344", "duties guard: 'el museo, en la plaza, presenta una exposición' still asks nothing - a thing adjunct is an announcement (round-27 skeptic fence)", cd._has_ask("El museo, en la plaza, presenta una exposición.", "es") is False)
    check("U345", "duties guard: 'la cuenta, como la tarjeta, presenta un saldo' still asks nothing - thing plus como (round-27 skeptic fence)", cd._has_ask("La cuenta, como la tarjeta, presenta un saldo.", "es") is False)
    check("U346", "duties guard: 'tanto la directora como la secretaria presentan los documentos' still asks nothing - staff tanto...como (round-27 skeptic fence)", cd._has_ask("Tanto la directora como la secretaria presentan los documentos.", "es") is False)
    check("U347", "duties guard: 'ni el titular ni la directora, en la oficina, presentan los documentos' still asks nothing - the ni pair survives an adjunct (round-27 skeptic fence)", cd._has_ask("Ni el titular ni la directora, en la oficina, presentan los documentos.", "es") is False)
    check("U348", "duties guard: 'la directora, asi como la secretaria, presenta los documentos' still asks nothing - staff pair, accent dropped (round-27 skeptic fence)", cd._has_ask("La directora, asi como la secretaria, presenta los documentos.", "es") is False)
    check("U349", "duties guard: 'el titular, de la cuenta, presenta los documentos' ASKS - a parenthetical de-phrase travels too (round-28 technical)", cd._has_ask("El titular, de la cuenta, presenta los documentos.", "es") is True)
    check("U350", "duties guard: 'el titular, como la directora, de la cuenta, presenta los documentos' ASKS - member then parenthetical (round-28 technical)", cd._has_ask("El titular, como la directora, de la cuenta, presenta los documentos.", "es") is True)
    check("U351", "duties guard: 'el titular, mediante la presente, presenta los documentos' ASKS - the formal letter's stock adjunct (round-28 skeptic)", cd._has_ask("El titular, mediante la presente, presenta los documentos.", "es") is True)
    check("U352", "duties guard: 'el titular mediante la presente presenta los documentos' ASKS - bare mediante on the chain (round-28 skeptic)", cd._has_ask("El titular mediante la presente presenta los documentos.", "es") is True)
    check("U353", "duties guard: 'el titular, a través de la sucursal, presenta los documentos' ASKS (round-28 skeptic)", cd._has_ask("El titular, a través de la sucursal, presenta los documentos.", "es") is True)
    check("U354", "duties guard: 'el titular a través de la plataforma presenta los documentos' ASKS - bare a través de (round-28 skeptic)", cd._has_ask("El titular a través de la plataforma presenta los documentos.", "es") is True)
    check("U355", "duties guard: 'el titular, por medio de la presente, presenta la solicitud' ASKS - the multiword unit sits in the member (round-28 skeptic)", cd._has_ask("El titular, por medio de la presente, presenta la solicitud.", "es") is True)
    check("U356", "duties guard: 'el beneficiario, de parte de la familia, presenta la solicitud' ASKS (round-28 skeptic)", cd._has_ask("El beneficiario, de parte de la familia, presenta la solicitud.", "es") is True)
    check("U357", "duties guard: 'el titular, desde la aplicación, presenta los documentos' ASKS (round-28 skeptic)", cd._has_ask("El titular, desde la aplicación, presenta los documentos.", "es") is True)
    check("U358", "duties guard: 'el titular desde el portal presenta los documentos' ASKS - bare desde (round-28 skeptic)", cd._has_ask("El titular desde el portal presenta los documentos.", "es") is True)
    check("U359", "duties guard: 'el titular, para la renovación, presenta los documentos' ASKS - para in the member only (round-28 skeptic)", cd._has_ask("El titular, para la renovación, presenta los documentos.", "es") is True)
    check("U360", "duties guard: 'el titular, para presentar los documentos, acude a la ventanilla' still ASKS - para never joins the chain, so the purpose infinitive still reaches the scan (round-28 skeptic control)", cd._has_ask("El titular, para presentar los documentos, acude a la ventanilla.", "es") is True)
    check("U361", "duties guard: 'la directora, mediante la presente, presenta los documentos' still asks nothing - staff stock adjunct (round-28 skeptic fence)", cd._has_ask("La directora, mediante la presente, presenta los documentos.", "es") is False)
    check("U362", "duties guard: 'la directora, de la oficina, presenta los documentos' still asks nothing - a staff parenthetical is a description (round-28 technical fence)", cd._has_ask("La directora, de la oficina, presenta los documentos.", "es") is False)
    check("U363", "duties guard: 'el museo, desde la plaza, presenta una exposición' still asks nothing - thing plus desde (round-28 skeptic fence)", cd._has_ask("El museo, desde la plaza, presenta una exposición.", "es") is False)
    check("U364", "duties guard: 'la cuenta, a través de la sucursal, presenta un saldo' still asks nothing - thing plus a través de (round-28 skeptic fence)", cd._has_ask("La cuenta, a través de la sucursal, presenta un saldo.", "es") is False)
    check("U365", "duties guard: 'ni el titular ni la directora, mediante la presente, presentan los documentos' still asks nothing - the ni pair survives the new adjuncts (round-28 skeptic fence)", cd._has_ask("Ni el titular ni la directora, mediante la presente, presentan los documentos.", "es") is False)
    check("U366", "duties guard: 'la directora, para la renovación, presenta los documentos' still asks nothing - staff para (round-28 skeptic fence)", cd._has_ask("La directora, para la renovación, presenta los documentos.", "es") is False)
    check("U367", "duties guard: 'el titular, a nombre de la empresa, presenta los documentos' ASKS - the one-letter preposition opens the phrase (round-29 skeptic)", cd._has_ask("El titular, a nombre de la empresa, presenta los documentos.", "es") is True)
    check("U368", "duties guard: 'el titular, a petición de la institución, presenta los documentos' ASKS (round-29 skeptic)", cd._has_ask("El titular, a petición de la institución, presenta los documentos.", "es") is True)
    check("U369", "duties guard: 'el titular, en atención a la solicitud, presenta los documentos' ASKS - the phrase ENDS in the missing link (round-29 skeptic)", cd._has_ask("El titular, en atención a la solicitud, presenta los documentos.", "es") is True)
    check("U370", "duties guard: 'el titular, en cuanto a la solicitud, presenta los documentos' ASKS - a top-frequency connector (round-29 skeptic)", cd._has_ask("El titular, en cuanto a la solicitud, presenta los documentos.", "es") is True)
    check("U371", "duties guard: 'el titular a la ventanilla presenta los documentos' ASKS - bare a plus determiner (round-29 skeptic)", cd._has_ask("El titular a la ventanilla presenta los documentos.", "es") is True)
    check("U372", "duties guard: 'el titular, para efectos de la presente, presenta los documentos' ASKS - the unit sits in the member only, para still out of the chain (round-29 skeptic)", cd._has_ask("El titular, para efectos de la presente, presenta los documentos.", "es") is True)
    check("U373", "duties guard: 'el titular, al amparo de la norma, presenta los documentos' ASKS - al is a contraction no chain link matches (round-29 skeptic)", cd._has_ask("El titular, al amparo de la norma, presenta los documentos.", "es") is True)
    check("U374", "duties guard: 'el titular, de la cuenta a la sucursal, presenta los documentos' ASKS - the a-link exercised INSIDE the comma-led member's span (round-29 member-side pin)", cd._has_ask("El titular, de la cuenta a la sucursal, presenta los documentos.", "es") is True)
    check("U375", "duties guard: 'el titular, a la oficina de la sucursal, presenta los documentos' ASKS - the comma-led member's own link IS the a-link (round-29 member-side pin)", cd._has_ask("El titular, a la oficina de la sucursal, presenta los documentos.", "es") is True)
    check("U376", "duties guard: 'el museo, en su sala, presenta una exposición' asks NOTHING - a possessive intervener no longer invents a duty (round-29 judge)", cd._has_ask("El museo, en su sala, presenta una exposición.", "es") is False)
    check("U377", "duties guard: 'el banco, desde su portal, presenta la nueva aplicación' asks NOTHING (round-29 judge)", cd._has_ask("El banco, desde su portal, presenta la nueva aplicación.", "es") is False)
    check("U378", "duties guard: 'la cuenta, en su estado, presenta un saldo de cero' asks NOTHING (round-29 judge)", cd._has_ask("La cuenta, en su estado, presenta un saldo de cero.", "es") is False)
    check("U379", "duties guard: 'la secretaria, en su oficina, presenta los documentos' asks NOTHING - the secretaria doctrine holds in the su shape (round-29 judge)", cd._has_ask("La secretaria, en su oficina, presenta los documentos.", "es") is False)
    check("U380", "duties guard: 'el museo, hoy, presenta una exposición' asks NOTHING - a bare time word between subject and verb (round-29 judge)", cd._has_ask("El museo, hoy, presenta una exposición.", "es") is False)
    check("U381", "duties guard: 'el titular, en su oficina, presenta los documentos' still ASKS - the stamp's new segment carries the role guard, so a role subject keeps its duty (round-29 judge control)", cd._has_ask("El titular, en su oficina, presenta los documentos.", "es") is True)
    check("U382", "duties guard: 'el titular va a presentar los documentos' still ASKS - the a-periphrase is untouched; a heads infinitives only after a verb (round-29 skeptic control)", cd._has_ask("El titular va a presentar los documentos.", "es") is True)
    check("U383", "duties guard: 'la directora, a nombre de la empresa, presenta los documentos' still asks nothing - staff a-opener (round-29 skeptic fence)", cd._has_ask("La directora, a nombre de la empresa, presenta los documentos.", "es") is False)
    check("U384", "duties guard: 'el museo, en cuanto a la exposición, presenta una muestra' still asks nothing - thing plus a-tail (round-29 skeptic fence)", cd._has_ask("El museo, en cuanto a la exposición, presenta una muestra.", "es") is False)
    check("U385", "duties guard: 'ni el titular ni la directora, a nombre de la empresa, presentan los documentos' still asks nothing - the ni pair survives an a-opener (round-29 skeptic fence)", cd._has_ask("Ni el titular ni la directora, a nombre de la empresa, presentan los documentos.", "es") is False)
    check("U386", "duties guard: 'la directora, para efectos de la presente, presenta los documentos' still asks nothing - staff member-only unit (round-29 skeptic fence)", cd._has_ask("La directora, para efectos de la presente, presenta los documentos.", "es") is False)
    check("U387", "duties guard: 'su estado de cuenta presenta un saldo de cero' asks NOTHING - a possessive head is an announcement, the bank's commonest frame (round-30 skeptic)", cd._has_ask("Su estado de cuenta presenta un saldo de cero.", "es") is False)
    check("U388", "duties guard: 'su estado de cuenta muestra un saldo de cero' asks NOTHING (round-30 skeptic)", cd._has_ask("Su estado de cuenta muestra un saldo de cero.", "es") is False)
    check("U389", "duties guard: 'su representante presenta los documentos' asks NOTHING - a third person acting is news, as staff announcements are (round-30 skeptic)", cd._has_ask("Su representante presenta los documentos.", "es") is False)
    check("U390", "duties guard: 'su estado de cuenta, en su portal, muestra un saldo de cero' asks NOTHING - possessive head plus the intervener segment (round-30 skeptic)", cd._has_ask("Su estado de cuenta, en su portal, muestra un saldo de cero.", "es") is False)
    check("U391", "duties guard: 'su titular presenta los documentos' still ASKS - the possessive head carries the role guard (round-30 skeptic fence)", cd._has_ask("Su titular presenta los documentos.", "es") is True)
    check("U392", "duties guard: 'su cuenta muestra su saldo' still ASKS - the verb-adjacent su refusal is untouched (round-30 skeptic fence)", cd._has_ask("Su cuenta muestra su saldo.", "es") is True)
    check("U393", "duties guard: 'el titular recoge la carpeta y presenta los documentos' ASKS - no fake subject from the object plus y (round-30 skeptic)", cd._has_ask("El titular recoge la carpeta y presenta los documentos.", "es") is True)
    check("U394", "duties guard: 'el titular recoge la carpeta y muestra los documentos' ASKS (round-30 skeptic)", cd._has_ask("El titular recoge la carpeta y muestra los documentos.", "es") is True)
    check("U395", "duties guard: 'el paciente recoge la tarjeta y presenta los documentos' ASKS (round-30 skeptic)", cd._has_ask("El paciente recoge la tarjeta y presenta los documentos.", "es") is True)
    check("U396", "duties guard: 'el titular va a la oficina y presenta los documentos' ASKS - the object slot takes a plus determiner (round-30 skeptic)", cd._has_ask("El titular va a la oficina y presenta los documentos.", "es") is True)
    check("U397", "duties guard: 'el museo exhibe la colección y presenta una muestra' still asks nothing - the same swallow is load-bearing here and was NOT guarded away (round-30 skeptic fence)", cd._has_ask("El museo exhibe la colección y presenta una muestra.", "es") is False)
    check("U398", "duties guard: 'la secretaria recoge la carpeta y presenta los documentos' still asks nothing - the staff twin keeps the doctrine (round-30 skeptic fence)", cd._has_ask("La secretaria recoge la carpeta y presenta los documentos.", "es") is False)
    check("U399", "duties guard: 'el museo, en atención a la muestra, presenta una exposición' asks NOTHING - the scope no longer starves the stamp of its anchor (round-30 judge)", cd._has_ask("El museo, en atención a la muestra, presenta una exposición.", "es") is False)
    check("U400", "duties guard: 'el museo, en la muestra, presenta una exposición' asks NOTHING (round-30 judge)", cd._has_ask("El museo, en la muestra, presenta una exposición.", "es") is False)
    check("U401", "duties guard: 'el titular, en atención a la muestra, presenta los documentos' still ASKS - the role twin keeps its duty (round-30 judge control)", cd._has_ask("El titular, en atención a la muestra, presenta los documentos.", "es") is True)
    check("U402", "duties guard: 'el titular envía el pago y archiva los documentos' ASKS - the tempered segment no longer eats a duty first verb (round-31 judge)", cd._has_ask("El titular envía el pago y archiva los documentos.", "es") is True)
    check("U403", "duties guard: 'el titular firma el contrato y guarda la copia' ASKS (round-31 judge)", cd._has_ask("El titular firma el contrato y guarda la copia.", "es") is True)
    check("U404", "duties guard: 'el paciente entrega la tarjeta y espera en la sala' ASKS (round-31 judge)", cd._has_ask("El paciente entrega la tarjeta y espera en la sala.", "es") is True)
    check("U405", "duties guard: 'el titular envía el pago y la directora archiva los documentos' ASKS - a new clause after the y is not the segment's cell (round-31 judge)", cd._has_ask("El titular envía el pago y la directora archiva los documentos.", "es") is True)
    check("U406", "duties guard: 'su titular, en su portal, presenta los documentos' ASKS - the stamp no longer re-anchors on the intervener's noun (round-31 technical)", cd._has_ask("Su titular, en su portal, presenta los documentos.", "es") is True)
    check("U407", "duties guard: 'su paciente, en su sala, presenta los documentos' ASKS (round-31 technical)", cd._has_ask("Su paciente, en su sala, presenta los documentos.", "es") is True)
    check("U408", "duties guard: 'la galería, con la muestra gratuita, presenta una exposición' asks NOTHING - the refusal sees past gratuita (round-31 technical)", cd._has_ask("La galería, con la muestra gratuita, presenta una exposición.", "es") is False)
    check("U409", "duties guard: 'la muestra gratuita presenta los resultados' asks NOTHING (round-31 technical)", cd._has_ask("La muestra gratuita presenta los resultados.", "es") is False)
    check("U410", "round trip: the Maria sample email is detected as written in English", cd.detect_lang("Hello Maria, the board meeting moved to Tuesday November 24 at 5:15 PM in Room 4. Please reply to confirm and bring your photo ID. Thank you.") == "en")
    check("U411", "round trip: a Spanish email is detected as Spanish", cd.detect_lang("Hola Jose Luis, la reunión se mueve para el martes. Por favor confirma tu asistencia y trae los documentos a la oficina. Gracias por tu ayuda con la cuenta.") == "es")
    check("U412", "round trip: a Vietnamese email is detected as Vietnamese", cd.detect_lang("Xin chào, cuộc họp sẽ chuyển sang thứ Ba. Vui lòng xác nhận và mang theo giấy tờ. Cảm ơn bạn rất nhiều.") == "vi")
    check("U413", "round trip: a translation that copies the date and time word-for-word passes the dates check", cd._dates_survive("Confirmo que la reunión es el Tuesday November 24 a las 5:15 PM.", "I confirm the meeting is on Tuesday November 24 at 5:15 PM.") is True)
    check("U414", "round trip: a translation that REFORMATS the date fails the dates check - it would never be sent", cd._dates_survive("Confirmo que la reunión es el Tuesday November 24 a las 5:15 PM.", "I confirm the meeting is on November 24 at 5:15 in the evening.") is False)
    _saved_url = cd.os.environ.pop("CLEARDAY_MODEL_URL", None)
    _no_model = cd.translate_reply("Hola, confirmo mi asistencia.", "en")
    if _saved_url:
        cd.os.environ["CLEARDAY_MODEL_URL"] = _saved_url
    check("U415", "round trip: with no model configured, translate_reply refuses cleanly instead of guessing", _no_model == (None, False))

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
    lines = bpage.split("class='bulkline'")
    check("L21", "bulk slim: 1 email -> exactly 1 line naming Maria + subject + her NEW meeting date WITH its label + the tap-to-open link", code == 200 and len(lines) - 1 == 1 and "Maria Lopez" in bpage and "Board meeting moved" in bpage and "New Meeting Date: Tuesday, November 24 at 5:15 PM" in bpage and "/inbox/clear?id=" in bpage)
    _m = re.search(r"/inbox/clear\?id=([A-Za-z0-9_\-]+)", bpage)
    code, opened = get("/inbox/clear?id=" + (_m.group(1) if _m else "") + "&lang=en")
    check("L22", "bulk slim: behind the tap, Maria's full clear page with her labeled dates", "EVERYTHING YOU MUST DO" in bpage and code == 200 and "Tuesday, November 24 at 5:15 PM" in opened and "Friday, November 27" in opened)
    send_mail("Dana Ruiz <dana@example.org>", "Form due", "The form is due 11/24/2026. Please reply to confirm.")
    send_mail("Sam Ortiz <sam@example.org>", "Deadline", "The deadline is 2026-11-30. Please reply.")
    time.sleep(1)
    before = mp_list()["total"]
    code, bpage = post("/bulk/clear", {"lang": "en"}, timeout=300)
    lines = bpage.split("class='bulkline'")[1:]
    def line_with(token):
        for c in lines:
            if token in c:
                return c
        return ""
    check("L23", "bulk slim: 3 emails -> 3 lines, each with ONLY its own date (Maria's line carries her NEW date, labeled)", len(lines) == 3 and "2026-11-30" not in line_with("11/24/2026") and "Tuesday, November 24" not in line_with("11/24/2026") and "11/24/2026" not in line_with("2026-11-30") and "11/24/2026" not in line_with("Tuesday, November 24") and "2026-11-30" not in line_with("Tuesday, November 24"))
    combined = bpage.split("class='box blue'")[0]
    check("L24", "bulk: combined list aggregates actions from all 3 emails", combined.count("&#9654;") >= 3)
    check("L25", "bulk: the inbox itself is untouched (nothing deleted, nothing sent)", mp_list()["total"] == before)
    code, bpage2 = post("/bulk/clear", {"lang": "en"}, timeout=300)
    check("L26", "bulk slim: a second press shows the same line count (idempotent)", code == 200 and len(bpage2.split("class='bulkline'")) - 1 == 3)
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
