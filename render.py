"""Dyslexia-friendly rendering. IDA + WCAG 2.2 AA rules in CSS:
cream background #FFF6D6, dark text #20242E (not pure black on white),
Arial/Verdana, body 21-22px, headings 24-32px, line-height 1.7,
letter-spacing .04em, left aligned, bold only, color+label+shape per box.
Reader choice: tint + text size are client-side buttons (IDA/WCAG: let the
reader choose their own background color).
"""
import html
def esc(x):
    return html.escape(str(x))

STRINGS = {
    "en": {"tagline": "Long message in. <b>1 clear page out.</b>", "language": "Language",
           "from": "From", "subject": "Subject", "paste": "Paste the long message", "button": "Make it clear",
           "demo_warn": "Public demo — please paste sample text only, not real email.",
           "see_followups": "See follow-ups I remember",
           "demo_page": "Demo page — made from text pasted by a visitor.",
           "what": "WHAT THIS IS", "do": "YOU MUST DO", "facts": "KEY FACTS", "dates": "DATES + NUMBERS",
           "no_dates": "No dates found", "risk": "IF YOU DO NOTHING", "steps": "Steps", "source": "Source",
           "another": "Make another clear", "followups": "Follow-ups",
           "followups_title": "Follow-ups I remember",
           "demo_entries": "Demo entries — made from sample text pasted by visitors.",
           "no_followups": "No follow-ups waiting.", "nudge": "no reply yet — I will nudge"},
    "es": {"tagline": "Mensaje largo entra. <b>Una página clara sale.</b>", "language": "Idioma",
           "from": "De", "subject": "Asunto", "paste": "Pega el mensaje largo", "button": "Hazlo claro",
           "demo_warn": "Demostración pública: pega solo texto de ejemplo, no correo real.",
           "see_followups": "Ver los seguimientos que recuerdo",
           "demo_page": "Página de demostración: creada con el texto que pegó un visitante.",
           "what": "QUÉ ES ESTO", "do": "LO QUE DEBES HACER", "facts": "DATOS CLAVE", "dates": "FECHAS Y NÚMEROS",
           "no_dates": "No se encontraron fechas", "risk": "SI NO HACES NADA", "steps": "Pasos", "source": "Fuente",
           "another": "Hacer otra página clara", "followups": "Seguimientos",
           "followups_title": "Seguimientos que recuerdo",
           "demo_entries": "Entradas de demostración: creadas con texto de ejemplo pegado por visitantes.",
           "no_followups": "No hay seguimientos en espera.", "nudge": "sin respuesta aún — le recordaré a"},
    "vi": {"tagline": "Đưa vào tin nhắn dài. <b>Nhận lại một trang rõ ràng.</b>", "language": "Ngôn ngữ",
           "from": "Người gửi", "subject": "Chủ đề", "paste": "Dán tin nhắn dài", "button": "Làm rõ",
           "demo_warn": "Bản demo công khai — chỉ dán văn bản mẫu, không dán email thật.",
           "see_followups": "Xem những việc tôi ghi nhớ",
           "demo_page": "Trang demo — được tạo từ văn bản do khách truy cập dán vào.",
           "what": "ĐÂY LÀ GÌ", "do": "VIỆC BẠN PHẢI LÀM", "facts": "THÔNG TIN CHÍNH", "dates": "NGÀY VÀ CON SỐ",
           "no_dates": "Không tìm thấy ngày nào", "risk": "NẾU BẠN KHÔNG LÀM GÌ", "steps": "Các bước", "source": "Nguồn",
           "another": "Tạo một trang rõ ràng khác", "followups": "Việc cần theo dõi",
           "followups_title": "Những việc tôi ghi nhớ",
           "demo_entries": "Mục demo — được tạo từ văn bản mẫu do khách truy cập dán vào.",
           "no_followups": "Không có việc nào đang chờ.", "nudge": "chưa trả lời — tôi sẽ nhắc"},
}
def S(lang):
    return STRINGS.get(lang, STRINGS["en"])
CSS = """
body{font-family:Arial,Verdana,sans-serif;background:#FFF6D6;color:#20242E;font-size:21px;
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

def render_form(extra="", lang="en"):
    s = S(lang)
    checked = {code: ("checked" if code == lang else "") for code in STRINGS}
    return _shell(f"""<h1>ClearDay</h1><div class='big'>{s['tagline']}</div>
{extra}
<form method='post'>
<p class='big'><b>{s['language']}</b><br>
<label><input type='radio' name='lang' value='en' style='width:auto' {checked['en']}> English</label>
<label><input type='radio' name='lang' value='es' style='width:auto' {checked['es']}> Español</label>
<label><input type='radio' name='lang' value='vi' style='width:auto' {checked['vi']}> Tiếng Việt</label></p>
<p><label class='big'><b>{s['from']}</b></label><input name='sender' placeholder='Maria Lopez'></p>
<p><label class='big'><b>{s['subject']}</b></label><input name='subject' placeholder='Meeting moved'></p>
<p><label class='big'><b>{s['paste']}</b></label><textarea name='text' rows='10'></textarea></p>
<p class='big'><b>{s['demo_warn']}</b></p>
<button type='submit'>{s['button']}</button></form>
<p class='big'><a href='/followups'>{s['see_followups']}</a></p>""")

def render_page(p):
    s = S(p.get("lang", "en"))
    actions = "".join(f"<div class='big'>{i}. {esc(a)}</div>" for i, a in enumerate(p.get("actions", []), 1))
    facts = "".join(f"<tr><td style='width:32%'><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in (p.get("facts") or {}).items())
    dates = "".join(f"<div style='font-size:26px'><b>{esc(d)}</b></div>" for d in p.get("dates_numbers", [])) or f"<div class='big'>{s['no_dates']}</div>"
    steps = " &rarr; ".join(esc(x) for x in p.get("steps", []))
    risk = f"<div class='box plain'><span class='lbl'>&#9650; {s['risk']}</span><div class='big'>{esc(p['risk'])}</div></div>" if p.get("risk") else ""
    return _shell(f"""<h1>ClearDay</h1>
<p class='big'><b>{s['demo_page']}</b></p>
<div class='box blue'><span class='lbl'>&#9632; {s['what']}</span><div class='big'>{esc(p.get('what',''))}</div></div>
<div class='box amber'><span class='lbl'>&#9654; {s['do']}</span>{actions}</div>
<div class='box purple'><span class='lbl'>&#9679; {s['facts']}</span><table>{facts}</table></div>
<div class='box plain'><span class='lbl'>&#9670; {s['dates']}</span>{dates}</div>
{risk}
<p class='big' style='margin-top:16px;'>{s['steps']}: {steps}</p>
<p style='font-size:18px;'>{s['source']}: {esc(p.get('sender',''))} &middot; {esc(p.get('source_date',''))}</p>
<p class='big'><a href='/'>{s['another']}</a> &middot; <a href='/followups'>{s['followups']}</a></p>""")
