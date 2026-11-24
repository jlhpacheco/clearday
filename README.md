# ClearDay

**Long message in. One clear page out.**

ClearDay is a personal agent built for people with dyslexia. It takes a long, hard-to-read email or document and turns it into one clear page, in the same order every time:

1. **WHAT THIS IS** — in one sentence
2. **YOU MUST DO** — at most 3 actions
3. **KEY FACTS** — who, what, where, in a table
4. **DATES + NUMBERS** — big type, one per line

Then ClearDay **remembers**. Its follow-up list shows what is still waiting for a reply, so nothing gets lost. It runs on a Fly.io Sprite — a small computer of its own that sleeps when idle, wakes in seconds, and keeps its memory on a persistent disk. It uses the Sprites **GitHub connector** (see the live connector check at `/connected`).

**Live demo:** https://clearday-bnjwz.sprites.app/
**Connector proof:** https://clearday-bnjwz.sprites.app/connected

Built for Fly.io **Hacksgiving**, November 23–29, 2026.

---

## Why this matters: dyslexia, in numbers

Every number below was checked on the source's own page. Sources are US institutions.

| Fact | Source |
|---|---|
| Dyslexia affects **20% of the population** — **1 in 5 children**, about **12 million children in the US** | Yale Center for Dyslexia & Creativity, Connecticut Longitudinal Study |
| Dyslexia is **life-long**, and represents **80–90% of all learning disabilities** | Yale Center for Dyslexia & Creativity |
| Schools identify only **0–4%** of students, even though scientific assessment finds **20%** — most dyslexic readers are never identified | Yale Center for Dyslexia & Creativity |
| The reading achievement gap appears **as early as first grade, and persists** | Yale Center for Dyslexia & Creativity |
| Undiagnosed, dyslexia is linked to **higher rates of dropout, unemployment, anxiety and depression**; studies estimate **almost 50% of prison inmates have dyslexia** | Yale Center for Dyslexia & Creativity |
| Dyslexia affects **boys and girls equally** | Yale Center for Dyslexia & Creativity (JAMA, 1990) |
| **15–20% of the population** have some symptoms of dyslexia, including slow or inaccurate reading, poor spelling, or poor writing | International Dyslexia Association (IDA), Dyslexia Basics |
| About **85%** of students classified with a learning disability have a **primary disability in reading and language processing** | International Dyslexia Association (IDA) |
| Between **12% and 20%** of individuals have some type of learning disability, and **dyslexia is the most common** one | NICHD / National Institutes of Health |

Dyslexia is **not** reversing letters, and it is **not** low intelligence. Yale defines it as an *unexpected* difficulty in reading in a person with the intelligence to be a much better reader. Dyslexic readers are slow readers — and, paradoxically, often very fast and creative thinkers, with excellent skills in reasoning, imagination, and seeing the big picture.

**The cost of a wall of text is real.** For 1 in 5 people, a long email is not a small annoyance. It is slow, error-prone work — and a missed date, a missed form, or a missed reply can cost a meeting, a benefit, or a job. The information was sent. It just never became usable.

ClearDay exists to close that last gap: not more text about the text, but the same facts, laid out the way a dyslexic reader can actually use them.

Sources:
- Yale Center for Dyslexia & Creativity — https://dyslexia.yale.edu/update-connecticut-longitudinal-study-cls/
- Yale Center for Dyslexia & Creativity, *Speaking with One Voice* — https://dyslexia.yale.edu/wp-content/uploads/2017/08/YCDC-Guide-to-Talking-About-Dyslexia_Final032017.pdf
- International Dyslexia Association, Dyslexia Basics — https://dyslexiaida.org/dyslexia-basics/
- International Dyslexia Association, Definition of Dyslexia (adopted October 22, 2025) — https://dyslexiaida.org/definition-of-dyslexia/
- NICHD / NIH — https://www.nichd.nih.gov/about/profiles/KnowNICHD/miller

---

## My story — why I built this

My name is **Jose Luis Pacheco**. I live with severe dyslexia. It is personal to me.

My own doctors prescribed the fix decades ago: help turning long written material into **graphs, tables, and charts**. That is not a preference. It is how my brain takes in information. Reading long text is slow, halting work. I can miss a date or a deadline buried in a long page.

I have still built a full life and career on top of that — public service, board rooms, and work where the reading never stops. But the cost is paid every single day, in time and in risk, one long document at a time.

So for Hacksgiving I built the tool I needed first: **ClearDay**. It does to every long message what my doctors told me to do by hand — it turns words into a table, in a fixed order, with the dates and numbers big and impossible to miss. Then, because a Sprite remembers, it does not let the message be forgotten.

I built it for people who suffer from dyslexia. If it helps one person catch the one date that mattered, it was worth building.

— Jose Luis Pacheco, Campbell, California

**Hear it in my own voice** — this is me, speaking for myself, not a bio written about me:

- [SDAC, October 24, 2024 — Jose Luis Pacheco, speaking to board members during his first term on the CalPERS Board of Administration (2022–2026)](https://www.youtube.com/watch?v=S0sxcC-EQrg)

ClearDay is my personal project. I worked on it on my own breaks, on my personal accounts. It is not a District project.

From that talk: I am an IT professional at the San Jose Evergreen Community College District, where I have worked since 2015. I am a past president of CSEA Chapter 363 and a former South Bay Labor Council delegate. I serve on the board of Latinas Contra Cancer. I hold two bachelor's degrees — economics, and biological sciences. I did all of that reading the way I read: slowly, carefully, and with tables and charts doing the heavy lifting. That is the reader ClearDay is built for.

## Serving others — and thankful for it

My whole career has one shape: serving other people.

| Where I served | Who it was for |
|---|---|
| CalPERS Board of Administration | The retirees and workers whose pension money had to be guarded with care |
| CSEA Chapter 363, as president | School employees — so nobody works a lifetime in public service and retires with nothing |
| South Bay Labor Council, as a delegate | Working families across the South Bay |
| Latinas Contra Cancer, board chair | Latina women and families facing breast cancer and its disparities |
| My day job in IT since 2015 | The students and staff of a community college district |

I am thankful — for every teacher, colleague, and friend who ever handed me a chart instead of a chapter, and for every chance I have had to serve. ClearDay is that same service, in software: helping people get the message without fighting the page. Serving others is the work. This is just my newest way of doing it — and I think it is an awesome one.

---

## How ClearDay is designed for dyslexic readers

Design rules follow the International Dyslexia Association's guidance and WCAG 2.2 AA / ADA / Section 508 practice:

- Cream background (#FFF6D6), never pure white; dark text, never pure black on white
- Arial / Verdana sans-serif, body text 21–22px, line height 1.7, extra letter spacing
- Left-aligned, one column, short lines
- Bold only — no italics, no underlining
- Every section has a **big label + a shape + a color** — never color alone, and never red/green as a meaning pair
- Dates and numbers are **copied exactly from the source, never invented**
- The same page order, every time — no surprises to re-learn

## How it works

| Step | What happens |
|---|---|
| 1. Paste | A long email or message goes into the form |
| 2. Transform | ClearDay extracts the facts, actions, dates and numbers (`clearday.py`) |
| 3. Render | One clear page comes out (`render.py`), same order every time |
| 4. Remember | The follow-up is saved to `memory.json` on the Sprite's persistent disk |
| 5. Follow up | `/followups` shows what is still waiting for a reply |
| 6. Connector | `/connected` calls GitHub through the Sprites GitHub connector gateway — no key in the code |

## Run it

```bash
python3 app.py            # serves on port 8080 (or $PORT)
```

On a Sprite, `app.py` runs as the `http` service on port 8080, which serves the Sprite's own URL. Set `CLEARDAY_GITHUB_GATEWAY` to the connector gateway URL copied from the connector's page in the Fly dashboard, and grant the connector access by Sprite name in its access policy.

Optional: set `CLEARDAY_MODEL_URL` to a Sprites Connector gateway URL for a model provider (Anthropic / OpenRouter) for LLM-quality extraction. Without it, ClearDay uses its built-in exact-extraction fallback — dates and numbers still come only from the source text.

## Files

| File | Job |
|---|---|
| `app.py` | Web app + follow-up memory + connector check |
| `clearday.py` | The transform: text in, clear facts out |
| `render.py` | The dyslexia-friendly page |
| `sample_email.txt` | The demo email used in testing |

## Submission (Hacksgiving)

ClearDay — a persistent accessibility agent on a Fly Sprite that turns long, hard-to-read messages into one clear page for people with dyslexia, then remembers and follows up. Built by Jose Luis Pacheco, who lives with severe dyslexia, during Hacksgiving week.
