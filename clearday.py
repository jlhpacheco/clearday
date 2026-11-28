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
           "do not reply", "don't reply", "no reply please", "no reply expected", "for information only", "no reply is necessary"),
    "es": ("no es necesario responder", "no hace falta responder", "solo comparto",
           "solo para tu información", "solo para su información",
           "no es necesario que responda", "no es necesario que respondas",
           "no hace falta que responda", "no hace falta que respondas"),
    "vi": ("không cần trả lời", "chỉ chia sẻ", "chỉ để bạn biết"),
}
# Scoping phrases (round-17 simplicity): literal shapes that do not cancel
# an ask - they mark an occurrence that never was one. "at present" is an
# idiom, "the show" carries its article before the noun, "una muestra" is
# the noun, never the verb. An entry that needs context the phrase does
# not carry - a subject, a following word, an "except when" - does NOT
# belong in this list.
SCOPES = {
    "en": ("at present", "the present", "this present", "all present", "a present",
           "your present address", "the show", "show times",
           "come monday", "come tuesday", "come wednesday", "come thursday",
           "come friday", "come saturday", "come sunday",
           "come spring", "come summer", "come fall", "come autumn", "come winter",
           "come rain or shine"),
    "es": ("una muestra", "la muestra", "muestra gratuita"),
    "vi": (),
}
ASK_EXTRA = {
    "en": ("register", "complete", "fill out", "fill in", "return", "pay", "review", "check",
           "let me know", "let us know", "forget", "remember to", "be sure", "make sure",
           "need you", "asking", "request", "required", "must", "deadline", "due by",
           "remit", "requested", "be signed", "be returned", "be submitted", "be completed",
           "be paid", "be sent", "would you mind", "show", "present", "come"),
    "es": ("registre", "registrar", "complete", "completar", "rellene", "rellenar", "devuelva",
           "devolver", "pague", "pagar", "revise", "revisar", "avise", "avíseme", "olvide",
           "recuerde", "asegúrese", "necesito que", "solicito", "requerido", "debe", "fecha límite",
           "confirma", "responde", "envía", "envia", "envíe", "firma", "firme", "revisa", "completa",
           "firmar", "remitir", "sírvase", "tenga a bien",
           "enviar", "confirmar", "responder", "entregar", "entregue",
           "firmes", "pagues", "envíes", "envies", "devuelvas", "traigas", "respondas",
           "completes", "revises", "rellenes", "registres", "decir", "diga", "digan", "dime",
           "se ruega", "paga", "devuelve", "trae", "firmad", "enviad", "enviadlo",
           "muestra", "muestre", "mostrar", "presenta", "presente", "presentar",
           "enseña", "enseñe", "enseñar", "ven", "venga", "vengan", "venir"),
    "vi": ("đăng ký", "hoàn thành", "điền", "trả lại", "thanh toán", "xem lại", "cho tôi biết",
           "đừng quên", "nhớ", "hãy chắc chắn", "yêu cầu", "bắt buộc", "phải", "hạn chót",
           "nộp", "hoàn tất", "chuyển khoản", "đề nghị", "phản hồi", "mang"),
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

def _es_finite():
    # Finite forms - present, subjunctive and future (rounds 21 + 23): the scan family
    # held only singular stems, so group instructions ("Los solicitantes
    # presentan...") and futures ("Usted presentará...") were invisible.
    # Generated from the same base as the rest of the family - plurals
    # ride the singular stems (muestra -> muestran, diphthong included),
    # futures ride the infinitive (presentar -> presentara/as/an/emos,
    # accents already folded by _deacc). The irregular forms mail
    # actually uses are named in _ES_IRREGULAR - named, not generated.
    out = set()
    for w in _ES_BASE:
        if " " in w:
            continue
        d = _deacc(w)
        if w.endswith("r"):
            out |= {d + e for e in ("a", "as", "an", "emos")}
        if w.endswith(("ar", "er", "ir")) and len(d) >= 5:
            # Present + subjunctive ride the infinitive stem, singular and plural:
            # entregar -> entregan / entreguen. Most verbs enter the
            # base as infinitives only, so the singular-stem rule above
            # never sees them. The length floor keeps "ir" / "dar"
            # stems from minting bare syllables.
            stem = d[:-2]
            out |= {stem + "an", stem + "en", stem + "a", stem + "e"}
        if d[-1:] in "ae":
            out.add(d + "n")
    out.discard("page")  # pagar's stem mint coins an English noun; its
    # true subjunctive (pague) is already in the family (round-24 technical)
    return out | _ES_IRREGULAR

_ES_IRREGULAR = {"viene", "vienen", "vendra", "vendras", "vendran",
                 "vendremos", "dira", "diras", "diran", "diremos",
                 "dicen", "digan", "tengan", "pidan"}
_ES_FINITE = _es_finite()
# Plural imperatives (the ustedes forms) carry glued pronouns too -
# "presentenlo" (present it, all of you) - so their stems join the tail
# expansion: -ar verbs take the -en stem, -er/-ir the -an stem
# (round-22 skeptic). Five stems are named, not generated - the
# spelling-change residue: paguen, entreguen, digan, traigan, vengan.
_ES_IMP_PL = sorted({_deacc(w)[:-2] + "en" for w in _ES_BASE
                     if " " not in w and w.endswith("ar") and len(_deacc(w)) >= 5} |
                    {_deacc(w)[:-2] + "an" for w in _ES_BASE
                     if " " not in w and w.endswith(("er", "ir")) and len(_deacc(w)) >= 5} |
                    {"paguen", "entreguen", "digan", "traigan", "vengan"})
_ES_DEACC = sorted({_deacc(w) for w in _ES_BASE} | _ES_FINITE |
                   {_deacc(w) + t for w in _ES_STEMS + _ES_IMP_PL for t in _ES_TAILS + _ES_STACKS})
_ASK_RE_ES = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in _ES_DEACC) + r")\b")
_NO_ASK_ALL = tuple(p for lg in ("en", "es", "vi") for p in NO_ASK_PHRASES[lg])
_SCOPES_ALL = tuple(p for lg in ("en", "es", "vi") for p in SCOPES[lg])

def _stamp_re(phrases):
    # Whole words only (round-19 technical): a stamp must never match
    # inside a longer word - the English scope "a present" was found
    # eating the Spanish verb "presenta" ("la secretaria presenta...").
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in sorted(phrases, key=len, reverse=True)) + r")\b")

_NO_ASK_RE = _stamp_re(_NO_ASK_ALL)
_SCOPES_RE = _stamp_re(tuple(p for p in _SCOPES_ALL if "muestra" not in p))
_ANNOUNCE_ES = "muestra|presenta|enseña|muestre|presente|enseñe|muestran|presentan|enseñan|muestren|presenten|enseñen|mostrará|presentará|enseñará|mostrarán|presentarán|enseñarán"
# The three muestra scopes ride their own stamp (round-30 judge):
# eaten plainly, "la muestra" starves the announcement stamp of its
# re-anchor when the phrase is the intervener's noun ("el museo, en
# atención a la muestra, presenta..."), so this stamp refuses when
# an announce verb follows, across an optional de-phrase - the
# stamp then eats phrase and verb together, as it does for every
# other intervener noun.
_SCOPES_MUESTRA_RE = re.compile(r"\b(?:(?:una|la)\s+muestra(?:\s+gratuita)?|muestra\s+gratuita)\b(?!(?:\s+gratuita)?(?:\s+(?:de|del)\s+\w+(?:\s+\w+)?)?[\s,]+(?:" + _ANNOUNCE_ES + r")\b)")
# The Spanish announcement verbs are stamped by a GUARDED pattern, not a
# literal (round-17 skeptic): "se muestra / se presenta / se enseña" is an
# announcement only while no place or time follows before the sentence ends -
# "Se presenta a la oficina mañana" is an order to appear, and the stamp
# must not touch it.
_SE_SCOPE_RE = re.compile(r"\bse (" + _ANNOUNCE_ES + r")\b(?![^.!?;\n]*?\b(?:a la\b|al\b|a trabajar\b|ante el\b|ante la\b|en la puerta\b|en recepción\b|mañana\b|a las\b|al entrar\b))")
# Named-subject descriptives (round-18 skeptic): "El museo presenta
# una exposición" announces what a third party does - the reader is
# asked nothing. Determiner + one noun + the verb stamps, unless a
# reader word (tu / su) follows the verb, and never when the subject
# noun is a reader-role noun (round-19 skeptic): bureaucratic Spanish
# writes instructions in the third person - "El solicitante presenta
# los documentos" is an order to the reader wearing a role name.
# The subject guard answers one question - may this word serve as the
# subject noun? Reader-role nouns fail it (they name the reader), and
# "se" fails it in every branch: it is not a noun at all, and letting it
# fill a slot lets the stamp eat "se presenta" duties (U196). The role
# guard applies only under definite determiners (round-20 skeptic):
# "un solicitante" in a news sentence is a stranger, not the reader.
_READER_ROLES = "solicitantes?|participantes?|aspirantes?|postulantes?|estudiantes?|titular(?:es)?|contribuyentes?|pacientes?|residentes?|derechohabientes?|comparecientes?|pensionistas?|cosolicitantes?|interesad[oa]s?|candidat[oa]s?|usuari[oa]s?|emplead[oa]s?|pasajer[oa]s?|vecin[oa]s?|client[ea]s?|miembr[oa]s?|beneficiari[oa]s?|asegurad[oa]s?|afiliad[oa]s?|inquilin[oa]s?|pensionad[oa]s?|alumn[oa]s?|jubilad[oa]s?|becari[oa]s?|pasantes?|arrendatari[oa]s?"
_ROLE_GUARD = r"(?!(?:" + _READER_ROLES + r"|se)\b)"
_SE_GUARD = r"(?!se\b)"
_MOD_CHAIN_ES = r"(?:\s+(?:y\s+)?(?:de|en|del|por|con|seg[úu]n|ante|durante|tras|mediante|desde|a\s+través\s+de|a)\s+(?:(?:el|la|los|las)\s+)?\w+)*"
# The pattern's first alternative is the guard made visible (round-22
# skeptic): a role-headed subject phrase is consumed whole, so the
# stamp can never restart at a determiner inside the role's own
# de-phrase and re-read "la cuenta" as the subject - "el titular de
# la cuenta presenta..." asks, because the reader's party is acting.
# Its modifier chain is prep-headed (de / en / del at first; por /
# con / según / ante / durante / tras joined in round 27; mediante /
# desde / a través de in round 28; the one-letter "a" in round 29,
# landed in both spellings of the prep list at once) on purpose: the
# verb is never prep-headed, so the chain can repeat without ever
# eating it - a bare optional word in that seat ate the verb in this
# fix's first build, and U268 caught it.
# A coordinated second subject is consumed with the first ("el
# titular y la directora...", ", junto con la directora,") - any
# determiner left standing is a fresh start for the stamp, and the
# stamp would orphan the role and silence the pair (round-24 skeptic).
# The continuation is one repeating group over the whole coordination
# vocabulary - y/o conjuncts repeat, bare comma lists, junto con /
# junto a with or without the comma, acompañado de appositives -
# because round 25's survivor audit found every connector the group
# did not know orphaning its conjunct the same way. "ni" is NOT a
# member on purpose: "ni el titular ni la directora presentan..." is
# a negative description, and it stays silent only because the stamp
# still silences the pair (round-25 skeptic, U307).
# Round 26 widened the same group to the connectors' other spellings:
# a comma before a final y/o (", y la gerente"), the register
# synonyms así como / además de, acompañado without its commas and
# in the plural, and chain links that carry a leading "y" ("de la
# cuenta y de la tarjeta") - a y-headed link is still prep-headed
# after the "y", so the chain still cannot reach the verb
# (round-26 skeptic, U309-U324).
# Round 27 audited the third position - what INTERVENES between the
# role subject and the verb. A determiner-headed adjunct left
# standing ("el titular, en la oficina, presenta...") was a fresh
# start for the stamp, so the group gained an adjunct member and
# the chain's prep set widened to the adjunct prepositions (por /
# con / según / ante / durante / tras) for the bare forms; a "como"
# member covers tanto...como and the appositive como; the y/o
# member takes its written "y/o" spelling and a también slot; and
# the three members Spanish spells with accents (así como, además
# de, acompañado, según) take their accent-dropped spellings too,
# because senders drop accents and the failure direction is
# erasure. One exposure is recorded, not hidden: a single leading
# "ni" plus an adjunct now asks, the twin of the single-ni plus
# conjunct exposure standing since round 24 - the ni...ni pair
# itself still silences (round-27 skeptic, U325-U348).
# Round 28 took the intervention position's second layer and one
# parenthetical. The register's stock adjunct phrases joined the
# seats their shapes allow: mediante / desde / a través de ride
# both the adjunct member and the chain; por medio de / de parte
# de / para sit in the adjunct member only - the first two because
# their bare forms already compose link by link on the chain, para
# because it must NEVER join the chain: a para link would eat
# purpose infinitives ("para presentar los documentos, acude...")
# and manufacture the erasure it claims to fix, while the member's
# determiner slot refuses infinitives on its own. And a comma-led
# chain member covers the parenthetical de-phrase ("el titular, de
# la cuenta, presenta..."), the one comma shape no member reached
# (round-28 skeptic and technical, U349-U366).
# Round 29 closed the intervention position's third stratum - the
# stock phrases built on the one-letter preposition "a", as opener
# (a nombre de, a petición de), as tail (en atención a, en cuanto
# a), and bare (a la ventanilla). "a" joins the chain's prep set,
# in the constant and in the comma-led member's own copy in the
# same edit: it is not para - it heads infinitives only after a
# governing verb, never in subject-intervener position, so no
# infinitive trap exists. Two more units sit in the adjunct member
# only (para efectos de, al amparo de - "al" is a contraction no
# chain link can match). The same round fixed an invention on the
# announcement side: the stamp's subject gained an optional
# intervener segment - a possessive phrase (en su sala, desde su
# portal) or a bare hoy / mañana - between the subject and the
# verb, carrying the role guard on both nouns, so thing and staff
# announcements stop inventing duties while a role subject with
# the same phrase still asks (round-29 skeptic and judge,
# U367-U386).
# Round 30 paid three prices in three different seats. The
# announcement stamp gained a possessive HEAD branch (su / sus +
# the same role-guarded noun phrase): "su estado de cuenta
# presenta un saldo" is the bank's commonest announcement frame
# and it was inventing duties. Alternative 1 gained a pre-verb
# segment - one non-announce verb, an object, and "y" - because
# the stamp was building a fake subject out of the object plus
# the conjunction ("el titular recoge la carpeta y presenta..."
# lost its verb to "la carpeta y presenta"); the segment is
# alt-1-side precisely because the same swallow is load-bearing
# for the museum twin, and the usted twin stays blind - the
# subject-blindness it shares with the name head, classified for
# a board decision. And the muestra scopes learned to refuse
# when an announce verb follows (see _SCOPES_MUESTRA_RE), so a
# scope can no longer starve the stamp of its anchor
# (round-30 skeptic and judge, U387-U401).
# Round 31 tempered the segment and paid the simplicity price.
# The segment fires only when an announce verb follows the "y"
# (a lookahead on _ANNOUNCE_ES): untempered, it ate any first
# verb that carried an object, and when that verb was itself a
# duty the duty vanished ("el titular envía el pago y archiva
# los documentos" read as news). Three of the judge's seven
# probes were NOT this - recoge / guarda / espera sit outside
# the scan's verb family and read the same in round 30, the
# standing out-of-family classification, unchanged. And the
# muestra exclusion stopped re-spelling its three phrases: it
# filters on the substring, so a fourth muestra phrase can
# never ride the plain stamp by accident (round-31 judge and
# simplicity, U402-U405). The same round's technical pass priced
# two more in the seats round 30 built: the stamp's possessive
# branch could re-anchor mid-sentence on an intervener's noun
# ("su titular, en su portal, presenta..." went silent), so
# alternative 1 learned the possessive role head too (su / sus
# joining the determiner set before _READER_ROLES) and the role
# subject is consumed before the stamp can slide; and the
# muestra refusal learned to see past "gratuita", the adjective
# its own third phrase carries (round-31 technical, U406-U409).
_SUBJ_SCOPE_RE = re.compile(r"\b(?:(?:(?:el|la|los|las|este|esta|ese|esa)|(?:su|sus))\s+(?:" + _READER_ROLES + r")\b" + _MOD_CHAIN_ES + r"(?:(?:,\s+|\s+)(?:y/o|y|o)\s+(?:también\s+)?(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|(?:,\s+|\s+)as[íi]\s+como\s+(?:también\s+)?(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|(?:,\s+|\s+)adem[áa]s\s+de\s+(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|(?:,\s+|\s+)acompa[ñn]ad[oa]s?\s+de\s+(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|(?:,\s+|\s+)como\s+(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|,\s+(?:para\s+efectos\s+de|al\s+amparo\s+de|a\s+través\s+de|por\s+medio\s+de|de\s+parte\s+de|en|con|por|seg[úu]n|ante|durante|tras|mediante|desde|para)\s+(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|,\s+(?:y\s+)?(?:de|en|del|por|con|seg[úu]n|ante|durante|tras|mediante|desde|a\s+través\s+de|a)\s+(?:(?:el|la|los|las)\s+)?\w+" + _MOD_CHAIN_ES + r"|,\s+(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r"|(?:,\s+|\s+)junto\s+(?:con|a)\s+(?:el|la|los|las)\s+\w+" + _MOD_CHAIN_ES + r")*" + r"(?:\s+(?!(?:" + _ANNOUNCE_ES + r")\b)\w+\s+(?:(?:el|la|los|las|su|sus)\s+\w+|a\s+(?:el|la|los|las)\s+\w+)\s+y(?=\s+(?:" + _ANNOUNCE_ES + r")\b))?" + r"|(?:(?:(?:el|la|los|las|este|esta|ese|esa)\s+(?:" + _ROLE_GUARD + r"\w+\s+)?" + _ROLE_GUARD + r"\w+|(?:su|sus)\s+(?:" + _ROLE_GUARD + r"\w+\s+)?" + _ROLE_GUARD + r"\w+|(?:un|una)\s+(?:" + _SE_GUARD + r"\w+\s+)?" + _SE_GUARD + r"\w+)(?:\s+(?:de|del)\s+\w+(?:\s+\w+)?)?(?:[\s,]+(?:(?:en|desde|con|por|ante|durante|tras|mediante|seg[úu]n|a)\s+(?:su|sus)\s+(?:" + _ROLE_GUARD + r"\w+\s+)?" + _ROLE_GUARD + r"\w+(?:\s+(?:de|del)\s+\w+(?:\s+\w+)?)?|hoy|mañana))?[\s,]+(?:" + _ANNOUNCE_ES + r")\b(?!\s+(?:tu|su)\b)))")

# A chain link may cross a short object ("el documento firmado por el
# notario o..."), but it may not step over a word that is itself an ask
# word: in a punctuation-free run-on ("...que firmes el documento envía
# el pago o trae el recibo") an untempered span swallows the second duty
# whole (round-15 technical). The temper set is the scan's OWN
# generated family - _ES_DEACC plus the bare stems and gerunds behind
# it - never a second hand list: a span refuses exactly the words the
# scan can see (round-16 simplicity + technical).
def _fold_acc(w):
    return "".join({"a": "[aá]", "e": "[eé]", "i": "[ií]", "o": "[oó]", "u": "[uú]"}.get(c, re.escape(c)) for c in w)

_ES_TEMPER_WORDS = sorted(set(_ES_DEACC) | {_deacc(w) for w in _ES_STEMS} |
                          {_deacc(w)[:-1] for w in _ES_BASE if " " not in w and w.endswith("r")})
_SPAN_ES = (r"(?:(?!(?:" + "|".join(_fold_acc(w) for w in _ES_TEMPER_WORDS) + r")\b)\w+\s+){0,6}?")
_VI_BASE = [w for w in ACTION_HINTS["vi"] + ASK_EXTRA["vi"] if w not in _NOT_ASK_WORDS]
_VI_TEMPER_WORDS = sorted({w for w in _VI_BASE if " " not in w})
_SPAN_VI = (r"(?:(?!(?:" + "|".join(re.escape(w) for w in _VI_TEMPER_WORDS) + r")\b)\w+\s+){0,6}?")

# A no-need phrase governs the verb right after it: in "No hace falta
# firmarlo ni enviarlo" (no need to sign it or send it) the glued verbs
# are exactly what the sentence says is NOT needed, so the phrase and
# its governed verb(s) lift out together - otherwise the scan hears two
# duties in a sentence that cancels them (round-7 skeptic, Nov 28).
_PRON = "lo|la|los|las|le|les|me|te|se|nos"
_GOVERNED = "(?:(" + _PRON + r")\s+)?\w+(?:" + _PRON + ")?"
_NO_NEED_RE = re.compile(r"\b(no hace falta|no es necesario|no necesitas|no es preciso|no tienes|no hay que|no hay necesidad de|no es obligatorio|no es menester|no resulta necesario|no se precisa|no procede|no se requiere|no corresponde|no cabe)"
                         r"(\s+ni)?(\s+que)?(?:[\s,]*(?:por ahora|por el momento))?[\s,]*"
                         + _GOVERNED + r"([\s,]+" + _SPAN_ES + r"(?:ni|o)\s+(?:que\s+)?" + _GOVERNED + ")*")
_NO_NEED_EN_RE = re.compile(r"\b(no need to|there is no need to|don't need to|do not need to|don't have to|do not have to|needn't|need not|not required to|not necessary to|no obligation to|under no obligation to|not obliged to)\s+\w+(\s+(or|and)\s+\w+)*")
_NEG_ASK_ES_RE = re.compile(r"\b(favor de no|se ruega\s+" + _SPAN_ES + r"no|se solicita no|sin necesidad de|por favor,?\s+no|(?:te |le |les )?pedimos que no|se pide que no|(?:te |le |les )?ruego que no|rogamos no|rogamos que no|absténgase de|(?:se ruega\s+" + _SPAN_ES + r"|favor de )?abstenerse de|evite|evita|eviten|sírvase no|se le pide no|no se moleste en)\s+" + _GOVERNED + r"([\s,]+" + _SPAN_ES + r"ni\s+" + _GOVERNED + r")*")
_BARE_NO_ES_RE = re.compile(r"\bno\s+" + _GOVERNED + r"([\s,]+" + _SPAN_ES + r"(?:ni|o)\s+(?:que\s+)?" + _GOVERNED + ")*")
_NO_NEED_VI_RE = re.compile(r"\bkhông (?:cần(?:\s+thiết)?|nhất thiết|bắt buộc|việc gì)(\s+phải)?\s+\w+(\s+" + _SPAN_VI + r"hay\s+\w+)*")
_DO_NOT_EN_RE = re.compile(r"\b(do not|don't|that you not)\s+\w+(\s+(or|and)\s+\w+)*")
_NEVER_EN_RE = re.compile(r"\bnever\s+\w+(\s+(or|and)\s+\w+)*")
_NEG_ASK_VI_RE = re.compile(r"\b(đừng|chớ|không nên|không phải)(\s+có)?\s+\w+")

def _has_ask(text, lang="en"):
    """True when the source text itself asks the reader for something.
    Round-3 rebuild (skeptic + technical lenses, Nov 27): first lift the
    'no reply needed' phrases OUT of the text - the ask-words inside them
    ('reply' in 'no need to reply') must not trip the scan - then look for
    a real ask-word in ANY of the three languages, on word boundaries, so
    'add' inside 'addition' and 'sign' inside 'signed' stay silent. A real
    ask anywhere outranks a no-ask phrase anywhere; a question mark alone
    is conversation, not a duty."""
    text = unicodedata.normalize("NFC", text or "")  # round-20 technical: decomposed (NFD) Vietnamese must match the literal phrases
    low = (text or "").lower().replace("\u2019", "'").replace("\u2018", "'")
    low = _NO_ASK_RE.sub(" ", low)
    low = _SCOPES_RE.sub(" ", low)
    low = _SCOPES_MUESTRA_RE.sub(" ", low)
    low = _SE_SCOPE_RE.sub(" ", low)
    low = _SUBJ_SCOPE_RE.sub(" ", low)
    low = _NO_NEED_EN_RE.sub(" ", _NO_NEED_RE.sub(" ", low))
    low = _NO_NEED_VI_RE.sub(" ", _BARE_NO_ES_RE.sub(" ", _NEG_ASK_ES_RE.sub(" ", low)))
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
