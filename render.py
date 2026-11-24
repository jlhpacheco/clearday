"""Dyslexia-friendly rendering. IDA + WCAG 2.2 AA rules in CSS:
cream background #FFF6D6, dark text #20242E (not pure black on white),
Arial/Verdana, body 21-22px, headings 24-32px, line-height 1.7,
letter-spacing .04em, left aligned, bold only, color+label+shape per box.
Reader choice: tint + text size are client-side buttons (IDA/WCAG: let the
reader choose their own background color).
"""
CSS = """
body{font-family:Arial,Verdana,sans-serif;background:#FFF6D6;color:#20242E;
line-height:1.7;letter-spacing:.04em;margin:0;padding:20px}
.wrap{max-width:680px;margin:0 auto}
h1{font-size:32px;line-height:1.3;margin:0}
.big{font-size:22px}.box{border-radius:12px;padding:14px;margin-top:14px;border:3px solid}
.blue{background:#DCEBFF;border-color:#2456A6}.blue b{color:#123A7A}
.amber{background:#FFE3B3;border-color:#9A5B00}.amber b{color:#6B3E00}
.purple{background:#EADCF8;border-color:#5B2EA6}.purple b{color:#351261}
.plain{background:#FFFDF4;border-color:#20242E}
.lbl{font-size:24px;font-weight:bold}
table{width:100%;border-collapse:collapse;font-size:21px}td{padding:8px;vertical-align:top}
textarea,input{width:100%;font-size:20px;font-family:Arial,Verdana,sans-serif;padding:10px;box-sizing:border-box}
button{font-size:22px;font-weight:bold;padding:12px 20px;margin-top:12px}
"""

def _shell(inner):
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ClearDay</title><style>{CSS}</style></head><body><div class='wrap'>{inner}</div></body></html>"

def render_form(extra=""):
    return _shell(f"""<h1>ClearDay</h1><div class='big'>Long message in. <b>1 clear page out.</b></div>
{extra}
<form method='post'>
<p><label class='big'><b>From</b></label><input name='sender' placeholder='Maria Lopez'></p>
<p><label class='big'><b>Subject</b></label><input name='subject' placeholder='Meeting moved'></p>
<p><label class='big'><b>Paste the long message</b></label><textarea name='text' rows='10'></textarea></p>
<button type='submit'>Make it clear</button></form>
<p class='big'><a href='/followups'>See follow-ups I remember</a></p>""")

def render_page(p):
    actions = "".join(f"<div class='big'>{i}. {a}</div>" for i, a in enumerate(p.get("actions", []), 1))
    facts = "".join(f"<tr><td style='width:32%'><b>{k}</b></td><td>{v}</td></tr>" for k, v in (p.get("facts") or {}).items())
    dates = "".join(f"<div style='font-size:26px'><b>{d}</b></div>" for d in p.get("dates_numbers", [])) or "<div class='big'>No dates found</div>"
    steps = " &rarr; ".join(p.get("steps", []))
    risk = f"<div class='box plain'><span class='lbl'>&#9650; IF YOU DO NOTHING</span><div class='big'>{p['risk']}</div></div>" if p.get("risk") else ""
    return _shell(f"""<h1>ClearDay</h1>
<div class='box blue'><span class='lbl'>&#9632; WHAT THIS IS</span><div class='big'>{p.get('what','')}</div></div>
<div class='box amber'><span class='lbl'>&#9654; YOU MUST DO</span>{actions}</div>
<div class='box purple'><span class='lbl'>&#9679; KEY FACTS</span><table>{facts}</table></div>
<div class='box plain'><span class='lbl'>&#9670; DATES + NUMBERS</span>{dates}</div>
{risk}
<p class='big' style='margin-top:16px;'>Steps: {steps}</p>
<p style='font-size:18px;'>Source: {p.get('sender','')} &middot; {p.get('source_date','')}</p>
<p class='big'><a href='/'>Make another clear</a> &middot; <a href='/followups'>Follow-ups</a></p>""")
