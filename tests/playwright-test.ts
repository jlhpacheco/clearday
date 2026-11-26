/**
 * ClearDay — Playwright smoke test (TypeScript)
 * Tests the public demo at https://clearday-bnjwz.sprites.app/
 * Run:  npx tsx playwright-test.ts
 * Outputs: home.png, result.png, followups.png, results.log (in this folder)
 */
import { chromium } from "playwright";
import * as fs from "fs";
import * as path from "path";
import * as net from "net";
import * as http from "http";
import * as dns from "dns";
import { fileURLToPath } from "url";

/**
 * Local CONNECT relay. This VM's egress proxy works with curl and Node
 * (CONNECT -> 200) but drops Chromium's own proxy requests
 * (ERR_TUNNEL_CONNECTION_FAILED / ERR_EMPTY_RESPONSE). So when an
 * HTTPS_PROXY is configured, the test starts a tiny local relay:
 * Chromium -> this relay (no auth) -> upstream proxy (Node, with auth).
 * On a normal machine with no proxy env, no relay is used.
 */
async function startRelay(upstream: URL) {
  const upHost = await dns.promises
    .lookup(upstream.hostname, { family: 4 })
    .then((r) => r.address)
    .catch(() => upstream.hostname);
  const upPort = Number(upstream.port || 3128);
  const auth =
    "Basic " +
    Buffer.from(
      `${decodeURIComponent(upstream.username)}:${decodeURIComponent(upstream.password)}`
    ).toString("base64");

  const server = http.createServer((_req, res) => {
    res.writeHead(501);
    res.end("relay handles CONNECT only");
  });

  server.on("connect", (req, clientSocket: net.Socket, head: Buffer) => {
    const target = req.url || "";
    const up = net.connect(upPort, upHost, () => {
      up.write(
        `CONNECT ${target} HTTP/1.1\r\nHost: ${target}\r\n` +
          `Proxy-Authorization: ${auth}\r\nProxy-Connection: Keep-Alive\r\n\r\n`
      );
    });
    let buf = Buffer.alloc(0);
    const onData = (chunk: Buffer) => {
      buf = Buffer.concat([buf, chunk]);
      const idx = buf.indexOf("\r\n\r\n");
      if (idx === -1) return;
      const header = buf.slice(0, idx).toString();
      const rest = buf.slice(idx + 4);
      up.off("data", onData);
      if (/^HTTP\/1\.1 200/.test(header)) {
        clientSocket.write("HTTP/1.1 200 Connection Established\r\n\r\n");
        if (rest.length) clientSocket.write(rest);
        if (head.length) up.write(head);
        up.pipe(clientSocket);
        clientSocket.pipe(up);
      } else {
        clientSocket.write("HTTP/1.1 502 Bad Gateway\r\n\r\n");
        clientSocket.end();
        up.end();
      }
    };
    up.on("data", onData);
    up.on("error", () => clientSocket.destroy());
    clientSocket.on("error", () => up.destroy());
  });

  await new Promise<void>((res) => server.listen(0, "127.0.0.1", res));
  const port = (server.address() as net.AddressInfo).port;
  return { server, port };
}

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BASE = "https://clearday-bnjwz.sprites.app";
const SAMPLE = fs.readFileSync(
  path.join(HERE, "..", "sample_email.txt"),
  "utf-8"
);

type Result = { name: string; ok: boolean; detail: string };
const results: Result[] = [];

function check(name: string, ok: boolean, detail = "") {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
}

async function bodyText(page: any): Promise<string> {
  return (await page.locator("body").innerText()).replace(/\s+/g, " ");
}

async function main() {
  // Route Chromium through the local relay when a proxy env is set
  // (see startRelay above); otherwise connect directly.
  const proxyEnv = process.env.HTTPS_PROXY || process.env.https_proxy;
  let relay: Awaited<ReturnType<typeof startRelay>> | null = null;
  let launchProxy: { server: string } | undefined;
  if (proxyEnv) {
    relay = await startRelay(new URL(proxyEnv));
    launchProxy = { server: `http://127.0.0.1:${relay.port}` };
  }
  const browser = await chromium.launch({ headless: true, proxy: launchProxy });
  // This VM's egress proxy intercepts TLS with its own CA (trusted by the
  // system curl, not by Chromium's store), so the test context accepts it.
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  page.setDefaultTimeout(60_000);

  // ---------- Step 1: home page ----------
  await page.goto(BASE + "/", { waitUntil: "load", timeout: 90_000 });

  const title = await page.title();
  check("Home: page title is 'ClearDay'", title === "ClearDay", `title="${title}"`);

  const h1 = page.locator("h1").first();
  check(
    "Home: heading 'ClearDay' visible",
    (await h1.isVisible()) && (await h1.innerText()).includes("ClearDay")
  );

  check("Home: From field visible", await page.locator('input[name="sender"]').isVisible());
  const homeBody = await page.locator("body").innerText();
  check("Home: HIS narrative on the clear page, right under the hero - 'what it is like to be dyslexic'", homeBody.includes("Before you judge this app, please take a moment to experience what it is like to be dyslexic"));
  check("Home: the story strip has ONE button - 'Read my story' (no Mailpit button)", (await page.locator("a.rawbtn").count()) === 1 && (await page.locator("a.rawbtn").first().innerText()).includes("Read my story"));
  await page.locator("a.rawbtn").first().click();
  const dlgOpen = await page.evaluate(() => { const d = document.getElementById("rawbox") as HTMLDialogElement | null; return !!d && d.open; });
  check("Home: 'Read my story' opens ONE dialog - his story on top, the raw inbox below", dlgOpen);
  const story = await page.evaluate(() => { const d = document.getElementById("rawbox") as HTMLDialogElement | null; return d ? d.textContent || "" : ""; });
  check("Home: the dialog's story is his FULL story ('three tries' + the Thanksgiving close)", story.includes("three tries") && story.includes("thankful this Thanksgiving"), "");
  const freshMsg = page.locator("#freshmsg");
  check("Home: the SAME press starts the FRESH delivery - progress bar + 'on its way' words", await page.locator("#freshfill").isVisible() && ((await freshMsg.innerText()).includes("on its way") || (await freshMsg.innerText()).includes("just landed")), "");
  let landedText = "";
  for (let i = 0; i < 25 && !landedText.includes("Hi everyone"); i++) {
    await page.waitForTimeout(1000);
    for (const f of page.frames()) {
      if (f.url().includes("/view/")) {
        try { landedText = await f.evaluate(() => document.body ? document.body.innerText : ""); } catch {}
        if (landedText.includes("Hi everyone")) break;
      }
    }
  }
  check("Home: raw-inbox dialog LANDS on Maria's email already open - body visible, NO click on the message needed", landedText.includes("Hi everyone") && landedText.includes("5:15"), "");
  check("Home: progress bar FINISHES - 'It just landed in the raw inbox' over the opened email", (await freshMsg.innerText()).includes("just landed"), "");
  // Build C (Nov 26, Jose Luis's pick): the dialog must NOT jump on its own.
  const dlgScrollTop = await page.evaluate(() => { const d = document.getElementById("rawbox") as HTMLDialogElement | null; return d ? d.scrollTop : -1; });
  check("Home (build C): after the email lands, the dialog did NOT scroll itself - his story is still at the top", dlgScrollTop === 0, `scrollTop=${dlgScrollTop}`);
  check("Home (build C): the landed note is BIG and the 'See the email' button is showing", await page.locator("#seeemail").isVisible() && (await freshMsg.evaluate((e) => parseFloat(getComputedStyle(e).fontSize))) >= 24, "");
  await page.click("#seeemail");
  await page.waitForTimeout(600);
  const dlgScrollAfter = await page.evaluate(() => { const d = document.getElementById("rawbox") as HTMLDialogElement | null; return d ? d.scrollTop : -1; });
  check("Home (build C): the button scrolls ONLY when the reader taps it", dlgScrollAfter > 0, `scrollTop=${dlgScrollAfter}`);
  await page.locator("#rawclose").click();
  check("Home: Subject field visible", await page.locator('input[name="subject"]').isVisible());
  check("Home: 'Paste the long message' box visible", await page.locator('textarea[name="text"]').isVisible());

  let home = await bodyText(page);
  check(
    "Home: 'Public demo — please paste sample text only' line visible",
    home.includes("Public demo — please paste sample text only")
  );

  await page.screenshot({ path: path.join(HERE, "home.png"), fullPage: true });
  check("Home: screenshot saved", fs.existsSync(path.join(HERE, "home.png")), "home.png");

  // ---------- Step 1b: the green sample button path (added Nov 24) ----------
  // The button must FILL the form where the reader can see it - never skip it.
  await page.click("a.btn[href*='sample=1']");
  await page.waitForSelector('input[name="sender"][value="Maria Lopez"]', { timeout: 30_000 });
  const sFrom = await page.inputValue('input[name="sender"]');
  check("Sample button: From filled with 'Maria Lopez'", sFrom === "Maria Lopez", `from="${sFrom}"`);
  const sSubj = await page.inputValue('input[name="subject"]');
  check("Sample button: Subject filled", sSubj === "Board meeting moved", `subject="${sSubj}"`);
  const sBody = await page.inputValue('textarea[name="text"]');
  check("Sample button: message body filled in the box", sBody.includes("Room 4") && sBody.length > 100, `body length=${sBody.length}`);
  const filled = await bodyText(page);
  check("Sample button: 'Sample loaded in the form' note shown", filled.includes("Sample loaded in the form"));
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=WHAT THIS IS", { timeout: 60_000 });
  const sRes = await bodyText(page);
  check("Sample button: result page shows exact date 'Tuesday November 24'", sRes.includes("Tuesday November 24"));
  await page.goto(BASE + "/", { waitUntil: "load", timeout: 90_000 });

  // ---------- Step 2: submit the sample email ----------
  await page.fill('input[name="sender"]', "Maria Lopez");
  await page.fill('input[name="subject"]', "Board meeting moved");
  await page.fill('textarea[name="text"]', SAMPLE);
  // Thinking banner: dispatch a held submit (navigation paused by the test)
  // and confirm the banner appears - the same wiring a real click uses.
  await page.evaluate(() => {
    const f = document.querySelector("form") as HTMLFormElement;
    f.addEventListener("submit", (e) => e.preventDefault(), { once: true });
    f.requestSubmit();
  });
  let thinkShown = true;
  try {
    await page.locator("#thinking").waitFor({ state: "visible", timeout: 3_000 });
  } catch { thinkShown = false; }
  check("Thinking: blinking 'AI is thinking' banner shows while the model works", thinkShown);
  await page.evaluate(() => { document.querySelectorAll("button[type=submit]").forEach((b) => { (b as HTMLButtonElement).disabled = false; }); });
  await page.click('button[type="submit"]');
  await page.waitForSelector("text=WHAT THIS IS", { timeout: 60_000 });

  const res = await bodyText(page);
  for (const label of ["WHAT THIS IS", "YOU MUST DO", "KEY FACTS", "DATES + NUMBERS"]) {
    check(`Result: section '${label}' shown`, res.includes(label));
  }
  check(
    "Result: 'Demo page — made from text pasted by a visitor' label shown",
    res.includes("Demo page — made from text pasted by a visitor")
  );
  check("Result: exact date 'Tuesday November 24' shown", res.includes("Tuesday November 24"));
  check("Result: right column present - 'IF YOU DO NOTHING' + 'Why the cream page'", res.includes("IF YOU DO NOTHING") && res.includes("Why the cream page"));
  const bigBtns = await page.locator("button.bigbtn").count();
  check("Result: REPLY button is the BIG button (noticeable, active)", bigBtns >= 1, `big buttons=${bigBtns}`);
  check("Result: exact time '5:15 PM' shown", res.includes("5:15 PM"));

  await page.screenshot({ path: path.join(HERE, "result.png"), fullPage: true });
  check("Result: screenshot saved", fs.existsSync(path.join(HERE, "result.png")), "result.png");

  // ---------- Step 2b: the Mailpit inbox path (added Nov 24) ----------
  // The Inbox ROUTE still works, but its TAB left the nav on Nov 26 (Jose Luis: it confused everyone).
  check("Nav: NO Inbox tab in the top nav anymore", (await page.locator('.navrow a[href="/inbox"]').count()) === 0, "");
  await page.goto(BASE + "/inbox", { waitUntil: "load", timeout: 90_000 });
  await page.waitForSelector("text=THE INBOX", { timeout: 30_000 });
  const ib = await bodyText(page);
  check("Inbox: real email from 'Maria Lopez' listed", ib.includes("Maria Lopez"));
  check("Inbox: 'Make it clear' button shown", ib.includes("Make it clear"));
  await page.click("text=Make it clear");
  await page.waitForSelector("text=WHAT THIS IS", { timeout: 60_000 });
  const ibRes = await bodyText(page);
  check("Inbox: clear page shows exact date 'Tuesday November 24'", ibRes.includes("Tuesday November 24"));

  // ---------- Step 2c: the reply walk (added Nov 24) ----------
  // From the inbox clear page: draft + send a reply, thinking banner up while drafting.
  await page.evaluate(() => {
    const f = document.querySelector('form[action="/reply"]') as HTMLFormElement;
    f.addEventListener("submit", (e) => e.preventDefault(), { once: true });
    f.requestSubmit();
  });
  let draftThink = true;
  try {
    await page.locator("#thinking").waitFor({ state: "visible", timeout: 3_000 });
  } catch { draftThink = false; }
  check("Reply: thinking banner shows while the AI drafts the reply", draftThink);
  await page.evaluate(() => { document.querySelectorAll("button[type=submit]").forEach((b) => { (b as HTMLButtonElement).disabled = false; }); });
  await page.click("text=Draft a reply");
  await page.waitForSelector("text=YOUR REPLY DRAFT", { timeout: 90_000 });
  const dp = await bodyText(page);
  check("Reply: draft page shows BEFORE anything is sent (Send button waits for the reader)", dp.includes("Send this reply") && dp.includes("Nothing is sent until you press Send"));
  check("Reply: draft page says who wrote it (AI pill or Rules pill)", dp.includes("AI: live model response") || dp.includes("Rules: instant answer"));
  await page.fill('textarea[name="body"]', "Hello Maria,\n\nI will attend on Tuesday November 24 at 5:15 PM and bring my photo ID.\n\nThank you,\nJose Luis");
  await page.click("text=Send this reply");
  await page.waitForSelector("text=REPLY SENT", { timeout: 90_000 });
  const rp = await bodyText(page);
  check("Reply: sent page shows the sender's real address", rp.includes("maria.lopez@example.org"));
  check("Reply: sent page shows subject 'Re: Board meeting moved'", rp.includes("Re: Board meeting moved"));
  check("Reply: sent page has the BIG 'See both emails in Mailpit' button", rp.includes("See both emails in Mailpit") && (await page.locator("a.bigbtn[href='/mailpit/']").isVisible()), "");

  // ---------- Step 2d: inbox in Spanish + the seed button (added Nov 24) ----------
  await page.goto(BASE + "/inbox?lang=es", { waitUntil: "load", timeout: 90_000 });
  const ibes = await bodyText(page);
  check("Inbox ES: 'LA BANDEJA' title shown", ibes.includes("LA BANDEJA"));
  check("Inbox ES: 'Hazlo claro' button shown", ibes.includes("Hazlo claro"));
  await page.goto(BASE + "/inbox?lang=en", { waitUntil: "load", timeout: 90_000 });
  const beforeCount = await page.locator('a.btn[href*="/inbox/clear"]').count();
  await page.click('form[action*="/inbox/seed"] button[type="submit"]');
  await page.waitForSelector("text=THE INBOX", { timeout: 30_000 });
  const afterCount = await page.locator('a.btn[href*="/inbox/clear"]').count();
  check("Inbox: seed button adds one more real email", afterCount === beforeCount + 1, `${beforeCount} -> ${afterCount}`);

  // ---------- Step 4: accessibility spot checks (on the result page) ----------
  const style = await page.evaluate(() => {
    const cs = getComputedStyle(document.body);
    return {
      backgroundColor: cs.backgroundColor,
      fontSize: parseFloat(cs.fontSize),
      textAlign: cs.textAlign,
    };
  });
  check(
    "A11y: body background is cream rgb(255, 246, 214)",
    style.backgroundColor === "rgb(255, 246, 214)",
    `actual=${style.backgroundColor}`
  );
  check(
    "A11y: body font-size at least 20px",
    style.fontSize >= 20,
    `actual=${style.fontSize}px`
  );
  check(
    "A11y: text is left-aligned",
    style.textAlign === "left" || style.textAlign === "start",
    `actual=${style.textAlign} (start = left for left-to-right text)`
  );

  // ---------- Step 2e: bulk clear + the API (added Nov 26) ----------
  // The bulk button is CLICKED, never URL-typed - the path a person walks.
  await page.click('a[href="/bulk"]');
  await page.waitForLoadState("load");
  const bulkLand = await bodyText(page);
  check("Bulk: nav link lands on the bulk page with the big button", bulkLand.includes("CLEAR THE WHOLE INBOX") && (await page.locator('form[action="/bulk/clear"] button[type="submit"]').count()) === 1);
  await page.click('form[action="/bulk/clear"] button[type="submit"]');
  await page.waitForSelector("text=EVERYTHING YOU MUST DO", { timeout: 300_000 });
  const bulkDone = await bodyText(page);
  check("Bulk: one press clears the inbox - combined list + Maria's card", bulkDone.includes("EVERYTHING YOU MUST DO") && bulkDone.includes("Maria Lopez"));
  const apiResp = await page.request.post(BASE + "/api/clear", { data: { text: "The form is due 11/24/2026. Please reply.", sender: "Pat Lee", subject: "Form", lang: "en" } });
  const apiJson = await apiResp.json();
  check("API: POST /api/clear returns JSON with the exact date", apiResp.status() === 200 && Array.isArray(apiJson.dates_numbers) && apiJson.dates_numbers.includes("11/24/2026"));
  const apiBad = await page.request.post(BASE + "/api/clear", { data: { sender: "Pat Lee" } });
  check("API: missing text -> 400 JSON error", apiBad.status() === 400);
  const apiFol = await page.request.get(BASE + "/api/followups");
  const folJson = await apiFol.json();
  check("API: follow-ups JSON never carries an address field", apiFol.status() === 200 && (folJson.followups || []).every((i: any) => !("addr" in i)));

  // ---------- Step 3: follow-ups page ----------
  await page.click('a[href="/followups"]');
  await page.waitForLoadState("load");
  const fol = await bodyText(page);
  check("Follow-ups: 'Demo entries' label visible", fol.includes("Demo entries"));
  check(
    "Follow-ups: test entry for Maria Lopez was remembered",
    fol.includes("Maria Lopez")
  );

  await page.screenshot({ path: path.join(HERE, "followups.png"), fullPage: true });
  check("Follow-ups: screenshot saved", fs.existsSync(path.join(HERE, "followups.png")), "followups.png");

  await browser.close();
  if (relay) relay.server.close();

  // ---------- Report ----------
  const passed = results.filter((r) => r.ok).length;
  const lines = [
    `ClearDay Playwright test — ${new Date().toISOString()}`,
    `Target: ${BASE}/`,
    "",
    ...results.map(
      (r) => `${r.ok ? "PASS" : "FAIL"}  ${r.name}${r.detail ? " — " + r.detail : ""}`
    ),
    "",
    `TOTAL: ${passed}/${results.length} passed`,
  ];
  fs.writeFileSync(path.join(HERE, "results.log"), lines.join("\n") + "\n");
  console.log(`\nTOTAL: ${passed}/${results.length} passed`);
  process.exit(passed === results.length ? 0 : 1);
}

main().catch((e) => {
  console.error("ERROR", e);
  fs.writeFileSync(
    path.join(HERE, "results.log"),
    `ClearDay Playwright test — ${new Date().toISOString()}\nERROR: ${e}\n`
  );
  process.exit(2);
});
