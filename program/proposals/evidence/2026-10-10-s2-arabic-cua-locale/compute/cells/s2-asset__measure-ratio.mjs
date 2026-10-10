import { chromium } from '/Users/kevinliu/repos/Relay/node_modules/playwright-core/index.mjs';
import { readFileSync, writeFileSync } from 'node:fs';
const chrome = new Set(JSON.parse(readFileSync(process.argv[2], 'utf8')));
const tasks = ['channel-topic','thread-reply','edit-message','incident-triage','delete-draft','handoff-dm','release-sync','incident-closeout','saved-cleanup','decision-record','handoff-repair','qa-signoff','publish-update','oncall-briefing','thread-repair','pin-refresh','design-handoff','release-retrospective'];
const headers = { authorization: 'Bearer REDACTED_LOCAL_TEST_TOKEN', 'content-type': 'application/json' };
const browser = await chromium.launch({ headless: true });
const rows = [];
for (const taskId of tasks) {
  const r = await fetch('http://127.0.0.1:4321/sessions', { method: 'POST', headers, body: JSON.stringify({ taskId, seed: 42 }) });
  const s = await r.json();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'en-US', timezoneId: 'UTC' });
  const page = await ctx.newPage();
  await page.goto(`http://127.0.0.1:4320/s/${s.token}`);
  await page.getByRole('textbox', { name: 'Search Northstar' }).waitFor({ timeout: 10000 });
  await page.waitForTimeout(300);
  const lines = await page.evaluate(() => {
    const out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const vis = (el, r) => { if (!el) return false; const cs = getComputedStyle(el); if (cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0) return false; return r.width>0&&r.height>0&&r.bottom>0&&r.right>0&&r.top<innerHeight&&r.left<innerWidth; };
    while (w.nextNode()) { const n = w.currentNode; const t = n.textContent.replace(/\s+/g,' ').trim(); if (!t || ['SCRIPT','STYLE'].includes(n.parentElement?.tagName)) continue; const range=document.createRange(); range.selectNodeContents(n); if ([...range.getClientRects()].some(r=>vis(n.parentElement,r))) out.push(t); }
    const ph = [...document.querySelectorAll('input[placeholder],textarea[placeholder]')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.top<innerHeight&&!e.value}).map(e=>e.placeholder);
    return { lines: out, placeholders: ph };
  });
  let c = 0, t = 0, cl = 0;
  const all = [...lines.lines, ...lines.placeholders];
  for (const l of all) { const n = l.length; t += n; if (chrome.has(l) || lines.placeholders.includes(l)) { c += n; cl++; } }
  rows.push({ taskId, visibleChars: t, chromeChars: c, chromeShare: +(c / t).toFixed(3), nodes: all.length, chromeNodes: cl });
  await ctx.close();
  await fetch(`http://127.0.0.1:4321/sessions/${s.token}`, { method: 'DELETE', headers });
}
await browser.close();
const tc = rows.reduce((a, r) => a + r.chromeChars, 0), tt = rows.reduce((a, r) => a + r.visibleChars, 0);
writeFileSync(process.argv[3], JSON.stringify({ rows, pooledChromeShare: +(tc / tt).toFixed(3) }, null, 1));
console.log(JSON.stringify({ pooledChromeShare: +(tc / tt).toFixed(3), min: Math.min(...rows.map(r=>r.chromeShare)), max: Math.max(...rows.map(r=>r.chromeShare)) }));
