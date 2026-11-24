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
ACTION_HINTS = ("please", "reply", "confirm", "bring", "send", "sign", "add", "attend", "rsvp", "submit", "call")

def _sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 3]

def heuristic_transform(text, sender="", subject=""):
    sents = _sentences(text)
    dates = []
    for m in DATE_RE.finditer(text):
        if m.group(0) not in dates:
            dates.append(m.group(0))
    actions = []
    for s in sents:
        low = s.lower()
        if "from:" in low or "subject:" in low:
            continue
        if any(h in low for h in ACTION_HINTS) and len(s) < 180:
            clean = re.sub(r"^(first|second|third|finally),?\s+", "", s.rstrip(".!?"), flags=re.I)
            clean = re.sub(r"^please\s+", "Please ", clean)
            actions.append(" ".join(clean.split()[:9]))
        if len(actions) >= 3:
            break
    if not actions and sents:
        actions = ["Read the key facts below"]
    title = subject.strip() or (sents[0][:60] if sents else "New message")
    return {
        "what": title,
        "sender": sender or "Unknown sender",
        "actions": actions[:3],
        "facts": {"Who": sender or "See original", "What": title},
        "dates_numbers": dates[:4],
        "steps": ["Read this page", "Do the actions in the amber box", "Check the date in the white box"],
        "risk": "",
        "source_date": datetime.now().strftime("%a %b %d"),
    }

def llm_transform(text, sender="", subject=""):
    """Optional: use a Sprites Connector gateway model if configured.
    Env: CLEARDAY_MODEL_URL (connector gateway base, OpenAI-compatible),
         CLEARDAY_MODEL (model name). No key needed through the gateway
         (dummy key) - the gateway attaches the stored credential.
    Falls back to heuristic on any failure. Never blocks the demo.
    """
    base = os.environ.get("CLEARDAY_MODEL_URL")
    if not base:
        return None
    prompt = (
        "Turn this message into JSON only with keys: what (<=8 words), "
        "actions (max 3, each <=7 words, verb first), facts (Who, What, Where), "
        "dates_numbers (list, exact dates/times/money from text only, never invent), "
        "steps (max 5, each <=6 words), risk (<=8 words or empty). "
        f"Sender: {sender}\nSubject: {subject}\nText: {text[:6000]}"
    )
    body = json.dumps({"model": os.environ.get("CLEARDAY_MODEL", "unused"),
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer unused"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"]["content"]
        out = json.loads(re.search(r"\{.*\}", content, re.S).group(0))
        out["sender"] = sender; out["source_date"] = datetime.now().strftime("%a %b %d")
        return out
    except Exception:
        return None

def transform(text, sender="", subject=""):
    return llm_transform(text, sender, subject) or heuristic_transform(text, sender, subject)
