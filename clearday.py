"""ClearDay core: long text -> 1 dyslexia-friendly clear page.

Design rules (International Dyslexia Association (IDA, USA) + US WCAG 2.2 AA (ADA / Section 508) + Rello et al.):
- Sans serif, big type, wide letter/line spacing, left aligned
- Cream / warm background, dark (not pure black) text, no pure white glare
- Color + label + shape for every section (never color alone)
- Avoid red/green as a meaning pair
- Bold only, no italics / underline, short phrases, max 3 actions
"""
import re, json, os, urllib.request, threading
from datetime import datetime

DATE_RE = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{1,2}-\d{1,2}-\d{2,4}\b|\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b|\b(?:[01]?\d|2[0-3]):[0-5]\d\b", re.I)
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


_MODEL_SEM = threading.Semaphore(3)  # max model calls in flight, demo-wide

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
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(_MODEL_DEADLINE)
    if t.is_alive():
        raise TimeoutError(f"model call passed the {_MODEL_DEADLINE}s cap")
    if "error" in box:
        raise box["error"]
    return box["data"]

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
        "Do NOT output dates or numbers - they are handled separately. "
        f"Sender: {sender}\nSubject: {subject}\nText: {text[:6000]}"
    )
    body = json.dumps({"model": os.environ.get("CLEARDAY_MODEL", "unused"),
                       "temperature": 0.2, "max_tokens": 2500,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer unused",
                                          "User-Agent": "ClearDay/1.0"})
    try:
        with _MODEL_SEM:
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
    out["facts"] = {k: v for k, v in ((k, _strip_ungrounded(v, allowed, lang)) for k, v in out["facts"].items()) if v}
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
