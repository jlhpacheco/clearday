"""Dyslexia-friendly rendering. IDA + WCAG 2.2 AA rules in CSS:
cream background #FFF6D6, dark text #20242E (not pure black on white),
Arial/Verdana, body 21-22px, headings 24-32px, line-height 1.7,
letter-spacing .04em, left aligned, bold only, color+label+shape per box.
Layout polish modeled on Solvia (Jose Luis's other app): brand top bar,
hero headline with one accent line, numbered path card, rounded cards,
pill badges. The accessibility rules above never change - only the polish.
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
           "ai_live": "AI: live model response", "ai_rules": "Rules: instant answer — no model used",
           "hero1": "Long message in.", "hero2": "One clear page out.",
           "hero_sub": "Built for people with dyslexia. Paste a wall of text — get the facts, the actions, and the dates in big type.",
           "path_title": "Your path to a clear page", "path_sub": "Three steps. No guesswork.",
           "step1": "Paste the long message", "step2": "Press the button", "step3": "Read one clear page — same order, every time",
           "brand_pill": "Built for dyslexic readers",
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
           "ai_live": "IA: respuesta en vivo del modelo", "ai_rules": "Reglas: respuesta instantánea — sin modelo",
           "hero1": "Mensaje largo entra.", "hero2": "Una página clara sale.",
           "hero_sub": "Hecho para personas con dislexia. Pega un muro de texto y recibe los datos, las acciones y las fechas en letra grande.",
           "path_title": "Tu camino a una página clara", "path_sub": "Tres pasos. Sin adivinar.",
           "step1": "Pega el mensaje largo", "step2": "Pulsa el botón", "step3": "Lee una página clara — el mismo orden, siempre",
           "brand_pill": "Hecho para lectores con dislexia",
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
           "ai_live": "AI: phản hồi trực tiếp từ mô hình", "ai_rules": "Quy tắc: trả lời ngay — không dùng mô hình",
           "hero1": "Đưa vào tin nhắn dài.", "hero2": "Nhận lại một trang rõ ràng.",
           "hero_sub": "Làm cho người mắc chứng khó đọc. Dán một bức tường chữ — nhận lại thông tin, việc phải làm và ngày tháng bằng chữ lớn.",
           "path_title": "Đường tới một trang rõ ràng", "path_sub": "Ba bước. Không phải đoán.",
           "step1": "Dán tin nhắn dài", "step2": "Nhấn nút", "step3": "Đọc một trang rõ ràng — cùng thứ tự, mọi lần",
           "brand_pill": "Làm cho người đọc khó đọc",
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
.wrap{max-width:760px;margin:0 auto}
h1{font-size:30px;line-height:1.3;margin:0}
.big{font-size:22px}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.brand{display:flex;align-items:center;gap:12px}
.mark{width:52px;height:52px;border-radius:14px;background:#123A7A;color:#FFF6D6;
font-size:25px;font-weight:bold;display:flex;align-items:center;justify-content:center;gap:2px;
box-shadow:0 4px 0 rgba(32,36,46,.18)}
.mark span{color:#35C48D;font-size:17px}
.brandsub{font-size:16px;color:#4A5160;line-height:1.4}
.pill{display:inline-block;border:3px solid #20242E;background:#FFFDF4;border-radius:999px;
padding:6px 16px;font-weight:bold;font-size:20px}
.pill-ai{border-color:#1E7A34;background:#DFF5D8}
.hero{font-size:40px;line-height:1.25;font-weight:bold;margin:14px 0 6px}
.hero .accent{color:#0E7A5F}
.card{background:#FFFDF4;border:3px solid #20242E;border-radius:16px;padding:16px;margin-top:14px;
box-shadow:0 4px 0 rgba(32,36,46,.12)}
.cardtitle{font-size:24px;font-weight:bold}
.step{display:flex;gap:12px;align-items:flex-start;margin-top:12px}
.num{background:#DCEBFF;color:#123A7A;border-radius:10px;font-weight:bold;padding:2px 10px;font-size:20px}
.box{border-radius:16px;padding:14px;margin-top:14px;border:3px solid;box-shadow:0 4px 0 rgba(32,36,46,.12)}
.blue{background:#DCEBFF;border-color:#2456A6}.blue b{color:#123A7A}
.amber{background:#FFE3B3;border-color:#9A5B00}.amber b{color:#6B3E00}
.purple{background:#EADCF8;border-color:#5B2EA6}.purple b{color:#351261}
.plain{background:#FFFDF4;border-color:#20242E}
.lbl{font-size:24px;font-weight:bold}
table{width:100%;border-collapse:collapse;font-size:21px}td{padding:8px;vertical-align:top}
textarea,input{width:100%;font-size:20px;font-family:Arial,Verdana,sans-serif;padding:10px;box-sizing:border-box;
border:2px solid #20242E;border-radius:10px;background:#FFFDF4}
button{font-size:22px;font-weight:bold;padding:12px 22px;margin-top:12px;background:#123A7A;color:#FFF6D6;
border:3px solid #123A7A;border-radius:12px;cursor:pointer;box-shadow:0 4px 0 rgba(32,36,46,.25)}
.langrow label{display:inline-block;border:3px solid #20242E;border-radius:999px;padding:4px 14px;
font-weight:bold;background:#FFFDF4;cursor:pointer;margin-right:8px;font-size:20px}
.langrow label:has(input:checked){background:#123A7A;color:#FFF6D6}
.langrow input{width:auto}
a{color:#123A7A;font-weight:bold}
"""

def _shell(inner):
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ClearDay</title><style>{CSS}</style></head><body><div class='wrap'>{inner}</div></body></html>"

def _topbar(right=""):
    return f"""<div class='topbar'><div class='brand'><div class='mark'>C<span>&#9650;</span></div>
<div><h1>ClearDay</h1><div class='brandsub'>A clearer way to read</div></div></div><div>{right}</div></div>"""

def render_form(extra="", lang="en"):
    s = S(lang)
    checked = {code: ("checked" if code == lang else "") for code in STRINGS}
    return _shell(f"""{_topbar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>")}
<div class='hero'>{s['hero1']}<br><span class='accent'>{s['hero2']}</span></div>
<div class='big'>{s['hero_sub']}</div>
<div class='card'><div class='cardtitle'>&#9632; {s['path_title']}</div>
<div>{s['path_sub']}</div>
<div class='step'><div class='num'>01</div><div><b>{s['step1']}</b></div></div>
<div class='step'><div class='num'>02</div><div><b>{s['step2']}</b></div></div>
<div class='step'><div class='num'>03</div><div><b>{s['step3']}</b></div></div></div>
{extra}
<div class='card'><form method='post'>
<p class='big'><b>{s['language']}</b></p>
<p class='langrow'>
<label><input type='radio' name='lang' value='en' {checked['en']}> EN</label>
<label><input type='radio' name='lang' value='es' {checked['es']}> ES</label>
<label><input type='radio' name='lang' value='vi' {checked['vi']}> VI</label></p>
<p><label class='big'><b>{s['from']}</b></label><input name='sender' placeholder='Maria Lopez'></p>
<p><label class='big'><b>{s['subject']}</b></label><input name='subject' placeholder='Meeting moved'></p>
<p><label class='big'><b>{s['paste']}</b></label><textarea name='text' rows='10'></textarea></p>
<p class='big'><b>{s['demo_warn']}</b></p>
<button type='submit'>{s['button']}</button></form></div>
<p class='big'><a href='/followups'>{s['see_followups']}</a></p>""")

def render_page(p):
    s = S(p.get("lang", "en"))
    actions = "".join(f"<div class='big'>{i}. {esc(a)}</div>" for i, a in enumerate(p.get("actions", []), 1))
    facts = "".join(f"<tr><td style='width:32%'><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in (p.get("facts") or {}).items())
    dates = "".join(f"<div style='font-size:26px'><b>{esc(d)}</b></div>" for d in p.get("dates_numbers", [])) or f"<div class='big'>{s['no_dates']}</div>"
    steps = " &rarr; ".join(esc(x) for x in p.get("steps", []))
    risk = f"<div class='box plain'><span class='lbl'>&#9650; {s['risk']}</span><div class='big'>{esc(p['risk'])}</div></div>" if p.get("risk") else ""
    if p.get("source") == "model":
        short_model = esc(str(p.get("model_name", "")).split("/")[-1])
        pill = f"<span class='pill pill-ai'>&#9679; {s['ai_live']}" + (f" &middot; {short_model}" if short_model else "") + "</span>"
    else:
        pill = f"<span class='pill'>&#9670; {s['ai_rules']}</span>"
    return _shell(f"""{_topbar(pill)}
<p class='big'><b>{s['demo_page']}</b></p>
<div class='box blue'><span class='lbl'>&#9632; {s['what']}</span><div class='big'>{esc(p.get('what',''))}</div></div>
<div class='box amber'><span class='lbl'>&#9654; {s['do']}</span>{actions}</div>
<div class='box purple'><span class='lbl'>&#9679; {s['facts']}</span><table>{facts}</table></div>
<div class='box plain'><span class='lbl'>&#9670; {s['dates']}</span>{dates}</div>
{risk}
<p class='big' style='margin-top:16px;'>{s['steps']}: {steps}</p>
<p style='font-size:18px;'>{s['source']}: {esc(p.get('sender',''))} &middot; {esc(p.get('source_date',''))}</p>
<p class='big'><a href='/'>{s['another']}</a> &middot; <a href='/followups'>{s['followups']}</a></p>""")
