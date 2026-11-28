"""ClearDay core: long text -> 1 dyslexia-friendly clear page.

Design rules (International Dyslexia Association (IDA, USA) + US WCAG 2.2 AA (ADA / Section 508) + Rello et al.):
- Sans serif, big type, wide letter/line spacing, left aligned
- Cream / warm background, dark (not pure black) text, no pure white glare
- Color + label + shape for every section (never color alone)
- Avoid red/green as a meaning pair
- Bold only, no italics / underline, short phrases, max 3 actions
"""
import re, json, os, urllib.request, threading, unicodedata
from datetime import datetime

DATE_RE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{1,2}-\d{1,2}-\d{2,4}\b|\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b|\b(?:[01]?\d|2[0-3]):[0-5]\d\b", re.I)
# Numbers finder: money, comma-grouped, decimals, plain integers (2+ digits).
# Only ever applied OUTSIDE date/time spans, so a day or year inside a date is never double-counted.
NUMBER_RE = re.compile(r"\$\s?\d[\d,]*\.?\d*|(?<![\d/-])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d/-])|(?<![\d/-])\d+\.\d+(?![\d/-])|(?<![\d/-])\d{2,}(?![\d/-])")
# Spanish dates: "martes 24 de noviembre", "24 de noviembre de 2026", "5:15 p. m."
DATE_RE_ES = re.compile(r"\b(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+de\s+\d{4})?\b|\b\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+de\s+\d{4})?\b|\b\d{1,2}:\d{2}\s*(?:a\.\s*m\.|p\.\s*m\.|AM|PM)", re.I)
# Vietnamese dates: "ngày 24 tháng 11", "ngày 24 tháng 11 năm 2026", "17 giờ 15", "5:15"
DATE_RE_VI = re.compile(r"\bng[aà]y\s+\d{1,2}\s+th[aá]ng\s+\d{1,2}(?:\s+n[aă]m\s+\d{4})?\b|\b\d{1,2}\s*gi[oờ]\s*\d{2}\b|\b\d{1,2}:\d{2}\b", re.I)
DATE_RES = {"en": DATE_RE, "es": DATE_RE_ES, "vi": DATE_RE_VI}
ACTION_HINTS = {
    "en": ("please", "reply", "confirm", "bring", "send", "sign", "add", "attend", "rsvp", "submit", "call"),
    "es": ("por favor", "responda", "responder", "confirme", "confirmar", "traiga", "traer", "envíe", "enviar", "firme", "asista", "asistir", "llame", "llamar"),
    "vi": ("vui lòng", "trả lời", "xác nhận", "mang theo", "gửi", "ký", "tham dự", "gọi"),
}
CORE = {
    "en": {"who": "Who", "what": "What", "unknown_sender": "Unknown sender", "see_original": "See original",
           "fallback_action": "Read the key facts below",
           "no_ask": "This email asks nothing of you",
           "steps": ["Read this page", "Do the actions in the amber box", "Check the date in the white box"]},
    "es": {"who": "Quién", "what": "Qué", "unknown_sender": "Remitente desconocido", "see_original": "Ver el original",
           "fallback_action": "Lee los datos clave de abajo",
           "no_ask": "Este correo no te pide nada",
           "steps": ["Lee esta página", "Haz lo que dice el cuadro de color ámbar", "Revisa la fecha en el cuadro blanco"]},
    "vi": {"who": "Ai", "what": "Việc gì", "unknown_sender": "Không rõ người gửi", "see_original": "Xem bản gốc",
           "fallback_action": "Đọc thông tin chính bên dưới",
           "no_ask": "Email này không yêu cầu bạn làm gì",
           "steps": ["Đọc trang này", "Làm các việc trong khung màu hổ phách", "Kiểm tra ngày trong khung trắng"]},
}

def _sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 3]

_WEEKDAYS_EN = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTHS_EN = "January|February|March|April|May|June|July|August|September|October|November|December"
_TIME_ONLY = re.compile(r"^(?:[01]?\d|2[0-3]):[0-5]\d(?:\s?[APap][Mm])?$")

def _disp_date(v, lang):
    if lang == "en":
        v = re.sub(rf"^({_WEEKDAYS_EN}) ({_MONTHS_EN}) ", r"\1, \2 ", v)
    return v

def _label_for(ctx, meeting):
    """Label one date from the words just before it in the same sentence.
    The label is built ONLY from the email's own cue words - never guessed."""
    if re.search(r"\b(moved|rescheduled|postponed)\b[^.]{0,120}?\bto\b", ctx):
        return "New Meeting Date" if meeting else "New date"
    if "moved from" in ctx or "rescheduled from" in ctx or "originally" in ctx or "was scheduled" in ctx:
        return "Original Meeting Date" if meeting else "Original date"
    if re.search(r"\b(reply|confirm|respond|rsvp)\b", ctx) and re.search(r"\b(before|by)\b", ctx):
        return "Reply by"
    if re.search(r"\bpay\b", ctx) and re.search(r"\b(before|by)\b", ctx):
        return "Pay by"
    if re.search(r"\b(submit|send)\b", ctx) and re.search(r"\b(before|by)\b", ctx):
        return "Send by"
    return ""

def _label_dates(text, subject="", lang="en"):
    """The DATES + NUMBERS list with a plain label on each date, in text order.
    Labels come from the email's own words (Jose Luis's rule, Nov 26, 2026:
    'Original Meeting Date: Monday, November 23' / 'New Meeting Date: Tuesday,
    November 24 at 5:15 PM' / 'Reply by: Friday, November 27'). A time that
    belongs to a date joins its date. No cue words -> no label, never invented.
    English labels first; other languages keep the plain values for now."""
    items = []
    spans = []
    for rx in (DATE_RES[lang], DATE_RE):
        for m in rx.finditer(text):
            spans.append(m.span())
            items.append((m.start(), m.end(), m.group(0), True))
    for m in NUMBER_RE.finditer(text):
        if any(m.start() < e and s < m.end() for s, e in spans):
            continue
        items.append((m.start(), m.end(), m.group(0), False))
    items.sort()
    vals = [v for _, _, v, _ in items]
    items = [it for it in items if not any(it[2] != o and o.startswith(it[2]) for o in vals)]
    meeting = "meeting" in f"{subject} {text[:300]}".lower()
    out = []
    seen = set()
    prev_end = 0
    for start, end, value, is_date in items:
        if value in seen:
            prev_end = max(prev_end, end)
            continue
        if is_date and _TIME_ONLY.match(value) and out and out[-1]["_date"] and start - prev_end <= 10:
            out[-1]["value"] += " at " + value
            seen.add(value)
            prev_end = end
            continue
        label = ""
        if is_date and lang == "en":
            seg = text[prev_end:start]
            cut = max(seg.rfind(". "), seg.rfind("." + chr(10)), seg.rfind(chr(10)), seg.rfind("; "))
            if cut >= 0:
                seg = seg[cut + 1:]
            label = _label_for(seg.lower(), meeting)
        out.append({"label": label, "value": _disp_date(value, lang), "_date": is_date})
        seen.add(value)
        prev_end = end
        if len(out) >= 6:
            break
    for it in out:
        del it["_date"]
    return out

def heuristic_transform(text, sender="", subject="", lang="en"):
    if lang not in CORE:
        lang = "en"
    core = CORE[lang]
    hints = ACTION_HINTS[lang]
    sents = _sentences(text)
    dates = []
    spans = []
    for rx in (DATE_RES[lang], DATE_RE):
        for m in rx.finditer(text):
            spans.append(m.span())
            if m.group(0) not in dates:
                dates.append(m.group(0))
    dates = [d for d in dates if not any(d != o and o.startswith(d) for o in dates)]
    nums = []
    for m in NUMBER_RE.finditer(text):
        if any(m.start() < e and s < m.end() for s, e in spans):
            continue
        if m.group(0) not in dates and m.group(0) not in nums:
            nums.append(m.group(0))
    dates = (dates + nums)[:6]
    actions = []
    for s in sents:
        low = s.lower()
        if "from:" in low or "subject:" in low or "asunto:" in low or "chủ đề:" in low:
            continue
        if any(h in low for h in hints) and len(s) < 180:
            clean = re.sub(r"^(first|second|third|finally|primero|segundo|tercero),?\s+", "", s.rstrip(".!?"), flags=re.I)
            clean = re.sub(r"^please\s+", "Please ", clean)
            actions.append(" ".join(clean.split()[:9]))
        if len(actions) >= 3:
            break
    if not actions and sents:
        actions = [core["fallback_action"]]
    title = subject.strip() or (sents[0][:60] if sents else "New message")
    return {
        "what": title,
        "sender": sender or core["unknown_sender"],
        "actions": actions[:3],
        "facts": {core["who"]: sender or core["see_original"], core["what"]: title},
        "dates_numbers": dates,
        "dates_labeled": _label_dates(text, subject, lang),
        "steps": core["steps"],
        "risk": "",
        "source_date": datetime.now().strftime("%a %b %d"),
        "lang": lang,
    }

LANG_NAMES = {"en": "English", "es": "Spanish (Español)", "vi": "Vietnamese (Tiếng Việt)"}

def _clean_str(v, max_words):
    if not isinstance(v, str):
        return ""
    return " ".join(v.split()[:max_words]).strip()

def _clean_str_list(v, max_items, max_words):
    if not isinstance(v, list):
        return []
    out = []
    for item in v:
        s = _clean_str(item, max_words)
        if s:
            out.append(s)
        if len(out) >= max_items:
            break
    return out

def _clean_facts(v):
    if not isinstance(v, dict):
        return {}
    out = {}
    for k, val in v.items():
        key = _clean_str(str(k), 3)
        value = _clean_str(val, 10) if isinstance(val, str) else ""
        if key and value:
            out[key] = value
        if len(out) >= 4:
            break
    return out

def _norm_token(t):
    t = t.lower().strip().strip(".,;:")
    t = t.replace(",", "").replace("$", "").strip()
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    return re.sub(r"\s+", " ", t)

def _allowed_tokens(text, lang="en"):
    """The exact date/time/number tokens a model may use: the ones the rules
    themselves find in the source (dates first, numbers outside date spans)."""
    if lang not in DATE_RES:
        lang = "en"
    allowed = set()
    spans = []
    for rx in (DATE_RES[lang], DATE_RE):
        for m in rx.finditer(text or ""):
            spans.append(m.span())
            allowed.add(_norm_token(m.group(0)))
    for m in NUMBER_RE.finditer(text or ""):
        if any(m.start() < e and s < m.end() for s, e in spans):
            continue
        allowed.add(_norm_token(m.group(0)))
    return allowed

def _strip_ungrounded(s, allowed, lang="en"):
    """Remove any date/time/number token in model text that is NOT in the source.
    This is the no-fake-data rule enforced in code, not just asked in a prompt."""
    if not s:
        return s
    if lang not in DATE_RES:
        lang = "en"
    def repl(m):
        return m.group(0) if _norm_token(m.group(0)) in allowed else ""
    for rx in (DATE_RES[lang], DATE_RE):
        s = rx.sub(repl, s)
    # The number pass must not eat the digits inside a date that survived:
    # protect the spans of every date token still standing, then judge
    # only the numbers outside them. (Found by scenario U52/U57: without
    # this, "November 24" lost its 24 and Spanish dates lost their day.)
    spans = []
    for rx in (DATE_RES[lang], DATE_RE):
        spans += [m.span() for m in rx.finditer(s)]
    def nrepl(m):
        if any(m.start() < e and st < m.end() for st, e in spans):
            return m.group(0)
        return m.group(0) if _norm_token(m.group(0)) in allowed else ""
    s = NUMBER_RE.sub(nrepl, s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip(" ,;")


def _ground_facts(facts, allowed, source, lang="en"):
    """Facts get the same no-invention treatment as every other field.
    Keys are stripped of ungrounded dates/numbers too (a model key like
    'Due January 40' used to sail into the table untouched), and a row is
    dropped when neither its key nor its value shares one real word with
    the source - a row with no anchor in the email is an invented row
    ('importance: high', 'deadline: matters'). Dropping beats inventing."""
    src_words = {w for w in re.split(r"[^\w]+", (source or "").lower()) if len(w) >= 3}
    out = {}
    for k, v in facts.items():
        key = _strip_ungrounded(k, allowed, lang)
        val = _strip_ungrounded(v, allowed, lang)
        if not key or not val:
            continue
        words = {w for w in re.split(r"[^\w]+", f"{key} {val}".lower()) if len(w) >= 3}
        if words and not (words & src_words):
            continue
        out[key] = val
    return out

# The duties guard (Skeptic lens, Nov 26): if the email itself never asks
# for anything, the YOU MUST DO box must not be invented - not by the
# model, not by a fallback. These phrases say "no ask" out loud and win
# over the ask-word scan; the scan itself is generous on purpose (it errs
# toward seeing an ask, so the guard stays silent unless it is sure).
NO_ASK_PHRASES = {
    "en": ("no reply is needed", "no reply needed", "no action needed", "no action is needed",
           "no need to reply", "no response needed", "nothing is needed", "nothing needed from you",
           "just sharing", "just wanted to share", "for your information",
           "do not reply", "don't reply", "no reply please", "no reply expected", "for information only"),
    "es": ("no es necesario responder", "no hace falta responder", "solo comparto",
           "solo para tu información", "solo para su información",
           "no es necesario que responda", "no es necesario que respondas",
           "no hace falta que responda", "no hace falta que respondas"),
    "vi": ("không cần trả lời", "chỉ chia sẻ", "chỉ để bạn biết"),
}
ASK_EXTRA = {
    "en": ("register", "complete", "fill out", "fill in", "return", "pay", "review", "check",
           "let me know", "let us know", "forget", "remember to", "be sure", "make sure",
           "need you", "asking", "request", "required", "must", "deadline", "due by",
           "remit", "requested", "be signed", "be returned", "be submitted", "be completed",
           "be paid", "be sent", "would you mind"),
    "es": ("registre", "registrar", "complete", "completar", "rellene", "rellenar", "devuelva",
           "devolver", "pague", "pagar", "revise", "revisar", "avise", "avíseme", "olvide",
           "recuerde", "asegúrese", "necesito que", "solicito", "requerido", "debe", "fecha límite",
           "confirma", "responde", "envía", "envia", "envíe", "firma", "firme", "revisa", "completa",
           "firmar", "remitir", "sírvase", "tenga a bien",
           "enviar", "confirmar", "responder", "entregar", "entregue",
           "firmes", "pagues", "envíes", "envies", "devuelvas", "traigas", "respondas",
           "completes", "revises", "rellenes", "registres", "decir", "diga", "digan", "dime",
           "se ruega", "paga", "devuelve", "trae", "firmad", "enviad", "enviadlo"),
    "vi": ("đăng ký", "hoàn thành", "điền", "trả lại", "thanh toán", "xem lại", "cho tôi biết",
           "đừng quên", "nhớ", "hãy chắc chắn", "yêu cầu", "bắt buộc", "phải", "hạn chót",
           "nộp", "hoàn tất", "chuyển khoản", "đề nghị", "phản hồi"),
}

# Politeness words and pressure nouns are NOT asks on their own: "please"
# decorates thank-you notes too, and a deadline can be crucial without
# asking anyone for anything (skeptic probes P6/P9, Nov 27).
_NOT_ASK_WORDS = {"please", "por favor", "vui lòng",
                  "must", "deadline", "required", "due by",
                  "debe", "requerido", "fecha límite",
                  "bắt buộc", "phải", "hạn chót", "check", "review"}
_ASK_WORDS = tuple(w for lg in ("en", "es", "vi")
                   for w in ACTION_HINTS[lg] + ASK_EXTRA[lg]
                   if w not in _NOT_ASK_WORDS)
_ASK_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in _ASK_WORDS) + r")\b")

def _deacc(s):
    """Strip accent marks (á -> a) for the formal-Spanish scan below."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(ch))

# Formal written Spanish puts a written accent on a glued pronoun form -
# "envíelos" (send them), "devuélvalo" (return it), "fírmelas" (sign them) -
# so neither the bare verb nor its unaccented tail ever matches. Scan a
# de-accented copy of the text with de-accented Spanish ask-words and the
# full pronoun tail set (round-6 skeptic probes, Nov 28).
_ES_BASE = [w for w in ACTION_HINTS["es"] + ASK_EXTRA["es"] if w not in _NOT_ASK_WORDS]
def _es_gerund(w):
    """enviar -> enviando, devolver -> devolviendo, remitir -> remitiendo."""
    if w.endswith("ar"):
        return w[:-2] + "ando"
    if w.endswith(("er", "ir")):
        return w[:-2] + "iendo"
    return None

# Stems that can carry glued pronouns: the ask verbs themselves, plus
# their gerunds ("enviándolos" - sending them). Formal Spanish stacks
# TWO pronouns on one verb - indirect (me/te/se/nos) + direct
# (lo/la/los/las): "envíemelos" (send them to me), "fírmeselo" (sign it
# for him), "enviármelos" (to send them to me) - so the generator builds
# the stacks too (round-7 skeptic probes, Nov 28).
_ES_STEMS = [w for w in _ES_BASE if " " not in w and (w[-1] in "aeiou" or w.endswith("r"))]
_ES_STEMS += [g for w in _ES_BASE if " " not in w and _es_gerund(w) for g in (_es_gerund(w),)]
_ES_TAILS = ("lo", "la", "los", "las", "le", "les", "me", "se")
_ES_STACKS = tuple(i + d for i in ("me", "te", "se", "nos") for d in ("lo", "la", "los", "las"))
_ES_DEACC = sorted({_deacc(w) for w in _ES_BASE} |
                   {_deacc(w) + t for w in _ES_STEMS for t in _ES_TAILS + _ES_STACKS})
_ASK_RE_ES = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in _ES_DEACC) + r")\b")
_NO_ASK_ALL = tuple(p for lg in ("en", "es", "vi") for p in NO_ASK_PHRASES[lg])

# A no-need phrase governs the verb right after it: in "No hace falta
# firmarlo ni enviarlo" (no need to sign it or send it) the glued verbs
# are exactly what the sentence says is NOT needed, so the phrase and
# its governed verb(s) lift out together - otherwise the scan hears two
# duties in a sentence that cancels them (round-7 skeptic, Nov 28).
_PRON = "lo|la|los|las|le|les|me|te|se|nos"
_GOVERNED = "(?:(" + _PRON + r")\s+)?\w+(?:" + _PRON + ")?"
_NO_NEED_RE = re.compile(r"\b(no hace falta|no es necesario|no necesitas|no es preciso|no tienes)"
                         r"(\s+ni)?(\s+que)?(?:[\s,]*(?:por ahora|por el momento))?[\s,]*"
                         + _GOVERNED + r"(\s+(?:\w+\s+){0,2}?(?:ni|o)\s+(?:que\s+)?" + _GOVERNED + ")*")
_NO_NEED_EN_RE = re.compile(r"\b(no need to|there is no need to|don't need to|do not need to|don't have to|do not have to|needn't)\s+\w+(\s+(or|and)\s+\w+)*")
_NEG_ASK_ES_RE = re.compile(r"\b(favor de no|se ruega no|se solicita no|sin necesidad de|por favor,?\s+no|(?:te |le |les )?pedimos que no|se pide que no|(?:te |le |les )?ruego que no|rogamos no|rogamos que no|absténgase de|(?:se ruega |favor de )?abstenerse de)\s+\w+(?:" + _PRON + r")?(\s+ni\s+\w+(?:" + _PRON + ")?)*")
_NO_NEED_VI_RE = re.compile(r"\bkhông cần(\s+phải)?\s+\w+(\s+(?:\w+\s+){0,2}?hay\s+\w+)*")
_DO_NOT_EN_RE = re.compile(r"\b(do not|don't|that you not)\s+\w+(\s+(or|and)\s+\w+)*")
_NEVER_EN_RE = re.compile(r"\bnever\s+\w+(\s+(or|and)\s+\w+)*")
_NEG_ASK_VI_RE = re.compile(r"\b(đừng|chớ|không nên)\s+\w+")

def _has_ask(text, lang="en"):
    """True when the source text itself asks the reader for something.
    Round-3 rebuild (skeptic + technical lenses, Nov 27): first lift the
    'no reply needed' phrases OUT of the text - the ask-words inside them
    ('reply' in 'no need to reply') must not trip the scan - then look for
    a real ask-word in ANY of the three languages, on word boundaries, so
    'add' inside 'addition' and 'sign' inside 'signed' stay silent. A real
    ask anywhere outranks a no-ask phrase anywhere; a question mark alone
    is conversation, not a duty."""
    low = (text or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    for p in _NO_ASK_ALL:
        low = low.replace(p, " ")
    low = _NO_NEED_EN_RE.sub(" ", _NO_NEED_RE.sub(" ", low))
    low = _NO_NEED_VI_RE.sub(" ", _NEG_ASK_ES_RE.sub(" ", low))
    low = _NEG_ASK_VI_RE.sub(" ", _NEVER_EN_RE.sub(" ", _DO_NOT_EN_RE.sub(" ", low)))
    return bool(_ASK_RE.search(low) or _ASK_RE_ES.search(_deacc(low)))


_MODEL_SEM = threading.Semaphore(3)  # max model calls in flight, demo-wide - held inside _call_model so EVERY call site counts (technical lens, Nov 28)

_MODEL_DEADLINE = 45  # seconds TOTAL per model call, never per socket read

def _call_model(req):
    """One model HTTP call with a hard total deadline (45 seconds).

    A slow-dripping provider defeats urlopen's per-socket timeout - every
    drip resets it, and a call can hang for minutes. So the call runs on a
    daemon thread and the caller stops waiting at the deadline; the rules
    answer instead. Cap approved by Jose Luis on Nov 26, 2026."""
    box = {}
    def run():
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                box["data"] = r.read()
        except Exception as e:  # handed to the caller below
            box["error"] = e
    with _MODEL_SEM:
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(_MODEL_DEADLINE)
        if t.is_alive():
            raise TimeoutError(f"model call passed the {_MODEL_DEADLINE}s cap")
    if "error" in box:
        raise box["error"]
    return box["data"]

def _labeled_str(text, subject="", lang="en"):
    lab = _label_dates(text, subject, lang)
    if not lab:
        return "NONE"
    return "; ".join(f"{it['label']}: {it['value']}" if it["label"] else it["value"] for it in lab)

_WEEKDAY_ONLY = re.compile(r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[.,]?$", re.I)

def _drop_date_facts(facts, labeled):
    """KEY FACTS are about the message, never about dates (Jose Luis's order,
    Nov 26 late - the model had turned the date labels into fact rows with
    weekday-only values: 'Original Meeting Date: Monday'). Drop any row whose
    key is a date label, or whose value is a bare weekday or a lone date."""
    labels = {it["label"].lower() for it in (labeled or []) if it.get("label")}
    out = {}
    for k, v in (facts or {}).items():
        if k.strip().lower() in labels:
            continue
        if _WEEKDAY_ONLY.match(v.strip()):
            continue
        if DATE_RE.fullmatch(v.strip()) or any(rx.fullmatch(v.strip()) for rx in (DATE_RES["en"],)):
            continue
        out[k] = v
    return out

def llm_transform(text, sender="", subject="", lang="en"):
    """Optional model pass, through a Sprites Connector gateway (Together AI).
    Env: CLEARDAY_MODEL_URL (connector gateway base, OpenAI-compatible),
         CLEARDAY_MODEL (model name). No key inside the Sprite - the gateway
         attaches the stored credential.
    The model drafts WORDS ONLY (what / actions / facts / steps / risk).
    It never supplies dates or numbers - the rules own those, always.
    Returns a cleaned partial dict, or None on any failure. Never blocks.
    """
    base = os.environ.get("CLEARDAY_MODEL_URL")
    if not base:
        return None
    if lang not in LANG_NAMES:
        lang = "en"
    prompt = (
        f"Write every value in {LANG_NAMES[lang]}. Be brief - answer directly, do not reason at length. "
        "Turn this message into JSON only with keys: what (<=8 words), "
        "actions (max 3, each <=7 words, verb first), facts (object, max 4 short key/value pairs), "
        "steps (max 5, each <=6 words), risk (<=8 words or empty string). "
        f"For your understanding only, the schedule in this message is: {_labeled_str(text, subject, lang)}. "
        "The app prints those labeled dates in their own box - do NOT write the labels, any date, any time, or any number in your output. "
        "Facts must be about the message itself (for example: meeting, location, attendance, agenda) - never about dates. "
        f"Sender: {sender}\nSubject: {subject}\nText: {text[:6000]}"
    )
    body = json.dumps({"model": os.environ.get("CLEARDAY_MODEL", "unused"),
                       "temperature": 0.2, "max_tokens": 2500,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer unused",
                                          "User-Agent": "ClearDay/1.0"})
    try:
        data = json.loads(_call_model(req))
        content = data["choices"][0]["message"]["content"]
        raw = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
    except Exception:
        return None
    out = {
        "what": _clean_str(raw.get("what"), 10),
        "actions": _clean_str_list(raw.get("actions"), 3, 9),
        "facts": _clean_facts(raw.get("facts")),
        "steps": _clean_str_list(raw.get("steps"), 5, 8),
        "risk": _clean_str(raw.get("risk"), 10),
    }
    allowed = _allowed_tokens(f"{subject} {text}", lang)
    out["what"] = _strip_ungrounded(out["what"], allowed, lang)
    out["risk"] = _strip_ungrounded(out["risk"], allowed, lang)
    out["actions"] = [a for a in (_strip_ungrounded(x, allowed, lang) for x in out["actions"]) if a]
    out["steps"] = [a for a in (_strip_ungrounded(x, allowed, lang) for x in out["steps"]) if a]
    out["facts"] = _drop_date_facts(_ground_facts(out["facts"], allowed, f"{subject} {text}", lang), _label_dates(text, subject, lang))
    if not out["what"] and not out["actions"]:
        return None
    return out

REPLY_TEMPLATES = {
    "en": "Hello {name},\n\nThank you for your message. I confirm{dates_line}.\n\nThank you,\nJose Luis",
    "es": "Hola {name},\n\nGracias por su mensaje. Confirmo{dates_line}.\n\nGracias,\nJose Luis",
    "vi": "Xin chào {name},\n\nCảm ơn tin nhắn của bạn. Tôi xác nhận{dates_line}.\n\nCảm ơn bạn,\nJose Luis",
}
REPLY_DATES_LINE = {
    "en": " - I have noted: {dates}",
    "es": " - He anotado: {dates}",
    "vi": " - Tôi đã ghi: {dates}",
}

def draft_reply(text, sender="", subject="", lang="en", dates=None):
    """Draft a short reply to the sender. The model may draft the words;
    the only dates allowed are the extracted ones (rules-owned, exact).
    Falls back to a plain template. Returns the reply body text."""
    if lang not in LANG_NAMES:
        lang = "en"
    dates = [d for d in (dates or []) if d]
    base = os.environ.get("CLEARDAY_MODEL_URL")
    if base:
        prompt = (
            f"Write in {LANG_NAMES[lang]}. Be brief - answer directly, do not reason at length. Draft a short, polite email reply (3-5 lines) "
            "to the sender of this message, confirming what they asked. "
            "You may ONLY use these exact dates/times, copied word for word, and no others: "
            f"{dates if dates else 'NONE - do not mention any date or time'}. "
            "When you mention a date, copy it in full - weekday, month, and day, with its time. Never write a weekday by itself. "
            "Do not invent any fact, date, time, place, or number. "
            "Sign off as Jose Luis. Output the reply text only, no subject line. "
            f"Sender: {sender}\nSubject: {subject}\nMessage: {text[:4000]}"
        )
        body = json.dumps({"model": os.environ.get("CLEARDAY_MODEL", "unused"),
                           "temperature": 0.2, "max_tokens": 2500,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer unused",
                                              "User-Agent": "ClearDay/1.0"})
        try:
            data = json.loads(_call_model(req))
            content = (data["choices"][0]["message"]["content"] or "").strip()
            if content and len(content) > 20:
                content = _strip_ungrounded(content, _allowed_tokens(f"{subject} {text}", lang), lang)
                if len(content) > 20:
                    return content[:2000], "model"
        except Exception:
            pass
    name = (sender or "").split("<")[0].strip() or sender or "there"
    dates_line = REPLY_DATES_LINE[lang].format(dates=", ".join(dates[:3])) if dates else ""
    return REPLY_TEMPLATES[lang].format(name=name, dates_line=dates_line), "rules"

def transform(text, sender="", subject="", lang="en"):
    """Hybrid: rules first (they own dates + numbers, copied exactly).
    If a model is configured, its cleaned words overlay the rule output.
    Dates and numbers ALWAYS come from the rules - never from the model.
    """
    out = heuristic_transform(text, sender, subject, lang)
    model = llm_transform(text, sender, subject, lang)
    if model:
        for key in ("what", "actions", "facts", "steps", "risk"):
            if model.get(key):
                out[key] = model[key]
        out["source"] = "model"
        out["model_name"] = os.environ.get("CLEARDAY_MODEL", "")
    else:
        out["source"] = "rules"
        out["model_name"] = ""
    out["lang"] = lang if lang in CORE else "en"
    if not _has_ask(f"{subject} {text}", out["lang"]):
        out["actions"] = [CORE[out["lang"]]["no_ask"]]
    return out


def _get_json(url, headers=None, timeout=10):
    import time
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "ClearDay/1.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read()), int((time.time() - t0) * 1000)


def connector_proof():
    """Live metadata for the Connector proof page. Real calls, made now.
    GitHub through the Sprites GitHub connector gateway; Together AI through
    the Sprites Custom API connector gateway. Each side reports ok=False and
    the real error when it is down - this function never invents a number."""
    out = {"github": {"ok": False}, "together": {"ok": False}}
    gw = os.environ.get("CLEARDAY_GITHUB_GATEWAY", "")
    if gw:
        try:
            g = out["github"]
            user, ms1 = _get_json(gw.rstrip("/") + "/user")
            login = user.get("login", "")
            repo, _ = _get_json(gw.rstrip("/") + f"/repos/{login}/clearday")
            commits, _ = _get_json(gw.rstrip("/") + f"/repos/{login}/clearday/commits?per_page=1")
            rate, _ = _get_json(gw.rstrip("/") + "/rate_limit")
            c0 = (commits or [{}])[0]
            g.update({
                "ok": True, "ms": ms1, "login": login,
                "name": user.get("name") or "",
                "repos": user.get("public_repos"),
                "repo_desc": repo.get("description") or "",
                "repo_updated": (repo.get("pushed_at") or "")[:10],
                "commit_sha": (c0.get("sha") or "")[:7],
                "commit_msg": ((c0.get("commit") or {}).get("message") or "").split("\n")[0][:90],
                "commit_date": (((c0.get("commit") or {}).get("author") or {}).get("date") or "")[:10],
                "rate_left": ((rate.get("rate") or {}).get("remaining")),
                "rate_limit": ((rate.get("rate") or {}).get("limit")),
            })
        except Exception as e:
            out["github"] = {"ok": False, "error": str(e)[:160]}
    else:
        out["github"] = {"ok": False, "error": "GitHub connector is not set on this Sprite."}
    base = os.environ.get("CLEARDAY_MODEL_URL", "")
    model = os.environ.get("CLEARDAY_MODEL", "")
    if base:
        try:
            import time
            t = out["together"]
            models, ms1 = _get_json(base.rstrip("/") + "/models",
                                    headers={"Authorization": "Bearer unused", "User-Agent": "ClearDay/1.0"})
            raw_models = models.get("data") if isinstance(models, dict) else models
            ids = [m.get("id", "") for m in (raw_models or []) if isinstance(m, dict)]
            body = json.dumps({"model": model, "temperature": 0, "max_tokens": 400,
                               "messages": [{"role": "user", "content": "Answer in one short sentence: what is 2 + 2? Be brief - answer directly, do not reason at length."}]}).encode()
            req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer unused",
                                                  "User-Agent": "ClearDay/1.0"})
            t0 = time.time()
            data = json.loads(_call_model(req))
            ms2 = int((time.time() - t0) * 1000)
            content = ((((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or "").strip()
            usage = data.get("usage") or {}
            t.update({"ok": True, "ms": ms1, "call_ms": ms2, "models_count": len(ids),
                      "model": model, "on_list": model in ids,
                      "answer": content[:200], "call_id": data.get("id", ""),
                      "tokens_in": usage.get("prompt_tokens"), "tokens_out": usage.get("completion_tokens"),
                      "tokens_total": usage.get("total_tokens")})
        except Exception as e:
            out["together"] = {"ok": False, "error": str(e)[:160]}
    else:
        out["together"] = {"ok": False, "error": "Together AI connector is not set on this Sprite."}
    return out
