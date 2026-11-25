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
           "nav_clear": "Clear page", "nav_followups": "Follow-ups", "nav_proof": "Connector proof",
           "nav_inbox": "Inbox", "inbox_title": "THE INBOX - the before picture",
           "thinking": "AI is thinking - reading your message...",
           "reply_title": "REPLY", "reply_btn": "Draft a reply", "reply_btn_draft": "Draft a reply",
           "reply_note": "ClearDay drafts the reply with the AI. You read it first. Nothing is sent until you press Send.",
           "reply_draft_only": "Draft only here - sending works from the Inbox, where the sender's real address lives.",
           "reply_sent_title": "REPLY SENT", "reply_draft_title": "YOUR REPLY DRAFT",
           "reply_to": "To", "reply_subject": "Subject", "followups_reply": "Reply",
           "send_btn": "Send this reply", "dont_send": "No - don't send it", "draft_check": "Read it first. Nothing is sent until you press Send.", "edit_hint": "You can change any words in the box. Then press Send.", "no_send_here": "NO SEND BUTTON ON THIS PAGE", "no_send_why": "This draft came from the paste box. We have the name, but not the real email address. To send a reply: open the email from the Inbox, then press Draft a reply - the Send button is there.",
           "inbox_line": "This is a real inbox (Mailpit). Real email arrives here and sits in small, dense text - hard to read. That is the problem ClearDay fixes.",
           "inbox_clear": "Make it clear", "inbox_empty": "The inbox is empty.",
           "inbox_seed": "Send the sample email into this inbox",
           "inbox_down": "The inbox is resting right now. The paste form still works.",
           "inbox_raw": "See the raw inbox (Mailpit)",
           "inbox_raw_note": "Small, dense, gray text - not dyslexia-friendly. Shown on purpose: that is what ClearDay replaces.",
           "sample_title": "Fastest way to test", "sample_btn": "Load the sample email",
           "sample_line": "No email handy? One press fills the form below with a real sample board email. You see it first — then press Make it clear.",
           "sample_loaded": "Sample loaded in the form — read it, then press Make it clear.",
           "trust1": "Dates copied exactly — never invented", "trust2": "Same order, every time",
           "trust3": "Cream page + big type — the research, not fashion",
           "why_title": "Why the cream page? For judges",
           "why1": "Cream, not white — warm backgrounds tested best for dyslexic readers; pure white glares (Rello & Baeza-Yates)",
           "why2": "Arial, bold, no italics — eye-tracking, 48 dyslexic readers: italics were the slowest (ACM ASSETS 2013)",
           "why3": "Wide letter spacing — reading errors cut in half in 74 dyslexic children (PNAS 2012)",
           "why4": "Short lines, one column — 27% faster reading, backward eye jumps cut by more than half (Harvard–Smithsonian, 2013)",
           "why5": "Color never works alone — every box has a big label + a shape (WCAG 2.2 AA)",
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
           "nav_clear": "Página clara", "nav_followups": "Seguimientos", "nav_proof": "Prueba de conexión",
           "nav_inbox": "Bandeja", "inbox_title": "LA BANDEJA - la foto del antes",
           "thinking": "La IA está pensando - leyendo tu mensaje...",
           "reply_title": "RESPUESTA", "reply_btn": "Redactar y enviar una respuesta", "reply_btn_draft": "Redactar una respuesta",
           "reply_note": "ClearDay redacta la respuesta con la IA. Tú la lees primero. Nada se envía hasta que presiones Enviar.",
           "reply_draft_only": "Aquí solo el borrador - el envío funciona desde la Bandeja, donde está la dirección real del remitente.",
           "reply_sent_title": "RESPUESTA ENVIADA", "reply_draft_title": "TU BORRADOR DE RESPUESTA",
           "reply_to": "Para", "reply_subject": "Asunto", "followups_reply": "Responder",
           "send_btn": "Enviar esta respuesta", "dont_send": "No - no lo envíes", "draft_check": "Léelo primero. Nada se envía hasta que presiones Enviar.", "edit_hint": "Puedes cambiar las palabras en el cuadro. Luego presiona Enviar.", "no_send_here": "EN ESTA PÁGINA NO HAY BOTÓN DE ENVIAR", "no_send_why": "Este borrador vino del cuadro de pegar. Tenemos el nombre, pero no la dirección real. Para enviar una respuesta: abre el correo desde la Bandeja y presiona Redactar una respuesta - allí está el botón Enviar.",
           "inbox_line": "Esta es una bandeja real (Mailpit). El correo real llega aquí y queda en texto pequeño y denso - difícil de leer. Ese es el problema que ClearDay resuelve.",
           "inbox_clear": "Hazlo claro", "inbox_empty": "La bandeja está vacía.",
           "inbox_seed": "Enviar el correo de ejemplo a esta bandeja",
           "inbox_down": "La bandeja está descansando ahora. El formulario para pegar sigue funcionando.",
           "inbox_raw": "Ver la bandeja sin procesar (Mailpit)",
           "inbox_raw_note": "Texto pequeño, denso y gris - no apto para dislexia. Se muestra a propósito: eso es lo que ClearDay reemplaza.",
           "sample_title": "La forma más rápida de probar", "sample_btn": "Cargar el correo de ejemplo",
           "sample_line": "¿Sin un correo a mano? Un botón llena el formulario con un correo real de ejemplo de la junta. Lo ves primero — luego pulsa Hazlo claro.",
           "sample_loaded": "Ejemplo cargado en el formulario — léelo y pulsa Hazlo claro.",
           "trust1": "Fechas copiadas exactas — nunca inventadas", "trust2": "El mismo orden, siempre",
           "trust3": "Página crema y letra grande — la investigación, no la moda",
           "why_title": "¿Por qué la página crema? Para los jueces",
           "why1": "Crema, no blanco — los fondos cálidos fueron los mejores para lectores con dislexia; el blanco puro deslumbra (Rello y Baeza-Yates)",
           "why2": "Arial, negrita, sin cursiva — seguimiento ocular en 48 lectores con dislexia: la cursiva fue lo más lento (ACM ASSETS 2013)",
           "why3": "Espaciado amplio entre letras — los errores de lectura se redujeron a la mitad en 74 niños con dislexia (PNAS 2012)",
           "why4": "Líneas cortas, una columna — lectura 27% más rápida y menos de la mitad de saltos hacia atrás (Harvard–Smithsonian, 2013)",
           "why5": "El color nunca actúa solo — cada caja tiene una etiqueta grande y una forma (WCAG 2.2 AA)",
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
           "nav_clear": "Trang rõ ràng", "nav_followups": "Việc cần theo dõi", "nav_proof": "Bằng chứng kết nối",
           "nav_inbox": "Hộp thư", "inbox_title": "HỘP THƯ - hình ảnh trước",
           "thinking": "AI đang suy nghĩ - đang đọc tin nhắn của bạn...",
           "reply_title": "TRẢ LỜI", "reply_btn": "Soạn và gửi trả lời", "reply_btn_draft": "Soạn thư trả lời",
           "reply_note": "ClearDay soạn thư trả lời bằng AI. Bạn đọc trước. Chưa có gì được gửi cho đến khi bạn nhấn Gửi.",
           "reply_draft_only": "Ở đây chỉ là bản nháp - gửi được từ Hộp thư, nơi có địa chỉ thật của người gửi.",
           "reply_sent_title": "ĐÃ GỬI TRẢ LỜI", "reply_draft_title": "BẢN NHÁP TRẢ LỜI CỦA BẠN",
           "reply_to": "Đến", "reply_subject": "Tiêu đề", "followups_reply": "Trả lời",
           "send_btn": "Gửi thư trả lời này", "dont_send": "Không - đừng gửi", "draft_check": "Đọc trước. Chưa có gì được gửi cho đến khi bạn nhấn Gửi.", "edit_hint": "Bạn có thể sửa bất kỳ từ nào trong khung. Rồi nhấn Gửi.", "no_send_here": "TRANG NÀY KHÔNG CÓ NÚT GỬI", "no_send_why": "Bản nháp này đến từ khung dán. Chúng ta có tên, nhưng không có địa chỉ email thật. Để gửi thư trả lời: mở email từ Hộp thư, rồi nhấn Soạn thư trả lời - nút Gửi ở đó.",
           "inbox_line": "Đây là hộp thư thật (Mailpit). Email thật đến đây và nằm trong chữ nhỏ, dày - khó đọc. Đó là vấn đề ClearDay giải quyết.",
           "inbox_clear": "Làm rõ", "inbox_empty": "Hộp thư trống.",
           "inbox_seed": "Gửi email mẫu vào hộp thư này",
           "inbox_down": "Hộp thư đang nghỉ. Biểu mẫu dán vẫn hoạt động.",
           "inbox_raw": "Xem hộp thư thô (Mailpit)",
           "inbox_raw_note": "Chữ nhỏ, dày, xám - không thân thiện với chứng khó đọc. Cố ý hiển thị: đó là thứ ClearDay thay thế.",
           "sample_title": "Cách thử nhanh nhất", "sample_btn": "Nạp email mẫu",
           "sample_line": "Không có email sẵn? Một lần nhấn sẽ điền email mẫu thật của ban vào biểu mẫu bên dưới. Bạn xem trước — rồi nhấn Làm rõ.",
           "sample_loaded": "Đã nạp mẫu vào biểu mẫu — xem lại rồi nhấn Làm rõ.",
           "trust1": "Ngày tháng sao chép chính xác — không bao giờ bịa ra", "trust2": "Cùng thứ tự, mọi lần",
           "trust3": "Trang màu kem + chữ lớn — theo nghiên cứu, không theo thời trang",
           "why_title": "Vì sao trang màu kem? Dành cho giám khảo",
           "why1": "Màu kem, không phải trắng — nền ấm cho kết quả tốt nhất với người khó đọc; trắng tinh gây chói (Rello & Baeza-Yates)",
           "why2": "Arial, chữ đậm, không nghiêng — theo dõi mắt 48 người khó đọc: chữ nghiêng chậm nhất (ACM ASSETS 2013)",
           "why3": "Khoảng cách chữ rộng — lỗi đọc giảm một nửa ở 74 trẻ khó đọc (PNAS 2012)",
           "why4": "Dòng ngắn, một cột — đọc nhanh hơn 27%, số lần mắt nhảy ngược giảm hơn một nửa (Harvard–Smithsonian, 2013)",
           "why5": "Màu sắc không bao giờ đứng một mình — mỗi hộp có nhãn lớn + hình dạng (WCAG 2.2 AA)",
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
a.btn{display:inline-block;background:#0E7A5F;color:#FFF6D6;border:3px solid #0E7A5F;border-radius:12px;
padding:12px 22px;font-size:22px;font-weight:bold;text-decoration:none;box-shadow:0 4px 0 rgba(32,36,46,.25);margin-top:10px}
.navrow{display:flex;gap:26px;flex-wrap:wrap;border-bottom:3px solid rgba(32,36,46,.15);padding:8px 0 12px;margin-bottom:6px}
.navrow a{text-decoration:none;color:#20242E}
.thinking{display:none;background:#123A7A;color:#FFF6D6;border-radius:16px;padding:18px 22px;font-size:24px;font-weight:bold;margin-bottom:14px}
.thinking .dot{display:inline-block;animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:.15}}
@media (prefers-reduced-motion: reduce){.thinking .dot{animation:none}}
.layout{display:block}
.trust div{margin-top:8px}
.why div{margin-top:10px}
@media(min-width:920px){.wrap{max-width:1080px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:16px;align-items:start}}
"""

def _shell(inner, s):
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ClearDay</title><style>{CSS}</style></head><body><div class='wrap'><div class='thinking' id='thinking'><span class='dot'>&#9679;</span> {s['thinking']}</div>{inner}</div><script>
function showThinking(){{var t=document.getElementById('thinking');if(t){{t.style.display='block';window.scrollTo(0,0);}}}}
document.addEventListener('submit',function(e){{if((e.target.getAttribute('action')||'').indexOf('/inbox/seed')>=0)return;showThinking();var b=e.target.querySelector('button[type=submit]');if(b){{b.disabled=true;}}}});
document.addEventListener('click',function(e){{var a=e.target.closest?e.target.closest('a.btn'):null;if(a){{var h=a.getAttribute('href')||'';if(h.indexOf('/inbox/clear')>=0||h.indexOf('sample=1')>=0||h.indexOf('/sample')>=0){{showThinking();}}}}var b=e.target.closest?e.target.closest('button[type=submit]'):null;if(b&&b.form&&(b.form.getAttribute('action')||'').indexOf('/inbox/seed')<0){{showThinking();}}}});
</script></body></html>"""

def _bar(right, s):
    return f"""<div class='topbar'><div class='brand'><div class='mark'>C<span>&#9650;</span></div>
<div><h1>ClearDay</h1><div class='brandsub'>A clearer way to read</div></div></div><div>{right}</div></div>
<div class='navrow'><a href='/'>{s['nav_clear']}</a><a href='/inbox'>{s['nav_inbox']}</a><a href='/followups'>{s['nav_followups']}</a><a href='/connected'>{s['nav_proof']}</a></div>"""

def _why_card(s):
    items = "".join(f"<div>&#10003; {s[k]}</div>" for k in ("why1", "why2", "why3", "why4", "why5"))
    return f"<div class='card why'><div class='cardtitle'>&#9670; {s['why_title']}</div>{items}</div>"

def render_inbox(messages, lang="en", down=False):
    s = S(lang)
    if down:
        body = f"<div class='card'><p class='big'>{s['inbox_down']}</p></div>"
    elif not messages:
        body = f"<div class='card'><p class='big'>{s['inbox_empty']}</p></div>"
    else:
        cards = ""
        for m in messages:
            frm = m.get("From") or {}
            who = esc(frm.get("Name") or frm.get("Address") or "")
            when = esc((m.get("Created") or "")[:16].replace("T", " "))
            cards += (f"<div class='card'><div class='big'><b>{who}</b></div>"
                      f"<div class='big'>{esc(m.get('Subject') or '')}</div>"
                      f"<div>{when}</div>"
                      f"<p><a class='btn' href='/inbox/clear?id={esc(m.get('ID') or '')}&lang={lang}'>{s['inbox_clear']}</a></p></div>")
        body = cards
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
<h1>{s['inbox_title']}</h1>
<div class='card'><p>{s['inbox_line']}</p></div>
{body}
<div class='card'><form method='post' action='/inbox/seed?lang={lang}'><button type='submit'>{s['inbox_seed']}</button></form></div>
<div class='card'><div class='cardtitle'>&#9632; {s['inbox_raw']}</div>
<div>{s['inbox_raw_note']}</div>
<p><a href='/mailpit/'>Mailpit</a></p></div>""", s)

def render_form(extra="", lang="en", prefill=None):
    s = S(lang)
    checked = {code: ("checked" if code == lang else "") for code in STRINGS}
    pf = prefill or {}
    pf_sender = esc(pf.get("sender", ""))
    pf_subject = esc(pf.get("subject", ""))
    pf_text = esc(pf.get("text", ""))
    loaded = f"<p class='big'><b>&#10003; {s['sample_loaded']}</b></p>" if pf else ""
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
<div class='layout'><div>
<div class='hero'>{s['hero1']}<br><span class='accent'>{s['hero2']}</span></div>
<div class='big'>{s['hero_sub']}</div>
{extra}
<div class='card'><div class='cardtitle'>&#9654; {s['sample_title']}</div>
<div>{s['sample_line']}</div>
<p><a class='btn' href='/?sample=1&lang={lang}'>{s['sample_btn']}</a></p></div>
{loaded}
<div class='card'><form method='post'>
<p class='big'><b>{s['language']}</b></p>
<p class='langrow'>
<label><input type='radio' name='lang' value='en' {checked['en']}> EN</label>
<label><input type='radio' name='lang' value='es' {checked['es']}> ES</label>
<label><input type='radio' name='lang' value='vi' {checked['vi']}> VI</label></p>
<p><label class='big'><b>{s['from']}</b></label><input name='sender' placeholder='Maria Lopez' value='{pf_sender}'></p>
<p><label class='big'><b>{s['subject']}</b></label><input name='subject' placeholder='Meeting moved' value='{pf_subject}'></p>
<p><label class='big'><b>{s['paste']}</b></label><textarea name='text' rows='10'>{pf_text}</textarea></p>
<p class='big'><b>{s['demo_warn']}</b></p>
<button type='submit'>{s['button']}</button></form></div>
{_why_card(s)}
</div><div>
<div class='card'><div class='cardtitle'>&#9632; {s['path_title']}</div>
<div>{s['path_sub']}</div>
<div class='step'><div class='num'>01</div><div><b>{s['step1']}</b></div></div>
<div class='step'><div class='num'>02</div><div><b>{s['step2']}</b></div></div>
<div class='step'><div class='num'>03</div><div><b>{s['step3']}</b></div></div></div>
<div class='card trust'><div>&#10003; {s['trust1']}</div><div>&#10003; {s['trust2']}</div><div>&#10003; {s['trust3']}</div></div>
</div></div>
<p class='big'><a href='/followups'>{s['see_followups']}</a></p>""", s)

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
    reply_card = ""
    if p.get("_text") is not None:
        can_send = bool(p.get("_addr"))
        btn = s['reply_btn'] if can_send else s['reply_btn_draft']
        note = s['reply_note'] if can_send else s['reply_draft_only']
        reply_card = f"""<div class='card'><div class='cardtitle'>&#9993; {s['reply_title']}</div>
<div>{note}</div>
<form method='post' action='/reply'>
<input type='hidden' name='mid' value='{esc(p.get("_mid", ""))}'>
<input type='hidden' name='sender' value='{esc(p.get("sender", ""))}'>
<input type='hidden' name='subject' value='{esc(p.get("_subject", ""))}'>
<input type='hidden' name='lang' value='{esc(p.get("lang", "en"))}'>
<textarea name='text' style='display:none'>{esc(p.get("_text", ""))}</textarea>
<p><button type='submit'>{btn}</button></p></form></div>"""
    return _shell(f"""{_bar(pill, s)}
<p class='big'><b>{s['demo_page']}</b></p>
<div class='box blue'><span class='lbl'>&#9632; {s['what']}</span><div class='big'>{esc(p.get('what',''))}</div></div>
<div class='box amber'><span class='lbl'>&#9654; {s['do']}</span>{actions}</div>
<div class='box purple'><span class='lbl'>&#9679; {s['facts']}</span><table>{facts}</table></div>
<div class='box plain'><span class='lbl'>&#9670; {s['dates']}</span>{dates}</div>
{risk}
<p class='big' style='margin-top:16px;'>{s['steps']}: {steps}</p>
<p style='font-size:18px;'>{s['source']}: {esc(p.get('sender',''))} &middot; {esc(p.get('source_date',''))}</p>
{reply_card}
{_why_card(s)}
<p class='big'><a href='/'>{s['another']}</a> &middot; <a href='/followups'>{s['followups']}</a></p>""", s)

def render_reply_draft(to, subject, body_text, lang="en", mid="", addr=""):
    s = S(lang)
    box = "width:100%;font-size:21px;line-height:1.7;font-family:Arial,Verdana,sans-serif;padding:12px;margin-top:12px;box-sizing:border-box;"
    send_form = ""
    if addr:
        send_form = f"""<form method='post' action='/reply/send'>
<input type='hidden' name='mid' value='{esc(mid)}'>
<input type='hidden' name='to' value='{esc(addr)}'>
<input type='hidden' name='subject' value='{esc(subject)}'>
<input type='hidden' name='lang' value='{esc(lang)}'>
<div>{s['edit_hint']}</div>
<textarea name='body' rows='9' style='{box}'>{esc(body_text)}</textarea>
<p><button type='submit'>{s['send_btn']}</button></p></form>
<p class='big'><a href='/inbox'>{s['dont_send']}</a></p>"""
    else:
        send_form = f"""<div class='box amber'><span class='lbl'>&#9650; {s['no_send_here']}</span><div class='big'>{s['no_send_why']}</div></div>
<div>{s['edit_hint']}</div>
<textarea rows='9' style='{box}'>{esc(body_text)}</textarea>
<p class='big'>{s['reply_draft_only']}</p>"""
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
<h1>{s['reply_draft_title']}</h1>
<p class='big'><b>{s['draft_check']}</b></p>
<div class='card'><div class='big'><b>{s['reply_to']}:</b> {esc(to)}</div>
<div class='big'><b>{s['reply_subject']}:</b> {esc(subject)}</div>
{send_form}</div>
<p class='big'><a href='/followups'>{s['nav_followups']}</a> &middot; <a href='/'>{s['nav_clear']}</a></p>""", s)

def render_reply_sent(to, subject, body_text, sent, lang="en"):
    s = S(lang)
    title = s['reply_sent_title'] if sent else s['reply_draft_title']
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
<h1>{title}</h1>
<div class='card'><div class='big'><b>{s['reply_to']}:</b> {esc(to)}</div>
<div class='big'><b>{s['reply_subject']}:</b> {esc(subject)}</div>
<div style='white-space:pre-wrap;font-size:21px;line-height:1.7;margin-top:12px;'>{esc(body_text)}</div></div>
<p class='big'><a href='/inbox'>{s['nav_inbox']}</a> &middot; <a href='/followups'>{s['nav_followups']}</a> &middot; <a href='/'>{s['nav_clear']}</a></p>""", s)
