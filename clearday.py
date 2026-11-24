"""ClearDay core: long text -> 1 dyslexia-friendly clear page.

Design rules (International Dyslexia Association (IDA, USA) + US WCAG 2.2 AA (ADA / Section 508) + Rello et al.):
- Sans serif, big type, wide letter/line spacing, left aligned
- Cream / warm background, dark (not pure black) text, no pure white glare
- Color + label + shape for every section (never color alone)
- Avoid red/green as a meaning pair
- Bold only, no italics / underline, short phrases, max 3 actions
"""
import re, json, os, urllib.request
from datetime import datetime

DATE_RE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,?\s+\d{4})?\b|\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b", re.I)
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
           "steps": ["Read this page", "Do the actions in the amber box", "Check the date in the white box"]},
    "es": {"who": "Quién", "what": "Qué", "unknown_sender": "Remitente desconocido", "see_original": "Ver el original",
           "fallback_action": "Lee los datos clave de abajo",
           "steps": ["Lee esta página", "Haz lo que dice el cuadro de color ámbar", "Revisa la fecha en el cuadro blanco"]},
    "vi": {"who": "Ai", "what": "Việc gì", "unknown_sender": "Không rõ người gửi", "see_original": "Xem bản gốc",
           "fallback_action": "Đọc thông tin chính bên dưới",
           "steps": ["Đọc trang này", "Làm các việc trong khung màu hổ phách", "Kiểm tra ngày trong khung trắng"]},
}

def _sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 3]

def heuristic_transform(text, sender="", subject="", lang="en"):
    if lang not in CORE:
        lang = "en"
    core = CORE[lang]
    hints = ACTION_HINTS[lang]
    sents = _sentences(text)
    dates = []
    for rx in (DATE_RES[lang], DATE_RE):
        for m in rx.finditer(text):
            if m.group(0) not in dates:
                dates.append(m.group(0))
    dates = [d for d in dates if not any(d != o and o.startswith(d) for o in dates)]
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
        "dates_numbers": dates[:4],
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
        f"Write every value in {LANG_NAMES[lang]}. "
        "Turn this message into JSON only with keys: what (<=8 words), "
        "actions (max 3, each <=7 words, verb first), facts (object, max 4 short key/value pairs), "
        "steps (max 5, each <=6 words), risk (<=8 words or empty string). "
        "Do NOT output dates or numbers - they are handled separately. "
        f"Sender: {sender}\nSubject: {subject}\nText: {text[:6000]}"
    )
    body = json.dumps({"model": os.environ.get("CLEARDAY_MODEL", "unused"),
                       "temperature": 0.2, "max_tokens": 1500,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer unused",
                                          "User-Agent": "ClearDay/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
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
    if not out["what"] and not out["actions"]:
        return None
    return out

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
    return out
