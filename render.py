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
import json
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
           "no_dates": "No dates found", "risk": "IF YOU DO NOTHING", "risk_none": "No deadline or danger found in this message.", "steps": "Steps", "source": "Source",
           "ai_live": "AI: live model response", "ai_rules": "Rules: instant answer — no model used",
           "hero1": "Long message in", "hero2": "one clear page out!",
           "hero_sub": "Built for people with dyslexia.",
           "path_title": "Your path to a clear page", "path_sub": "Three steps. No guesswork.",
           "step1": "Paste the long message", "step2": "Press the button", "step3": "Read one clear page — same order, every time",
           "brand_pill": "Built for dyslexic readers",
           "nav_clear": "Clear page", "nav_followups": "Follow-ups", "nav_proof": "Connector proof",
           "nav_inbox": "Inbox", "nav_why": "Why the cream page?",
           "nav_bulk": "Bulk clear", "bulk_title": "CLEAR THE WHOLE INBOX", "bulk_intro": "One press clears every email waiting in the demo inbox. You get one page: everything you must do first, then each email on its own card.",
           "bulk_btn": "Clear the whole inbox", "bulk_waiting": "emails waiting", "bulk_cleared": "emails cleared", "bulk_all": "EVERYTHING YOU MUST DO",
           "bulk_from": "from", "bulk_empty": "The inbox is empty. Nothing to clear.", "bulk_down": "The inbox is resting. Try again in a moment.",
           "bulk_cap": "Bulk clear takes up to 10 emails at a time. It can take a minute - the AI reads each one.", "bulk_open": "Open the clear page",
           "bulk_skip_own": "of your own replies, skipped", "bulk_skip_dupe": "already waiting as follow-ups, skipped", "bulk_failed": "could not be read",
           "proof_title": "CONNECTOR PROOF", "proof_sub": "Every number on this page was fetched live, the moment you opened it. Nothing here is typed in by hand.",
           "proof_checked": "Checked at", "proof_live": "LIVE - working now", "proof_down": "DOWN",
           "proof_source": "Source", "proof_ms": "answered in", "proof_ask": "We asked the model", "proof_said": "The model answered",
           "t_repos": "Public repos", "t_rate": "API calls left", "t_commit": "Newest commit", "t_models": "Models this account can use", "t_tokens": "Tokens in the test call", "t_speed": "Test call took",
           "r_account": "Account", "r_updated": "Repo last updated", "r_model": "Our model", "r_onlist": "On the list", "r_callid": "Call ID",
           "proof_note": "No typed-in numbers. If a connector is down, this page says DOWN and shows the real error. It never invents a number.",
 "inbox_title": "THE INBOX - the before picture",
           "thinking": "AI is thinking - reading your message...",
           "reply_title": "REPLY", "reply_next": "Click Draft a reply after reading the email.", "reply_btn": "Draft a reply", "reply_btn_draft": "Draft a reply",
           "reply_note": "First you read the draft, and then, you approve it by pressing the send button.",
           "reply_draft_only": "You read the draft first. Nothing is sent until you press Send.",
           "reply_sent_title": "REPLY SENT", "raw_close": "Close - back to my story", "see_line": "See for yourself", "fresh_step1": "A brand-new email from Maria is on its way to you...", "fresh_step2": "It just landed in the raw inbox. This is what I see:", "story_btn": "Read my story", "see_email": "See the email", "raw_close_plain": "Close", "story_close": "Close", "raw_dialog_title": "The raw inbox - this is what I see", "found_addr": "Good news - we found the real address in the raw inbox:", "sent_see": "Your email was sent and landed in Mailpit, right next to Maria's email to you. Go see both:", "sent_both": "See both emails in Mailpit", "sent_mailpit": "Open Mailpit", "reply_draft_title": "YOUR REPLY DRAFT",
           "reply_to": "To", "reply_subject": "Subject", "followups_reply": "Reply",
           "send_btn": "Send this reply", "dont_send": "No - don't send it", "draft_check": "Below, please read the proposed draft reply email generated for you. Please feel free to revise it and afterwards, approve it by pressing the dark blue Send this reply button. Thank you.", "edit_hint": "You can change any words in the box. Then press Send.", "no_send_here": "NO SEND BUTTON ON THIS PAGE", "no_send_why": "We have the words, but no real email address to send to - the raw inbox is empty. Go to the clear page and press Mailpit: a fresh email from Maria lands there. Then draft the reply again, and the Send button will be here.",
           "inbox_line": "This is a real inbox (Mailpit). Real email arrives here and sits in small, dense text - hard to read. That is the problem ClearDay fixes.",
           "inbox_clear": "Make it clear", "inbox_empty": "The inbox is empty.",
           "inbox_seed": "Send the sample email into this inbox",
           "inbox_down": "The inbox is resting right now. The paste form still works.",
           "inbox_raw": "See the raw inbox (Mailpit)",
           "inbox_raw_note": "Before you judge this app, please take a moment to experience what it is like to be dyslexic.\nAn email like the one below, which is long, tangled up, and in small dense gray text - can take me three tries reading before it gives up its meaning to me.\nSee for yourself [[MAILPIT]]. That is why I created ClearDay, so I can help folks like me and be thankful this Thanksgiving to give something back to the world. :)",
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
           "no_dates": "No se encontraron fechas", "risk": "SI NO HACES NADA", "risk_none": "No se encontró fecha límite ni peligro en este mensaje.", "steps": "Pasos", "source": "Fuente",
           "ai_live": "IA: respuesta en vivo del modelo", "ai_rules": "Reglas: respuesta instantánea — sin modelo",
           "hero1": "Mensaje largo entra", "hero2": "una página clara sale!",
           "hero_sub": "Hecho para personas con dislexia.",
           "path_title": "Tu camino a una página clara", "path_sub": "Tres pasos. Sin adivinar.",
           "step1": "Pega el mensaje largo", "step2": "Pulsa el botón", "step3": "Lee una página clara — el mismo orden, siempre",
           "brand_pill": "Hecho para lectores con dislexia",
           "nav_clear": "Página clara", "nav_followups": "Seguimientos", "nav_proof": "Prueba de conexión",
           "nav_inbox": "Bandeja", "nav_why": "¿Por qué la página crema?",
           "nav_bulk": "Limpiar todo", "bulk_title": "HAZ CLARA TODA LA BANDEJA", "bulk_intro": "Un toque hace claras todas las cartas de la bandeja. Recibes una página: primero todo lo que debes hacer, y luego cada carta en su propia tarjeta.",
           "bulk_btn": "Hacer clara toda la bandeja", "bulk_waiting": "cartas esperando", "bulk_cleared": "cartas claras", "bulk_all": "TODO LO QUE DEBES HACER",
           "bulk_from": "de", "bulk_empty": "La bandeja está vacía. Nada que limpiar.", "bulk_down": "La bandeja está descansando. Inténtalo en un momento.",
           "bulk_cap": "Se limpian hasta 10 cartas por vez. Puede tardar un minuto: la IA lee cada una.", "bulk_open": "Abrir la página clara",
           "bulk_skip_own": "respuestas tuyas, saltadas", "bulk_skip_dupe": "ya en seguimiento, saltadas", "bulk_failed": "no se pudieron leer",
           "proof_title": "PRUEBA DE CONEXIÓN", "proof_sub": "Cada número de esta página se obtuvo en vivo, en el momento en que la abriste. Nada aquí está escrito a mano.",
           "proof_checked": "Comprobado a las", "proof_live": "EN VIVO - funcionando ahora", "proof_down": "CAÍDO",
           "proof_source": "Fuente", "proof_ms": "respondió en", "proof_ask": "Le preguntamos al modelo", "proof_said": "El modelo respondió",
           "t_repos": "Repositorios públicos", "t_rate": "Llamadas API restantes", "t_commit": "Confirmación más reciente", "t_models": "Modelos que esta cuenta puede usar", "t_tokens": "Tokens en la llamada de prueba", "t_speed": "La llamada tardó",
           "r_account": "Cuenta", "r_updated": "Repositorio actualizado", "r_model": "Nuestro modelo", "r_onlist": "En la lista", "r_callid": "ID de la llamada",
           "proof_note": "Sin números escritos a mano. Si una conexión está caída, esta página dice CAÍDO y muestra el error real. Nunca inventa un número.",
 "inbox_title": "LA BANDEJA - la foto del antes",
           "thinking": "La IA está pensando - leyendo tu mensaje...",
           "reply_title": "RESPUESTA", "reply_next": "Presiona Redactar una respuesta después de leer el correo.", "reply_btn": "Redactar y enviar una respuesta", "reply_btn_draft": "Redactar una respuesta",
           "reply_note": "Primero lees el borrador, y luego, lo apruebas al presionar el botón Enviar.",
           "reply_draft_only": "Primero lees el borrador. Nada se envía hasta que presiones Enviar.",
           "reply_sent_title": "RESPUESTA ENVIADA", "raw_close": "Cerrar - volver a mi historia", "see_line": "Míralo por ti mismo", "fresh_step1": "Un correo nuevo de Maria viene en camino para ti...", "fresh_step2": "Acaba de llegar a la bandeja cruda. Esto es lo que yo veo:", "story_btn": "Lee mi historia", "see_email": "Ver el correo", "raw_close_plain": "Cerrar", "story_close": "Cerrar", "raw_dialog_title": "La bandeja sin procesar - esto es lo que yo veo", "found_addr": "Buenas noticias: encontramos la dirección real en la bandeja cruda:", "sent_see": "Tu correo fue enviado y llegó a Mailpit, junto al correo de Maria para ti. Ve a ver ambos:", "sent_both": "Ver ambos correos en Mailpit", "sent_mailpit": "Abrir Mailpit", "reply_draft_title": "TU BORRADOR DE RESPUESTA",
           "reply_to": "Para", "reply_subject": "Asunto", "followups_reply": "Responder",
           "send_btn": "Enviar esta respuesta", "dont_send": "No - no lo envíes", "draft_check": "Abajo, por favor lee el correo del borrador de respuesta propuesto, generado para ti. Siéntete libre de revisarlo y, después, apruébalo al presionar el botón azul oscuro Enviar esta respuesta. Gracias.", "edit_hint": "Puedes cambiar las palabras en el cuadro. Luego presiona Enviar.", "no_send_here": "EN ESTA PÁGINA NO HAY BOTÓN DE ENVIAR", "no_send_why": "Tenemos las palabras, pero no una dirección real a la que enviar: la bandeja cruda está vacía. Ve a la página clara y presiona Mailpit: un correo nuevo de Maria llega allí. Luego redacta la respuesta otra vez y el botón Enviar estará aquí.",
           "inbox_line": "Esta es una bandeja real (Mailpit). El correo real llega aquí y queda en texto pequeño y denso - difícil de leer. Ese es el problema que ClearDay resuelve.",
           "inbox_clear": "Hazlo claro", "inbox_empty": "La bandeja está vacía.",
           "inbox_seed": "Enviar el correo de ejemplo a esta bandeja",
           "inbox_down": "La bandeja está descansando ahora. El formulario para pegar sigue funcionando.",
           "inbox_raw": "Ver la bandeja sin procesar (Mailpit)",
           "inbox_raw_note": "Texto pequeño, denso y gris - no apto para dislexia. [[MAILPIT]] Se muestra a propósito: eso es lo que ClearDay reemplaza.",
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
           "no_dates": "Không tìm thấy ngày nào", "risk": "NẾU BẠN KHÔNG LÀM GÌ", "risk_none": "Không tìm thấy hạn chót hay nguy hiểm nào trong tin nhắn này.", "steps": "Các bước", "source": "Nguồn",
           "ai_live": "AI: phản hồi trực tiếp từ mô hình", "ai_rules": "Quy tắc: trả lời ngay — không dùng mô hình",
           "hero1": "Đưa vào tin nhắn dài", "hero2": "nhận lại một trang rõ ràng!",
           "hero_sub": "Làm cho người mắc chứng khó đọc.",
           "path_title": "Đường tới một trang rõ ràng", "path_sub": "Ba bước. Không phải đoán.",
           "step1": "Dán tin nhắn dài", "step2": "Nhấn nút", "step3": "Đọc một trang rõ ràng — cùng thứ tự, mọi lần",
           "brand_pill": "Làm cho người đọc khó đọc",
           "nav_clear": "Trang rõ ràng", "nav_followups": "Việc cần theo dõi", "nav_proof": "Bằng chứng kết nối",
           "nav_inbox": "Hộp thư", "nav_why": "Vì sao trang màu kem?",
           "nav_bulk": "Làm rõ hết", "bulk_title": "LÀM RÕ CẢ HỘP THƯ", "bulk_intro": "Một lần nhấn làm rõ mọi thư đang chờ trong hộp thư. Bạn nhận một trang: trước hết là mọi việc phải làm, rồi mỗi thư một thẻ riêng.",
           "bulk_btn": "Làm rõ cả hộp thư", "bulk_waiting": "thư đang chờ", "bulk_cleared": "thư đã làm rõ", "bulk_all": "MỌI VIỆC BẠN PHẢI LÀM",
           "bulk_from": "từ", "bulk_empty": "Hộp thư trống. Không có gì để làm rõ.", "bulk_down": "Hộp thư đang nghỉ. Thử lại sau một lát.",
           "bulk_cap": "Mỗi lần làm rõ tối đa 10 thư. Có thể mất một phút — AI đọc từng thư.", "bulk_open": "Mở trang rõ ràng",
           "bulk_skip_own": "thư trả lời của bạn, đã bỏ qua", "bulk_skip_dupe": "đã có trong danh sách theo dõi, đã bỏ qua", "bulk_failed": "không đọc được",
           "proof_title": "BẰNG CHỨNG KẾT NỐI", "proof_sub": "Mọi con số trên trang này được lấy trực tiếp, ngay lúc bạn mở trang. Không có gì ở đây được gõ tay.",
           "proof_checked": "Kiểm tra lúc", "proof_live": "ĐANG HOẠT ĐỘNG", "proof_down": "KHÔNG HOẠT ĐỘNG",
           "proof_source": "Nguồn", "proof_ms": "trả lời trong", "proof_ask": "Chúng tôi đã hỏi mô hình", "proof_said": "Mô hình đã trả lời",
           "t_repos": "Kho công khai", "t_rate": "Lượt gọi API còn lại", "t_commit": "Commit mới nhất", "t_models": "Số mô hình tài khoản này dùng được", "t_tokens": "Token trong lần gọi thử", "t_speed": "Lần gọi thử mất",
           "r_account": "Tài khoản", "r_updated": "Kho cập nhật lần cuối", "r_model": "Mô hình của chúng tôi", "r_onlist": "Có trong danh sách", "r_callid": "ID lần gọi",
           "proof_note": "Không có con số gõ tay. Nếu một kết nối hỏng, trang này báo KHÔNG HOẠT ĐỘNG và hiện lỗi thật. Nó không bao giờ bịa ra con số.",
 "inbox_title": "HỘP THƯ - hình ảnh trước",
           "thinking": "AI đang suy nghĩ - đang đọc tin nhắn của bạn...",
           "reply_title": "TRẢ LỜI", "reply_next": "Nhấn Soạn thư trả lời sau khi đọc email.", "reply_btn": "Soạn và gửi trả lời", "reply_btn_draft": "Soạn thư trả lời",
           "reply_note": "Đầu tiên bạn đọc bản nháp, và sau đó, bạn duyệt nó bằng cách nhấn nút Gửi.",
           "reply_draft_only": "Bạn đọc bản nháp trước. Không có gì được gửi cho đến khi bạn nhấn Gửi.",
           "reply_sent_title": "ĐÃ GỬI TRẢ LỜI", "raw_close": "Đóng - quay lại câu chuyện của tôi", "see_line": "Hãy tự xem", "fresh_step1": "Một email hoàn toàn mới từ Maria đang trên đường đến với bạn...", "fresh_step2": "Nó vừa đến hộp thư thô. Đây là những gì tôi thấy:", "story_btn": "Đọc câu chuyện của tôi", "see_email": "Xem thư", "raw_close_plain": "Đóng", "story_close": "Đóng", "raw_dialog_title": "Hộp thư thô - đây là những gì tôi thấy", "found_addr": "Tin vui - chúng tôi tìm thấy địa chỉ thật trong hộp thư thô:", "sent_see": "Thư của bạn đã được gửi và đã đến Mailpit, ngay cạnh email của Maria gửi bạn. Hãy xem cả hai:", "sent_both": "Xem cả hai email trong Mailpit", "sent_mailpit": "Mở Mailpit", "reply_draft_title": "BẢN NHÁP TRẢ LỜI CỦA BẠN",
           "reply_to": "Đến", "reply_subject": "Tiêu đề", "followups_reply": "Trả lời",
           "send_btn": "Gửi thư trả lời này", "dont_send": "Không - đừng gửi", "draft_check": "Bên dưới, xin hãy đọc email nháp trả lời được đề xuất, tạo ra cho bạn. Xin cứ tự nhiên sửa lại nó và sau đó, duyệt nó bằng cách nhấn nút Gửi thư trả lời này màu xanh đậm. Cảm ơn bạn.", "edit_hint": "Bạn có thể sửa bất kỳ từ nào trong khung. Rồi nhấn Gửi.", "no_send_here": "TRANG NÀY KHÔNG CÓ NÚT GỬI", "no_send_why": "Chúng ta có nội dung, nhưng không có địa chỉ email thật để gửi: hộp thư thô đang trống. Hãy vào trang rõ ràng và nhấn Mailpit: một email mới từ Maria sẽ đến đó. Rồi soạn thư trả lời lại, nút Gửi sẽ ở đây.",
           "inbox_line": "Đây là hộp thư thật (Mailpit). Email thật đến đây và nằm trong chữ nhỏ, dày - khó đọc. Đó là vấn đề ClearDay giải quyết.",
           "inbox_clear": "Làm rõ", "inbox_empty": "Hộp thư trống.",
           "inbox_seed": "Gửi email mẫu vào hộp thư này",
           "inbox_down": "Hộp thư đang nghỉ. Biểu mẫu dán vẫn hoạt động.",
           "inbox_raw": "Xem hộp thư thô (Mailpit)",
           "inbox_raw_note": "Chữ nhỏ, dày, xám - không thân thiện với chứng khó đọc. [[MAILPIT]] Cố ý hiển thị: đó là thứ ClearDay thay thế.",
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
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:12px 0}
.stat{background:#EFFAF4;border:3px solid #20242E;border-radius:16px;padding:14px 10px;text-align:center}
.stat .n{font-size:36px;font-weight:bold;line-height:1.15}
.stat .l{font-size:16px;margin-top:4px}
.prow{font-size:19px;margin-top:8px}
.card{background:#FFFDF4;border:3px solid #20242E;border-radius:16px;padding:16px;margin-top:14px;box-shadow:0 4px 0 rgba(32,36,46,.12)}
.replycard{border:4px solid #0E7A5F;background:#EFFAF4}
.bigbtn{width:100%;font-size:25px;padding:18px 20px;margin-top:10px;cursor:pointer;box-shadow:0 4px 0 rgba(32,36,46,.12)}
.sendbtn{background:#123A7A;color:#FFF6D6;border:3px solid #123A7A;border-radius:12px}
.rawbtn{padding:2px 16px;font-size:20px;vertical-align:baseline}
.freshtrack{height:20px;border:3px solid #20242E;border-radius:10px;background:#FFF6D6;overflow:hidden;margin:8px 0 12px}
#freshfill{height:100%;width:0%;background:#0E7A5F;transition:width .3s ease}
#freshmsg{font-weight:bold}
#seeemail{margin:10px 0 4px}
@media (prefers-reduced-motion: reduce){#freshfill{transition:none}}
.story-strip{padding:12px 16px}
.story-strip .big{margin:0}
dialog#rawbox{border:3px solid #20242E;border-radius:16px;padding:18px;width:min(940px,94vw);background:#FFFDF4;color:#20242E;font-size:21px;line-height:1.7}
dialog#rawbox::backdrop{background:rgba(32,36,46,.55)}
#rawbox iframe{width:100%;height:62vh;border:2px solid #20242E;border-radius:8px;background:#FFFFFF;margin-top:10px}
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
.cols2{display:block}
.trust div{margin-top:8px}
.why div{margin-top:10px}
@media(min-width:920px){.wrap{max-width:1080px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:16px;align-items:start}.cols2{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}.layout.even{grid-template-columns:1fr 1fr}}
"""

def _shell(inner, s):
    return f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ClearDay</title><style>{CSS}</style></head><body><div class='wrap'><div class='thinking' id='thinking'><span class='dot'>&#9679;</span> {s['thinking']}</div>{inner}</div><script>
function showThinking(){{var t=document.getElementById('thinking');if(t){{t.style.display='block';window.scrollTo(0,0);}}}}
document.addEventListener('submit',function(e){{if((e.target.getAttribute('action')||'').indexOf('/inbox/seed')>=0)return;showThinking();var b=e.target.querySelector('button[type=submit]');if(b){{b.disabled=true;}}}});
document.addEventListener('click',function(e){{var a=e.target.closest?e.target.closest('a.btn'):null;if(a){{var h=a.getAttribute('href')||'';if(h.indexOf('/inbox/clear')>=0||h.indexOf('sample=1')>=0||h.indexOf('/sample')>=0){{showThinking();}}}}var b=e.target.closest?e.target.closest('button[type=submit]'):null;if(b&&b.form&&(b.form.getAttribute('action')||'').indexOf('/inbox/seed')<0){{showThinking();}}}});

var STEP1=window.__fresh1, STEP2=window.__fresh2, creep=null;
function fresh(){{var msg=document.getElementById('freshmsg'),fill=document.getElementById('freshfill'),f=document.querySelector('#rawbox iframe');if(!msg||!fill){{land();return;}}var t0=Date.now();msg.textContent=STEP1;msg.style.display='';var se0=document.getElementById('seeemail');if(se0){{se0.style.display='none';}}fill.style.width='12%';var pct=12;if(creep){{clearInterval(creep);}}creep=setInterval(function(){{if(pct<72){{pct+=4;fill.style.width=pct+'%';}}}},120);fetch('/inbox/fresh',{{method:'POST'}}).then(function(r){{return r.json();}}).then(function(j){{var wait=Math.max(0,1600-(Date.now()-t0));setTimeout(function(){{if(creep){{clearInterval(creep);}}fill.style.width='88%';var done=function(){{if(f&&f.src.indexOf('/view/')<0){{return;}}fill.style.width='100%';msg.style.display='none';var se=document.getElementById('seeemail');if(se){{se.style.display='inline-block';}}if(f){{f.removeEventListener('load',done);}}}};if(j&&j.id&&f){{f.addEventListener('load',done);f.src='/mailpit/view/'+j.id;setTimeout(done,3000);}}else{{done();}}}},wait);}}).catch(function(){{if(creep){{clearInterval(creep);}}land();fill.style.width='100%';msg.style.display='none';var se2=document.getElementById('seeemail');if(se2){{se2.style.display='inline-block';}}}});}}
</script></body></html>"""

def _bar(right, s):
    return f"""<div class='topbar'><div class='brand'><div class='mark'>C<span>&#9650;</span></div>
<div><h1>ClearDay</h1><div class='brandsub'>A clearer way to read</div></div></div><div>{right}</div></div>
<div class='navrow'><a href='/'>{s['nav_clear']}</a><a href='/followups'>{s['nav_followups']}</a><a href='/bulk'>{s['nav_bulk']}</a><a href='/why'>{s['nav_why']}</a><a href='/connected'>{s['nav_proof']}</a></div>"""

def _why_card(s):
    items = "".join(f"<div>&#10003; {s[k]}</div>" for k in ("why1", "why2", "why3", "why4", "why5"))
    return f"<div class='card why'><div class='cardtitle'>&#9670; {s['why_title']}</div>{items}</div>"

def render_why(lang="en"):
    s = S(lang)
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
{_why_card(s)}
<div class='box plain'><p><a class='btn' href='/'>&#9993; {s['nav_clear']}</a></p></div>""", s)

def render_followups_page(rows_html, lang="en"):
    s = S(lang)
    return _shell(f"""{_bar("", s)}
<div class='box blue'><span class='lbl'>&#9679; {s['followups_title']}</span>
<p class='big'><b>{s['demo_entries']}</b></p>
{rows_html}</div>
<p class='big'><a href='/'>{s['nav_clear']}</a></p>""", s)


def render_bulk(lang="en", waiting=0, results=None, counts=None, up=True):
    s = S(lang)
    bar = _bar("", s)
    if not up:
        return _shell(f"""{bar}
<div class='box plain'><span class='lbl'>&#9670; {s['bulk_title']}</span><div class='big'>{s['bulk_down']}</div></div>
<p class='big'><a href='/'>{s['nav_clear']}</a></p>""", s)
    if results is None:
        if waiting == 0:
            body = f"<div class='big'>{s['bulk_empty']}</div>"
        else:
            body = f"""<div class='big'><b>{waiting}</b> {s['bulk_waiting']}</div>
<form method='post' action='/bulk/clear'>
<input type='hidden' name='lang' value='{esc(lang)}'>
<p><button type='submit' class='bigbtn'>&#9993; {s['bulk_btn']}</button></p></form>
<p style='font-size:18px;'>{s['bulk_cap']}</p>"""
        return _shell(f"""{bar}
<div class='box blue'><span class='lbl'>&#9632; {s['bulk_title']}</span><div class='big'>{s['bulk_intro']}</div></div>
{body}
<p class='big'><a href='/'>{s['nav_clear']}</a></p>""", s)
    counts = counts or {}
    all_actions = ""
    for r in results:
        for a in r.get("actions", []):
            all_actions += f"<div class='big'>&#9654; {esc(a)} <span style='font-size:18px;'>— {s['bulk_from']} {esc(r.get('sender',''))}</span></div>"
    if not all_actions:
        all_actions = f"<div class='big'>{s['no_actions'] if 'no_actions' in s else ''}</div>"
    cards = ""
    for r in results:
        acts = "".join(f"<div class='big'>{i}. {esc(a)}</div>" for i, a in enumerate(r.get("actions", []), 1))
        dates = _dates_html(r, s)
        cards += f"""<div class='box blue'><span class='lbl'>&#9632; {esc(r.get('sender',''))} — {esc(r.get('subject',''))}</span><div class='big'>{esc(r.get('what',''))}</div></div>
<div class='box amber'><span class='lbl'>&#9654; {s['do']}</span>{acts}</div>
<div class='box plain'><span class='lbl'>&#9670; {s['dates']}</span>{dates}</div>
<p class='big'><a href='/inbox/clear?id={esc(r.get('mid',''))}&lang={esc(lang)}'>{s['bulk_open']}</a></p>"""
    skips = ""
    if counts.get("own"):
        skips += f"<div style='font-size:18px;'>{counts['own']} {s['bulk_skip_own']}</div>"
    if counts.get("dupe"):
        skips += f"<div style='font-size:18px;'>{counts['dupe']} {s['bulk_skip_dupe']}</div>"
    if counts.get("failed"):
        skips += f"<div style='font-size:18px;'>{counts['failed']} {s['bulk_failed']}</div>"
    more = ""
    if counts.get("remaining"):
        more = f"""<form method='post' action='/bulk/clear'>
<input type='hidden' name='lang' value='{esc(lang)}'>
<p><button type='submit' class='bigbtn'>&#9993; {s['bulk_btn']}</button></p></form>"""
    return _shell(f"""{bar}
<p class='big'><b>{len(results)}</b> {s['bulk_cleared']}</p>
<div class='box amber'><span class='lbl'>&#9654; {s['bulk_all']}</span>{all_actions}</div>
{skips}
{cards}
{more}
<p class='big'><a href='/followups'>{s['nav_followups']}</a> &middot; <a href='/'>{s['nav_clear']}</a></p>""", s)

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
{_raw_card(s)}""", s)

def _story_note_html(s):
    parts = s['inbox_raw_note'].split("[[MAILPIT]]")
    note = esc(parts[0]) + (esc(parts[1]) if len(parts) > 1 else "")
    return note.replace(" .", ".").replace("\n", "<br><br>")

def _raw_card(s):
    btn = f"<a class='btn rawbtn' href='/mailpit/' target='_blank' rel='noopener'>{s['story_btn']}</a>"
    lead = esc(s['inbox_raw_note'].split("[[MAILPIT]]")[0].split("\n")[0].strip())
    return f"""<div class='card story-strip'>
<div class='big'>{lead}</div>
<div class='big' style='margin-top:8px;'>{btn}</div></div>
<dialog id='rawbox' aria-label="{esc(s['story_btn'])}">
<div>{_story_note_html(s)}</div>
<div class='cardtitle' style='margin-top:18px;'>{s['raw_dialog_title']}</div>
<div id='freshmsg'>{s['fresh_step1']}</div><div class='freshtrack'><div id='freshfill'></div></div>
<div><a class='btn' id='seeemail' href='#rawmail' style='display:none'>{s['see_email']} &#8595;</a> <button type='button' class='btn' id='rawclose'>{s['raw_close_plain']}</button></div>
<iframe id='rawmail' src='/mailpit/' title='Mailpit' loading='lazy'></iframe>
</dialog>
<script>
window.__fresh1={json.dumps(s['fresh_step1'])};window.__fresh2={json.dumps(s['fresh_step2'])};
document.addEventListener('click',function(e){{var a=e.target.closest?e.target.closest('a.rawbtn'):null;if(a){{e.preventDefault();var d=document.getElementById('rawbox');if(d&&d.showModal){{d.showModal();fresh();}}else{{window.open(a.href,'_blank');}}}}
function land(){{fetch('/mailpit/api/v1/messages').then(function(r){{return r.json();}}).then(function(j){{var ms=j.messages||[];var m=null;for(var i=0;i<ms.length;i++){{if(ms[i].Subject==='Board meeting moved'){{m=ms[i];break;}}}}if(!m&&ms.length){{m=ms[0];}}if(m){{var f=document.querySelector('#rawbox iframe');if(f){{f.src='/mailpit/view/'+m.ID;}}}}}}).catch(function(){{}});}}var se3=e.target.closest?e.target.closest('#seeemail'):null;if(se3){{e.preventDefault();var f3=document.getElementById('rawmail');if(f3){{f3.scrollIntoView({{block:'nearest'}});}}}}var c=e.target.closest?e.target.closest('#rawclose'):null;if(c){{var d2=document.getElementById('rawbox');if(d2){{d2.close();}}}}}});
</script>"""

def render_form(extra="", lang="en", prefill=None):
    s = S(lang)
    checked = {code: ("checked" if code == lang else "") for code in STRINGS}
    pf = prefill or {}
    pf_sender = esc(pf.get("sender", ""))
    pf_subject = esc(pf.get("subject", ""))
    pf_text = esc(pf.get("text", ""))
    loaded = f"<p class='big' id='sampletop'><b>&#10003; {s['sample_loaded']}</b></p>" if pf else ""
    scroll = ("<script>window.addEventListener('load',function(){var el=document.getElementById('sampletop');"
              "if(el){setTimeout(function(){el.scrollIntoView({behavior:'smooth',block:'start'});},200);}});</script>") if pf else ""
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
<div class='hero'>{s['hero1']}, <span class='accent'>{s['hero2']}</span></div>
<div class='big'>{s['hero_sub']}</div>
<div class='layout'><div>
{_raw_card(s)}
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
</div><div>
<div class='card'><div class='cardtitle'>&#9632; {s['path_title']}</div>
<div>{s['path_sub']}</div>
<div class='step'><div class='num'>01</div><div><b>{s['step1']}</b></div></div>
<div class='step'><div class='num'>02</div><div><b>{s['step2']}</b></div></div>
<div class='step'><div class='num'>03</div><div><b>{s['step3']}</b></div></div></div>
<div class='card trust'><div>&#10003; {s['trust1']}</div><div>&#10003; {s['trust2']}</div><div>&#10003; {s['trust3']}</div></div>
</div></div>
<p class='big'><a href='/followups'>{s['see_followups']}</a></p>{scroll}""", s)

def _dates_html(p, s):
    """The DATES + NUMBERS lines: labeled when the rules found cue words
    ('Reply by: Friday, November 27'), plain when they did not."""
    lab = p.get("dates_labeled") or []
    if lab:
        return "".join(
            f"<div style='font-size:26px'><b>{esc((it.get('label') + ': ') if it.get('label') else '')}{esc(it.get('value', ''))}</b></div>"
            for it in lab)
    return "".join(f"<div style='font-size:26px'><b>{esc(d)}</b></div>" for d in p.get("dates_numbers", [])) or f"<div class='big'>{s['no_dates']}</div>"

def render_page(p):
    s = S(p.get("lang", "en"))
    actions = "".join(f"<div class='big'>{i}. {esc(a)}</div>" for i, a in enumerate(p.get("actions", []), 1))
    facts = "".join(f"<tr><td style='width:32%'><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in (p.get("facts") or {}).items())
    dates = _dates_html(p, s)
    steps = " &rarr; ".join(esc(x) for x in p.get("steps", []))
    risk_text = esc(p["risk"]) if p.get("risk") else s["risk_none"]
    risk = f"<div class='box plain'><span class='lbl'>&#9650; {s['risk']}</span><div class='big'>{risk_text}</div></div>"
    if p.get("source") == "model":
        short_model = esc(str(p.get("model_name", "")).split("/")[-1])
        pill = f"<span class='pill pill-ai'>&#9679; {s['ai_live']}" + (f" &middot; {short_model}" if short_model else "") + "</span>"
    else:
        pill = f"<span class='pill'>&#9670; {s['ai_rules']}</span>"
    reply_card = ""
    if p.get("_text") is not None:
        can_send = bool(p.get("_addr"))
        btn = s['reply_btn'] if can_send else s['reply_btn_draft']
        reply_card = f"""<div class='card replycard'><div class='cardtitle'>&#9993; {s['reply_title']}</div>
<div class='big'><b>{s['reply_next']}</b></div>
<form method='post' action='/reply'>
<input type='hidden' name='mid' value='{esc(p.get("_mid", ""))}'>
<input type='hidden' name='sender' value='{esc(p.get("sender", ""))}'>
<input type='hidden' name='subject' value='{esc(p.get("_subject", ""))}'>
<input type='hidden' name='lang' value='{esc(p.get("lang", "en"))}'>
<textarea name='text' style='display:none'>{esc(p.get("_text", ""))}</textarea>
<p><button type='submit' class='bigbtn'>&#9993; {btn}</button></p></form>
</div>"""
    return _shell(f"""{_bar(pill, s)}
<p class='big'><b>{s['demo_page']}</b></p>
<div class='layout even'><div>
<div class='box blue'><span class='lbl'>&#9632; {s['what']}</span><div class='big'>{esc(p.get('what',''))}</div></div>
<div class='box amber'><span class='lbl'>&#9654; {s['do']}</span>{actions}</div>
<div class='box purple'><span class='lbl'>&#9679; {s['facts']}</span><table>{facts}</table></div>
<div class='box plain'><span class='lbl'>&#9670; {s['dates']}</span>{dates}</div>
<p class='big' style='margin-top:16px;'>{s['steps']}: {steps}</p>
<p style='font-size:18px;'>{s['source']}: {esc(p.get('sender',''))} &middot; {esc(p.get('source_date',''))}</p>
</div><div>
{risk}
{reply_card}
</div></div>
<p class='big'><a href='/'>{s['another']}</a> &middot; <a href='/followups'>{s['followups']}</a></p>""", s)

def render_reply_draft(to, subject, body_text, lang="en", mid="", addr="", source="rules", model_name="", found=False):
    s = S(lang)
    if source == "model":
        short_model = esc(str(model_name or "").split("/")[-1])
        pill = f"<span class='pill pill-ai'>&#9679; {s['ai_live']}" + (f" &middot; {short_model}" if short_model else "") + "</span>"
    else:
        pill = f"<span class='pill'>&#9670; {s['ai_rules']}</span>"
    box = "width:100%;font-size:21px;line-height:1.7;font-family:Arial,Verdana,sans-serif;padding:12px;margin-top:12px;box-sizing:border-box;"
    send_form = ""
    if addr:
        found_box = f"<div class='box plain' style='border-color:#0E7A5F;background:#EFFAF4'><div class='big'><b>&#10003; {s['found_addr']} {esc(addr)}</b></div></div>" if found else ""
        send_form = found_box + f"""<form method='post' action='/reply/send'>
<input type='hidden' name='mid' value='{esc(mid)}'>
<input type='hidden' name='to' value='{esc(addr)}'>
<input type='hidden' name='subject' value='{esc(subject)}'>
<input type='hidden' name='lang' value='{esc(lang)}'>
<div>{s['edit_hint']}</div>
<textarea name='body' rows='9' style='{box}'>{esc(body_text)}</textarea>
<p><button type='submit' class='bigbtn sendbtn'>{s['send_btn']}</button></p></form>
<p class='big'><a href='/'>{s['dont_send']}</a></p>"""
    else:
        send_form = f"""<div class='box amber'><span class='lbl'>&#9650; {s['no_send_here']}</span><div class='big'>{s['no_send_why']}</div></div>
<div>{s['edit_hint']}</div>
<textarea rows='9' style='{box}'>{esc(body_text)}</textarea>
<p class='big'>{s['reply_draft_only']}</p>"""
    return _shell(f"""{_bar(pill, s)}
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
{("<p class='big'><b>" + s['sent_see'] + "</b></p><p><a class='btn bigbtn' href='/mailpit/' target='_blank' rel='noopener'>" + s['sent_both'] + "</a></p>") if sent else ""}
<p class='big'><a href='/followups'>{s['nav_followups']}</a> &middot; <a href='/'>{s['nav_clear']}</a></p>""", s)


def render_connected(proof, lang="en", checked=""):
    s = S(lang)
    gh = proof.get("github") or {}
    tg = proof.get("together") or {}

    def pill(ok):
        return (f"<span class='pill pill-ai'>&#9679; {s['proof_live']}</span>" if ok
                else f"<span class='pill'>&#9670; {s['proof_down']}</span>")

    def stat(n, label):
        return f"<div class='stat'><div class='n'>{esc(str(n))}</div><div class='l'>{label}</div></div>"

    if gh.get("ok"):
        gh_html = f"""<div class='card'><div class='cardtitle'>&#9632; GitHub {pill(True)}</div>
<div class='stats'>{stat(gh.get('repos', '-'), s['t_repos'])}{stat(gh.get('rate_left', '-'), s['t_rate'])}{stat(gh.get('commit_sha', '-'), s['t_commit'])}</div>
<div class='prow'><b>{s['r_account']}:</b> {esc(gh.get('login', ''))} &middot; clearday</div>
<div class='prow'><b>{esc(gh.get('commit_msg', ''))}</b> ({esc(gh.get('commit_date', ''))})</div>
<div class='prow'><b>{s['r_updated']}:</b> {esc(gh.get('repo_updated', ''))}</div>
<div class='prow'><b>{s['proof_source']}:</b> Sprites GitHub connector &middot; api.sprites.dev &middot; GET /user, /repos, /rate_limit &middot; {s['proof_ms']} {gh.get('ms', '-')} ms</div></div>"""
    else:
        gh_html = f"""<div class='card'><div class='cardtitle'>&#9632; GitHub {pill(False)}</div>
<div class='prow'>{esc(gh.get('error', ''))}</div></div>"""
    if tg.get("ok"):
        onlist = "&#10003; " + s['r_onlist'] if tg.get("on_list") else s['proof_down']
        tg_html = f"""<div class='card'><div class='cardtitle'>&#9654; Together AI {pill(True)}</div>
<div class='stats'>{stat(tg.get('models_count', '-'), s['t_models'])}{stat(tg.get('tokens_total', '-'), s['t_tokens'])}{stat(str(tg.get('call_ms', '-')) + ' ms', s['t_speed'])}</div>
<div class='prow'><b>{s['r_model']}:</b> {esc(tg.get('model', ''))} &middot; {onlist}</div>
<div class='prow'><b>{s['proof_ask']}:</b> &ldquo;Answer in one short sentence: what is 2 + 2?&rdquo;</div>
<div class='prow'><b>{s['proof_said']}:</b> &ldquo;{esc(tg.get('answer', ''))}&rdquo;</div>
<div class='prow'><b>{s['r_callid']}:</b> {esc(tg.get('call_id', ''))}</div>
<div class='prow'><b>{s['proof_source']}:</b> Sprites Custom API connector &middot; api.together.xyz &middot; GET /models + POST /chat/completions</div></div>"""
    else:
        tg_html = f"""<div class='card'><div class='cardtitle'>&#9654; Together AI {pill(False)}</div>
<div class='prow'>{esc(tg.get('error', ''))}</div></div>"""
    return _shell(f"""{_bar(f"<span class='pill'>&#9679; {s['brand_pill']}</span>", s)}
<div class='hero' style='font-size:34px'>&#9670; {s['proof_title']}</div>
<div class='big'>{s['proof_sub']}</div>
<div class='big'><b>{s['proof_checked']}:</b> {esc(checked)}</div>
<div class='cols2'>
{gh_html}
{tg_html}
</div>
<div class='card'><div class='big'><b>{s['proof_note']}</b></div></div>""", s)
