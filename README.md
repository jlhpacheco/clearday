# ClearDay

**Long message in. One clear page out.**

**1 in 5 people has dyslexia** (Yale Center for Dyslexia & Creativity). A 40-line email goes in. **3 actions, a fact table, and the dates in big type** come out.

![ClearDay demo — paste a long email, get one clear page](demo.gif)

ClearDay is a personal agent built for people with dyslexia. It takes a long, hard-to-read email or document and turns it into one clear page, in the same order every time:

1. **WHAT THIS IS** — in one sentence
2. **YOU MUST DO** — at most 3 actions
3. **KEY FACTS** — who, what, where, in a table
4. **DATES + NUMBERS** — big type, one per line

Then ClearDay **remembers**. Its follow-up list shows what is still waiting for a reply, so nothing gets lost. It runs on a Fly.io Sprite — a small computer of its own that sleeps when idle, wakes in seconds, and keeps its memory on a persistent disk. It uses the Sprites **GitHub connector** (see the live connector check at `/connected`).

**Live demo:** https://clearday-bnjwz.sprites.app/
**Connector proof:** https://clearday-bnjwz.sprites.app/connected

**Tested:** Smoke test **6/6** · Playwright browser test **21/21** · 1 real bug caught by the tests and fixed (see Testing).

Built for Fly.io **Hacksgiving**, November 23–29, 2026.

## How ClearDay meets the Hacksgiving rules

| Rule | Proof |
|---|---|
| Runs on a Fly.io Sprite | The live demo above *is* the Sprite — it sleeps when idle and wakes on your click |
| Uses at least one Sprites connector | **GitHub** — live proof at [/connected](https://clearday-bnjwz.sprites.app/connected); this repo itself was created through that connector, from inside the Sprite |
| Built during Hacksgiving week | Built and submitted **Monday, November 23, 2026** — the first day |

## Try it in 60 seconds

1. Open the **live demo**: https://clearday-bnjwz.sprites.app/
2. In **From**, type: `Maria Lopez`
3. In **Subject**, type: `Board meeting moved`
4. Copy the sample email below into **Paste the long message**, and press **Make it clear**.

> Hi everyone, I hope you are all doing well. I am writing with several updates about our board meeting and a few related items that have come up since last week. First, please note that the meeting originally scheduled for Monday November 23 has been moved, after a long discussion with the venue and several board members who had conflicts, to Tuesday November 24 at 5:15 PM. The meeting will be held in Room 4 and also on Zoom for those who cannot attend in person. Second, please reply to this email to confirm whether you can attend in person or on Zoom, and please do that before Friday November 27 so we can order the right number of chairs and print the right number of packets. Third, please bring your photo ID, because the building has changed its check-in rules. The agenda includes the budget, the gala report, and a vote. If you cannot attend, please send your proxy to the chair before the meeting. Thank you so much for everything you do, and I look forward to seeing you there. Warm regards, Maria

What comes out: one clear page — the meeting moved to **Tuesday November 24, 5:15 PM**, 3 things to do, the facts in a table, and every date in big type. Then check **Follow-ups**: ClearDay remembered it.

## See it — the whole trip, in pictures

**1. The form.** One box. Paste the long message.

![ClearDay form](tests/home.png)

**2. The clear page.** Same order every time: what this is, what you must do, the facts, the dates in big type.

![ClearDay clear page](tests/result.png)

**3. It remembers.** The follow-up list — what is still waiting for a reply.

![ClearDay follow-ups](tests/followups.png)

---

## Three languages — built for the communities I serve

ClearDay works in **English, Español, and Tiếng Việt**. Pick the language on the form. The whole clear page comes back in that language — the labels, the steps, the fact table — and the date finder reads dates the way each language writes them:

| Language | A date, as written | What ClearDay finds |
|---|---|---|
| English | Tuesday November 24, 5:15 PM | Tuesday November 24 · 5:15 PM |
| Español | martes 24 de noviembre, 5:15 p. m. | martes 24 de noviembre · 5:15 p. m. |
| Tiếng Việt | ngày 24 tháng 11, 17 giờ 15 | ngày 24 tháng 11 · 17 giờ 15 |

Why these three: they are the languages of the families I serve in the South Bay — at my college district, in labor, and at Latinas Contra Cancer. A clear page only helps if it arrives in the language you dream in. Every translation was checked for plain, everyday wording — short phrases, no fancy words — because that is the rule for all three languages.

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

## Inspiration — my story, why I built this

It starts the way it always starts: one long email. The meeting moved. Confirm by Friday. Bring your photo ID. Send a proxy if you cannot come. For most people, 30 seconds. For me, that email is a wall — and somewhere in the wall is a date I cannot afford to miss.

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

## Testing — checked the way a judge will use it

| Test | What it proves | Result |
|---|---|---|
| **Smoke test** (inside the Sprite, against the live service) | Form loads · sample email gives the **exact 4 dates, none invented** · connector check names the GitHub user · pasted code stays escaped · giant pastes refused · follow-ups labeled | **6 of 6 PASS** — log in `tests/smoke-test-2026-11-23.log` |
| **Playwright browser test** (TypeScript, real Chromium, public demo) | A judge's path: open → fill → submit → clear page → follow-ups, with screenshots · cream background exact · body text 21px · left-aligned | **21 of 21 PASS** — script, log, and screenshots in `tests/` |

One honest note: the Playwright test first caught a real miss — the page body itself was 16px, under the 21–22px design rule, even though every visible element was sized right. The test failed, the CSS was fixed (one line), and the re-run passed 21 of 21. That is what the tests are for.

## Challenges we ran into

| Challenge | What happened |
|---|---|
| A public demo can be misused | Anyone can paste anything into a public form — so all output is escaped, entries are capped, and every result page is labeled as visitor-made. A red-team check found this; it was fixed before submission |
| My own design rule, broken quietly | The Playwright test caught the page body at 16px — under the 21–22px rule — even though every visible element looked right. One line of CSS fixed it; the re-run passed 21 of 21 |
| Three languages, three date systems | Spanish writes *martes 24 de noviembre, 5:15 p. m.*; Vietnamese writes *ngày 24 tháng 11, 17 giờ 15*. Each needed its own date finder — and a translation checker caught 6 wording fixes before launch |
| A Sprite is a real little computer | Services, restarts, and persistent memory all had to be learned and verified live — nothing was assumed from the docs alone |

## Accomplishments I am proud of

| Accomplishment | Proof |
|---|---|
| Built, tested, and submitted on **day one** of Hacksgiving week | This repo + the submission confirmation, Nov 23 |
| The connector did real work | The GitHub repo itself was **created through the Sprites GitHub connector**, from inside the Sprite |
| Tested like it matters | Smoke test 6/6 · Playwright 21/21 · the failure in between, shown honestly in Testing |
| Three languages at launch | English · Español · Tiếng Việt — the languages of the families I serve |
| It helps the builder first | I am the first user. ClearDay reads my board email the way my doctors prescribed |

## What I learned

A demo is not done when it works for the builder. It is done when it survives strangers, tests, and a tired judge at midnight — in their language, at their pace. And the test you almost skip is the one that finds the 16px.

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

```
  PASTE A LONG MESSAGE
          |
          v
  +------------------------------+
  |  SPRITE: clearday            |
  |  transform -> clear page     |
  |  memory.json -> follow-ups   |
  +------------------------------+
          |                \
          v                 v
  ONE CLEAR PAGE      GITHUB CONNECTOR
  (same order,        (this repo was made
   every time)         through it)
```

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

## What's next

Real readers. The next step is putting ClearDay in front of dyslexic readers in my own communities — my college district and the Latinas Contra Cancer network — and letting their feedback set the next version. A tool for readers should be judged by readers.
