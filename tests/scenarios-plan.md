# ClearDay — 106-scenario test matrix (plan for tests/scenarios.py)

Data-driven suite designed Nov 26, 2026. Exactly **114 scenarios: 74 unit-level** (60 original + U61–U66 guards, added Nov 26 evening on the swarm's word + U67–U69 labeled dates, added Nov 26 late on Jose Luis's direct order + U70 facts guard, added after his KEY FACTS printout)
(`import clearday`, no network, no model) + **40 live HTTP** (against the app
inside the Sprite, Mailpit as the inbox).

## Determinism rule (applies to every row)

Assert ONLY on rules-owned or structural facts: `dates_numbers` (copied exactly
by the rules), JSON shape and keys, HTTP status codes, Content-Type, fixed
page markers, Mailpit message counts, follow-up store contents. **Never**
assert on model wording (`what`, model `actions`, draft text). Where the model
may answer, the assertion must hold on BOTH paths (rules and model) — that is
exactly why `dates_numbers` is the safe field: the model overlay never touches it.

## Contract assumed for the new endpoints (coordinator builds to this)

- `POST /api/clear` — JSON body `{text, sender?, subject?, lang?}` →
  `200 application/json` with the `transform()` dict as JSON (keys incl.
  `what, actions, facts, dates_numbers, source, lang, sender`).
  Missing/empty `text` → `400` JSON error. Invalid JSON → `400`.
  Text over the 50,000-char cap → 4xx. Unknown `lang` → falls back to `en`.
- `GET /api/followups` → `200 application/json`, a JSON array; each item
  carries the follow-up store fields (`what, sender, lang, mid, addr`).
- `GET /bulk` → 200 page listing the inbox emails with a form that POSTs to
  `/bulk/clear`. `POST /bulk/clear` → 200 page: one clear summary per inbox
  email (sender + subject + its exact dates) plus ONE combined
  “Everything you must do” list aggregating every email’s actions.
  Bulk clearing never sends, deletes, or modifies the inbox.

## The matrix

| ID | Category | Input sketch | Assertion (deterministic) |
|---|---|---|---|
| U01 | Dates — English formats | `heuristic_transform` on “The meeting is on Tuesday November 24.” | `dates_numbers == ["Tuesday November 24"]` |
| U02 | Dates — English formats | “moved from Monday November 23 to Tuesday November 24” | both dates present, in that order, nothing else |
| U03 | Dates — English formats | “Please reply before Friday November 27.” | `dates_numbers == ["Friday November 27"]` |
| U04 | Dates — English formats | “The form is due 11/24/2026.” | `dates_numbers == ["11/24/2026"]` |
| U05 | Dates — English formats | “The deadline is 2026-11-30.” | `dates_numbers == ["2026-11-30"]` |
| U06 | Dates — English formats | “See you November 27th at 17:30.” | `dates_numbers == ["November 27th", "17:30"]` |
| U07 | Dates — English formats | “Meet on March 3, 2026 at noon.” | `dates_numbers == ["March 3, 2026"]` |
| U08 | Dates — English formats | “The visit is on 11-24-2026.” (US dash) | `dates_numbers == ["11-24-2026"]` |
| U09 | Dates — English formats | “It starts at 5:15 PM in Room 4.” | `dates_numbers == ["5:15 PM"]` (AM/PM stays one token; single-digit room not extracted) |
| U10 | Dates — English formats | “Call at 12:00 AM if needed.” | `dates_numbers == ["12:00 AM"]` |
| U11 | Dates — English formats | “The train leaves at 5:15.” (bare 24h-style time) | `dates_numbers == ["5:15"]` |
| U12 | Dates — English formats | “Payment due February 30, 2026.” (impossible date) | extracted verbatim: `dates_numbers == ["February 30, 2026"]` — rules copy, never validate or “fix” |
| U13 | Dates — English formats | Full `sample_email.txt` through `heuristic_transform` | `dates_numbers == ["Monday November 23", "Tuesday November 24", "5:15 PM", "Friday November 27"]` |
| U14 | Dates — English formats | Same date written twice: “March 3 … March 3 …” | “March 3” appears exactly once in `dates_numbers` (dedupe) |
| U15 | Money & numbers | “The cost is $1,250.50 total.” | `dates_numbers == ["$1,250.50"]` |
| U16 | Money & numbers | “Tickets are $5 each.” | `dates_numbers == ["$5"]` (single-digit money still counts) |
| U17 | Money & numbers | “Room 412 holds 37 people.” | `dates_numbers == ["412", "37"]` |
| U18 | Money & numbers | “It takes 3.5 hours.” | `dates_numbers == ["3.5"]` |
| U19 | Money & numbers | “About 1,250 people came.” | `dates_numbers == ["1,250"]` (comma-grouped, no $ needed) |
| U20 | Money & numbers | “The fee is $25 and the room holds 40 people.” | `dates_numbers == ["$25", "40"]` in source order |
| U21 | Money & numbers | “We meet in 2026 to plan.” (bare year, no full date) | `dates_numbers == ["2026"]` (plain number; not swallowed by a date span) |
| U22 | Money & numbers | “Room 4 is on floor 2.” (single digits only) | `dates_numbers == []` (plain integers need 2+ digits) |
| U23 | Money & numbers | 8 distinct extractable items in one email | `len(dates_numbers) == 6` (cap) and the first entries are the dates (dates before numbers) |
| U24 | Money & numbers | “Pay $1,250.50, not $1,250.51.” | `$1,250.50` and `$1,250.51` both present, exactly as written |
| U25 | Guards — phones, ranges, fractions | “Call 415-555-0132 today.” | `dates_numbers == []` (phone never extracted) |
| U26 | Guards — phones, ranges, fractions | “Open from 10-12 on weekdays.” | `dates_numbers == []` (range is not a date or a number) |
| U27 | Guards — phones, ranges, fractions | “Use 1/2 cup of sugar.” | `dates_numbers == []` (fraction is not a slash date) |
| U28 | Guards — phones, ranges, fractions | “On November 24 the office closes.” | `dates_numbers == ["November 24"]` — the “24” is NOT also listed as a plain number |
| U29 | Guards — phones, ranges, fractions | “In 2026-11-30 we met.” vs plain “in 2026 we met” (two calls) | ISO form gives `["2026-11-30"]`; the bare-year form gives `["2026"]` — span logic separates them |
| U30 | Guards — phones, ranges, fractions | “The code is 555-0132.” | `dates_numbers == []` (dash fragment rejected by lookarounds) |
| U31 | Guards — phones, ranges, fractions | “See you on the 27th of November.” (day-first, unsupported) | `dates_numbers == ["27"]` — documents current behavior honestly: no month-name date is invented |
| U32 | Guards — phones, ranges, fractions | “Order #12345 shipped.” | `dates_numbers == ["12345"]` (long digit run outside a date span is a number) |
| U33 | No invention | “Hello, just checking in. Hope you are well.” | `dates_numbers == []` |
| U34 | No invention | Empty string input | `dates_numbers == []` and `actions == ["Read the key facts below"]` (fallback) |
| U35 | No invention | “Please reply.” only (no dates, no facts) | `dates_numbers == []`; `what` falls back to the sentence text (no subject given) |
| U36 | No invention | Text with a question but no date: “Can we talk tomorrow?” | `dates_numbers == []` (“tomorrow” is never turned into a date) |
| U37 | No invention | “The meeting is next Friday.” | `dates_numbers == []` (relative weekday is not copied as a date) |
| U38 | No invention | Sender/subject empty, body dateless | `sender == "Unknown sender"` and `dates_numbers == []` |
| U39 | Spanish | lang=es: “La reunión es el martes 24 de noviembre.” | `dates_numbers == ["martes 24 de noviembre"]` |
| U40 | Spanish | lang=es: “El plazo es el 24 de noviembre de 2026.” | `dates_numbers == ["24 de noviembre de 2026"]` |
| U41 | Spanish | lang=es: “A las 5:15 p. m. en el salón.” | `dates_numbers` contains `"5:15 p. m."` exactly |
| U42 | Spanish | lang=es: “Por favor responda antes del viernes.” with a date “28 de noviembre” in body | the es date extracted; no English-format phantom date added |
| U43 | Spanish | lang=es dateless: “Hola, solo escribo para saludar.” | `dates_numbers == []` and `lang == "es"` |
| U44 | Spanish | lang=es: fallback structure | `facts` keys are `"Quién"` / `"Qué"` and steps are the es CORE steps |
| U45 | Vietnamese | lang=vi: “Cuộc họp vào ngày 24 tháng 11.” | `dates_numbers == ["ngày 24 tháng 11"]` |
| U46 | Vietnamese | lang=vi: “Hạn chót là ngày 24 tháng 11 năm 2026.” | `dates_numbers == ["ngày 24 tháng 11 năm 2026"]` |
| U47 | Vietnamese | lang=vi: “Lúc 17 giờ 15 tại phòng họp.” | `dates_numbers == ["17 giờ 15"]` |
| U48 | Vietnamese | lang=vi: “Bắt đầu lúc 5:15.” | `dates_numbers == ["5:15"]` (vi time pattern) |
| U49 | Vietnamese | lang=vi dateless: “Xin chào, tôi chỉ kiểm tra.” | `dates_numbers == []` and `lang == "vi"` |
| U50 | Grounding filter | `_allowed_tokens("Lunch is on March 3. The room holds 40 people.")`, then `_strip_ungrounded("Pay $999 by January 40, or confirm March 3 for 40 people, not 41, at 9:99 PM", …)` | result contains “March 3” and “40 people”; contains none of `$999`, `January 40`, `41`, `9:99` |
| U51 | Grounding filter | Source “…costs $25…”; strip “Pay $25 today, not $26” | `$25` kept, `$26` removed |
| U52 | Grounding filter | Source has “November 24”; strip “See you November 24 or November 25” | “November 24” kept, “November 25” removed |
| U53 | Grounding filter | Strip a sentence with NO date/number tokens: “Thank you for your message” | returned unchanged |
| U54 | Grounding filter | Strip with empty allowed set: “Meet March 3 at 5:15 PM, room 412” | every token removed; result has no digits |
| U55 | Grounding filter | `_allowed_tokens` on “See you November 27th” | normalized token is `november 27` (ordinal suffix normalized away) — so a model writing “November 27” is still grounded |
| U56 | Grounding filter | `_allowed_tokens("$1,250.50 fee")` | normalized token is `1250.50` ($ and comma normalized) |
| U57 | Grounding filter | Strip es: source “el 24 de noviembre”, lang=es; strip “el 24 de noviembre o el 25 de noviembre” | the real es date kept; the invented `25 de noviembre` removed |
| U58 | Transform structure | Four hint sentences (“Please reply…”, “Please confirm…”, “Please bring…”, “Please send…”) | `len(actions) == 3` (max-3 rule holds at rules level) |
| U59 | Transform structure | No hint words anywhere | `actions == ["Read the key facts below"]` and `steps == CORE en steps` (3 fixed steps) |
| U60 | Transform structure | `heuristic_transform(..., lang="fr")` (unsupported) | treated as English: `lang` handling falls back, es/vi patterns not applied, no crash |
| U61 | Guards — dotted dates | "We meet Jan. 5 at noon…" | `dates_numbers` contains "Jan. 5" (dotted month abbreviations now extracted) |
| U62 | Guards — dotted dates | `_strip_ungrounded("Meet Jan. 5 or Jan. 9", allowed from "…Jan. 5…")` | "Jan. 5" kept, invented "Jan. 9" cut |
| U63 | Guards — facts keys | `_ground_facts({"Due January 40": "Friday", …})` | no key carries "January 40" — keys are grounded like values |
| U64 | Guards — facts rows | `_ground_facts({"importance": "high", "deadline": "matters", "Room": "Room 412"}, source with Room 412)` | junk rows dropped (no shared word with the source); anchored row kept |
| U65 | Guards — duties | `transform(thank-you email: "…No reply is needed at all.")` | `actions == ["This email asks nothing of you"]` — no invented duties |
| U66 | Guards — duties | `transform(sample email)` (it asks: confirm, bring, send) | guard stays silent; real actions stand |
| U67 | Labeled dates: the sample email | labeled list == Original Meeting Date / New Meeting Date (time joined) / Reply by — exactly as Jose Luis wrote them |
| U68 | "Please pay the invoice by March 5." | one item: Pay by: March 5 |
| U69 | "The picnic is on July 4." | one item, label "" (no cue words, no invented label) |
| U70 | Facts guard fed the printout's broken facts | every date-label row + bare weekday dropped; only the real fact (Location) survives |
| U71 | Mixed email: no-ask sentence + real ask | the real ask wins — duties survive |
| U72 | English ask, Spanish picker | the ask is seen in any language |
| U73 | Chatty question, no ask | a '?' alone is not a duty — guard fires |
| U74 | 'Deadline' as a topic noun | pressure words alone ask nothing — guard fires |
| L01 | API — /api/clear happy path | POST JSON: sample email text, sender “Maria Lopez”, subject “Board meeting moved”, lang en | 200, Content-Type JSON, `dates_numbers == ["Monday November 23", "Tuesday November 24", "5:15 PM", "Friday November 27"]` |
| L02 | API — /api/clear happy path | POST JSON “The form is due 11/24/2026. Please reply.” | 200; `dates_numbers == ["11/24/2026"]` |
| L03 | API — /api/clear happy path | POST JSON dateless text | 200; `dates_numbers == []` |
| L04 | API — /api/clear happy path | POST JSON with lang=es + “martes 24 de noviembre” | 200; `dates_numbers == ["martes 24 de noviembre"]`; `lang == "es"` |
| L05 | API — /api/clear happy path | POST JSON with lang=vi + “ngày 24 tháng 11” | 200; `dates_numbers == ["ngày 24 tháng 11"]`; `lang == "vi"` |
| L06 | API — /api/clear happy path | POST JSON omitting sender and subject | 200; `sender == "Unknown sender"`; all required keys present (`what, actions, facts, dates_numbers, source, lang`) |
| L07 | API — /api/clear happy path | POST JSON “Room 412 holds 37 people. The cost is $1,250.50.” | 200; `dates_numbers == ["412", "37", "$1,250.50"]` (numbers in text order, exactly as the rules collect them) |
| L08 | API — /api/clear happy path | POST JSON “Call 415-555-0132. Open 10-12.” | 200; `dates_numbers == []` (guards hold through the API too) |
| L09 | API — errors | POST JSON `{}` (no text field) | 400; JSON body has an error key/message |
| L10 | API — errors | POST JSON `{"text": ""}` | 400 |
| L11 | API — errors | POST body that is not JSON (`text=hello` form-style) with JSON expected | 400 (never 500, never a stack trace page) |
| L12 | API — errors | POST JSON text of 60,000 chars | 4xx status (400 or 413); no clear page produced |
| L13 | API — errors | GET /api/clear (wrong method) | 404 or 405 — never 200 |
| L14 | API — errors | POST JSON `{"text": "Please reply.", "lang": "fr"}` | 200; `lang == "en"` (fallback), `dates_numbers == []` |
| L15 | API — followups | Fresh state (empty store): GET /api/followups | 200 JSON; body parses as a list; `len == 0` |
| L16 | API — followups | Seed inbox, GET /inbox/clear on Maria’s email, then GET /api/followups | list has ≥1 item; the item’s `mid` equals Maria’s Mailpit ID and `addr == "maria.lopez@example.org"` |
| L17 | API — followups | After L16, send the reply via POST /reply/send (real fields), then GET /api/followups | Maria’s `mid` no longer in the list |
| L18 | API — followups | GET /api/followups Content-Type check | header contains `application/json` |
| L19 | Bulk | Delete all mail (Mailpit API), then POST /bulk/clear immediately | 200; page shows the empty state (0 emails cleared); no crash |
| L20 | Bulk | GET /bulk with empty inbox | 200; page contains the clear-all form posting to `/bulk/clear` |
| L21 | Bulk | POST /inbox/fresh (exactly Maria), then POST /bulk/clear | 200; exactly 1 summary block; it names Maria Lopez / “Board meeting moved” and shows `Tuesday November 24` |
| L22 | Bulk | L21 continued | combined list heading present (“Everything you must do”) and the summary’s dates include `5:15 PM` and `Friday November 27` |
| L23 | Bulk | Fresh + send 2 more emails with distinct dates (11/24/2026; 2026-11-30) → 3 in inbox, POST /bulk/clear | 3 summary blocks; each block shows its own exact date (`11/24/2026` in one, `2026-11-30` in the other, `Tuesday November 24` in Maria’s) — no date leaks between blocks |
| L24 | Bulk | L23 continued | combined “Everything you must do” list has ≥3 action entries aggregated from all 3 emails |
| L25 | Bulk | Mailpit total before vs after POST /bulk/clear | totals equal — bulk clearing never deletes or sends |
| L26 | Bulk | POST /bulk/clear twice in a row (same inbox) | both 200; second result has the same summary count as the first (idempotent, read-only) |
| L27 | Pages — regression | GET / | 200; exactly one `class='btn rawbtn'` (“Read my story”); hero marker “Long message in” present |
| L28 | Pages — regression | GET /?sample=1&lang=en | 200; form filled: `value='Maria Lopez'`, sample banner marker, “Room 4” in the body field |
| L29 | Pages — regression | POST / with HTML in text (`Hello <b>ZZTEST</b> world`) | 200; raw `<b>ZZTEST</b>` absent from the result page |
| L30 | Pages — regression | POST / with 60,000-char text | 200 with the polite too-long refusal (mentions the 50,000 limit), no clear page |
| L31 | Pages — regression | GET /why | 200; research markers present (“Why the cream page? For judges”, “WCAG 2.2 AA”) |
| L32 | Pages — regression | GET /connected | 200; honesty footer “No typed-in numbers” present (page shape only — connector LIVE/DOWN state is provider-dependent and NOT asserted) |
| L33 | Pages — regression | GET /followups in clean state | 200; “No follow-ups waiting” marker present |
| L34 | Pages — regression | POST (write attempt) through the public /mailpit proxy (e.g. DELETE messages) | 403; inbox total unchanged |
| L35 | Reply mechanics | POST /reply {mid} on Maria’s email (after clearing it) | 200 draft page: “YOUR REPLY DRAFT”, `<textarea`, `name='body'`, “Send this reply”; Mailpit total unchanged (nothing sent) |
| L36 | Reply mechanics | POST /reply/send {mid, to=maria.lopez@example.org, subject, body=edited words} | 200 sent page with “See both emails in Mailpit”; Mailpit total +1; the delivered message text contains the edited words |
| L37 | Reply mechanics | POST /reply/send with to=stranger@example.org | refused: Mailpit total unchanged; no Re: message created |
| L38 | Reply mechanics | POST /reply (paste path) with unmatched sender + subject | 200; page contains the NO SEND BUTTON notice and no `/reply/send` form |
| L39 | Reply mechanics | POST /reply (paste path) blank sender + blank subject + sample text | 200; `maria.lopez@example.org` present in the page and a `/reply/send` form IS present (blank/blank adoption) |
| L40 | Reply mechanics | Wrong-method/edge: GET /reply/send | 404 or 405 — never 200, nothing sent (Mailpit total unchanged) |

## Category counts

| Category | IDs | Count |
|---|---|---|
| Dates — English formats (unit) | U01–U14 | 14 |
| Money & numbers (unit) | U15–U24 | 10 |
| Guards — phones, ranges, fractions (unit) | U25–U32 | 8 |
| No invention (unit) | U33–U38 | 6 |
| Spanish (unit) | U39–U44 | 6 |
| Vietnamese (unit) | U45–U49 | 5 |
| Grounding filter (unit) | U50–U57 | 8 |
| Transform structure (unit) | U58–U60 | 3 |
| Guards — keys, dotted dates, duties (unit) | U61–U66 | 6 |
| **Unit subtotal** | | **74** |
| API — /api/clear happy path (live) | L01–L08 | 8 |
| API — errors (live) | L09–L14 | 6 |
| API — followups (live) | L15–L18 | 4 |
| Bulk (live) | L19–L26 | 8 |
| Pages — regression (live) | L27–L34 | 8 |
| Reply mechanics (live) | L35–L40 | 6 |
| **Live subtotal** | | **40** |
| **TOTAL** | | **100** |
