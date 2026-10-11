// S2 render-oracle validation fixture (D68 repair). Renders a mock office-application window in
// four cells (en, ar-LTR, en-RTL, ar-RTL) under several fixture variants with known properties,
// in Chromium (Blink lays out bidirectional text with ICU's ubidi, the library LibreOffice's VCL
// calls with an explicit paragraph level). Writes one PNG and one element list per (variant,
// cell, render) for oracle.py. No network; the page is set from a string.
//
// Variants:
//   coupled     paragraph direction of every UI string follows the layout (VCL's behaviour when
//               the UI is mirrored: outdev.cxx sets BiDiRtl, ImplLayoutArgs passes level 1)
//   isolated    the same, but every catalog string is wrapped in FSI ... PDI (U+2068 ... U+2069),
//               the catalog-level isolation registered for the OSWorld fixture
//   plaintext   CSS unicode-bidi: plaintext on text widgets (the web-chrome decoupling)
//   halfmirror  isolated, but the sidebar stays on the right in RTL (negative control for O3)
//   reorder     isolated, but the toolbar's visual order is reversed in the Arabic cells (O4)
//   drift       isolated, but one content cell differs in ar-RTL (negative control for O5)
//   composite   isolated, plus one status field built in code from an isolated catalog string,
//               a code literal ": " and a number (a residual leak isolation cannot remove)
//
// Usage: PLAYWRIGHT_CORE=/path/to/playwright-core/index.mjs node fixture.mjs <outdir>
// Playwright is resolved from PLAYWRIGHT_CORE (a path to playwright-core's index.mjs) or the module path;
// this run used a local playwright-core install and its cached Chromium (version recorded in browser.json).
const { chromium } = await import(process.env.PLAYWRIGHT_CORE || 'playwright-core');
import fs from 'node:fs';
import path from 'node:path';

const out = process.argv[2];
fs.mkdirSync(out, { recursive: true });

const CAT = {
  menu: [['File', 'ملف'], ['Edit', 'تحرير'], ['View', 'عرض'], ['Insert', 'إدراج'], ['Format', 'تنسيق'], ['Help', 'مساعدة']],
  toolbar: [['Save As…', 'حفظ باسم…'], ['Export as PDF…', 'تصدير بصيغة PDF…'], ['Zoom: 100%', 'تكبير: 100%'], ['Find & Replace', 'بحث واستبدال'], ['Undo (Ctrl+Z)', 'تراجع (Ctrl+Z)']],
  sidebar: [['Properties', 'خصائص'], ['Character', 'حرف'], ['Font size: 12 pt', 'حجم الخط: 12 نقطة'], ['Bold', 'عريض']],
  status: [['Sheet 1 of 3', 'ورقة 1 من 3'], ['Default', 'افتراضي'], ['English (USA)', 'الإنجليزية (الولايات المتحدة)'], ['About LibreOffice', 'حول LibreOffice']],
  words: ['Words', 'كلمات'],
};
const FSI = '⁨';
const PDI = '⁩';

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
}

function page(variant, text, dir) {
  const ar = text === 'ar';
  const iso = variant !== 'coupled' && variant !== 'plaintext';
  const s = (pair) => {
    const v = pair[ar ? 1 : 0];
    return esc(iso ? FSI + v + PDI : v);
  };
  const item = (p, role, label, cls) => `<span class="w t ${cls || ''}" data-path="${p}" data-role="${role}">${label}</span>`;
  const menu = CAT.menu.map((m, i) => item(`win/menubar/m${i}`, 'menu', s(m))).join('');
  const tb = CAT.toolbar.map((m, i) => item(`win/toolbar/b${i}`, 'push button', s(m), 'btn')).join('');
  const side = CAT.sidebar.map((m, i) => item(`win/main/sidebar/p${i}`, i < 2 ? 'heading' : 'label', s(m))).join('');
  let status = CAT.status.map((m, i) => item(`win/status/s${i}`, 'label', s(m))).join('');
  if (variant === 'composite') status += item('win/status/s9', 'label', s(CAT.words) + ': 1,024');
  const cellv = variant === 'drift' && text === 'ar' && dir === 'rtl' ? '1,351' : '1,350';
  const reorder = variant === 'reorder' && ar ? '.toolbar { flex-direction: row-reverse; justify-content: flex-end; }' : '';
  const half = variant === 'halfmirror' && dir === 'rtl' ? '.main { flex-direction: row-reverse; }' : '';
  const plain = variant === 'plaintext' ? '.t { unicode-bidi: plaintext; }' : '';
  return `<!doctype html><html lang="${ar ? 'ar' : 'en'}"><head><meta charset="utf-8"><style>
  html, body { margin: 0; padding: 0; background: #ffffff; }
  * { box-sizing: border-box; -webkit-font-smoothing: antialiased; }
  body { font: 15px "Arial", "Geeza Pro", sans-serif; color: #111111; }
  .win { position: absolute; left: 0; top: 0; width: 1280px; height: 720px; background: #f4f4f4; }
  .menubar, .toolbar, .status { display: flex; gap: 18px; padding-inline-start: 12px; align-items: center; }
  .menubar { height: 30px; background: #e9e9e9; }
  .toolbar { height: 44px; gap: 10px; }
  .btn { border: 1px solid #b0b0b0; background: #fdfdfd; padding: 4px 8px; }
  .main { display: flex; height: 586px; }
  .canvas { flex: 0 0 1000px; background: #ffffff; border: 1px solid #cccccc; padding: 20px; }
  .sidebar { flex: 0 0 280px; display: flex; flex-direction: column; gap: 14px; padding: 16px; background: #ececec; }
  .status { height: 60px; background: #e2e2e2; }
  .w { display: inline-block; white-space: pre; }
  .sidebar .w { align-self: flex-start; }
  table { border-collapse: collapse; } td { border: 1px solid #999999; padding: 4px 12px; font: 15px "Arial", sans-serif; }
  ${reorder} ${half} ${plain}
  </style></head><body>
  <div class="win" id="win" dir="${dir}" data-path="win" data-role="frame">
    <div class="menubar" data-path="win/menubar" data-role="menu bar">${menu}</div>
    <div class="toolbar" data-path="win/toolbar" data-role="tool bar">${tb}</div>
    <div class="main" data-path="win/main" data-role="panel">
      <section class="canvas" dir="ltr" data-path="win/main/canvas" data-role="document frame">
        <table><tr><td>Region</td><td>Q1</td><td>Q2</td></tr><tr><td>North</td><td>1,200</td><td>${cellv}</td></tr><tr><td>South</td><td>980</td><td>1,010</td></tr></table>
      </section>
      <aside class="sidebar" data-path="win/main/sidebar" data-role="panel">${side}</aside>
    </div>
    <div class="status" data-path="win/status" data-role="status bar">${status}</div>
  </div></body></html>`;
}

async function render(p, variant, text, dir, tag, shift = 0) {
  await p.setContent(page(variant, text, dir).replace('<div class="win"', shift ? `<div style="transform: translateX(${shift}px)" class="win"` : '<div class="win"'));
  // fix every text widget's width to whole pixels so positions are integral in both directions
  await p.evaluate(() => {
    for (const el of document.querySelectorAll('.w')) {
      const w = el.getBoundingClientRect().width;
      el.style.width = Math.ceil(w) + 'px';
    }
  });
  const els = await p.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('[data-path]')) {
      const r = el.getBoundingClientRect();
      out.push({
        path: el.dataset.path,
        role: el.dataset.role,
        name: el.classList.contains('t') ? el.textContent : '',
        box: [r.x, r.y, r.width, r.height],
        text: el.classList.contains('t'),
        unit: el.dataset.path !== 'win',
      });
    }
    return out;
  });
  const base = path.join(out, `${variant}-${tag}`);
  await p.screenshot({ path: base + '.png', clip: { x: 0, y: 0, width: 1280, height: 720 } });
  fs.writeFileSync(base + '.json', JSON.stringify({ window: [0, 0, 1280, 720], content: 'win/main/canvas', elements: els }, null, 1));
}

const browser = await chromium.launch({ headless: true, args: ['--font-render-hinting=none', '--disable-lcd-text', '--force-device-scale-factor=1'] });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1, locale: 'en-US', timezoneId: 'UTC' });
const p = await ctx.newPage();
const cells = { en: ['en', 'ltr'], arL: ['ar', 'ltr'], enR: ['en', 'rtl'], arR: ['ar', 'rtl'] };
for (const variant of ['coupled', 'isolated', 'plaintext', 'halfmirror', 'reorder', 'drift', 'composite']) {
  for (const [cell, [text, dir]] of Object.entries(cells)) await render(p, variant, text, dir, cell);
}
// A/A: the isolated variant rendered a second time in a fresh page
const p2 = await ctx.newPage();
for (const [cell, [text, dir]] of Object.entries(cells)) await render(p2, 'isolated', text, dir, cell + '-AA');
// shifted A/A: the same cells moved right by 0.37 px (rasterisation at another subpixel phase)
for (const [cell, [text, dir]] of Object.entries(cells)) await render(p2, 'isolated', text, dir, cell + '-AAshift', 0.37);
const ver = browser.version();
fs.writeFileSync(path.join(out, 'browser.json'), JSON.stringify({ chromium: ver }, null, 1));
await browser.close();
console.log('rendered with Chromium', ver);
