// Measure visible chrome-vs-fixture text on Relay's initial screen per task (read-only; local server).
import { chromium } from '/Users/kevinliu/repos/Relay/node_modules/playwright-core/index.mjs';
const app = 'http://127.0.0.1:14318', control = 'http://127.0.0.1:14319';
const token = 'REDACTED_LOCAL_TEST_TOKEN';
const OUT = '/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2kill';
const tasks = ['channel-topic', 'thread-reply', 'incident-triage', 'release-sync', 'saved-cleanup', 'pin-refresh'];
const browser = await chromium.launch({ headless: true });
const rows = [];
for (const taskId of tasks) {
  const s = await (await fetch(control + '/sessions', {
    method: 'POST',
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
    body: JSON.stringify({ taskId, seed: 42 }),
  })).json();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'en-US', timezoneId: 'UTC' });
  const page = await ctx.newPage();
  await page.goto(`${app}/s/${s.token}`);
  await page.getByRole('textbox', { name: 'Search Northstar' }).waitFor({ timeout: 10000 });
  await page.waitForTimeout(500);
  const r = await page.evaluate(() => {
    // visible text nodes within the viewport
    const vw = innerWidth, vh = innerHeight;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let total = 0, msg = 0, names = 0;
    const msgSel = '[id^="msg-"], [id^="thread-"]';
    const chromeSamples = [];
    while (walker.nextNode()) {
      const n = walker.currentNode, t = n.textContent.replace(/\s+/g, ' ').trim();
      if (!t) continue;
      const el = n.parentElement;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
      const range = document.createRange(); range.selectNodeContents(n);
      const b = range.getBoundingClientRect();
      if (b.width === 0 || b.height === 0 || b.bottom < 0 || b.top > vh || b.right < 0 || b.left > vw) continue;
      total += t.length;
      if (el.closest(msgSel)) msg += t.length;
      else chromeSamples.push(t);
    }
    return { total, msg, chromeSamples };
  });
  await page.screenshot({ path: `${OUT}/relay-${taskId}-en.png` });
  rows.push({ taskId, ...r });
  await ctx.close();
}
await browser.close();
for (const r of rows) {
  console.log(`${r.taskId}: visible chars ${r.total}; inside message elements ${r.msg} (${(100*r.msg/r.total).toFixed(1)}%); outside ${r.total - r.msg}`);
}
console.log('\nNon-message visible strings (first task):');
console.log(JSON.stringify(rows[0].chromeSamples));
console.log('\nNon-message visible strings (release-sync):');
console.log(JSON.stringify(rows[3].chromeSamples));
