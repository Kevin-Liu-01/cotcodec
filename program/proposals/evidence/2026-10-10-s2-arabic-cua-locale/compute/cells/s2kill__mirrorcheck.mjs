import { chromium } from '/Users/kevinliu/repos/Relay/node_modules/playwright-core/index.mjs';
const app='http://127.0.0.1:14318', control='http://127.0.0.1:14319', token='REDACTED_LOCAL_TEST_TOKEN';
const OUT='/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/s2kill';
const W=1440;
async function boxes(page){
  return page.evaluate(()=>{
    const out=[]; const els=[...document.querySelectorAll('button,a,input,textarea,[role=button],[role=tab],[role=menuitem],[contenteditable=true]')];
    els.forEach((e,i)=>{const b=e.getBoundingClientRect(); if(b.width&&b.height&&b.bottom>0&&b.top<innerHeight) out.push({i,label:(e.getAttribute('aria-label')||e.textContent||'').trim().slice(0,40),x:b.x,y:b.y,w:b.width,h:b.height});});
    return out;});
}
const browser = await chromium.launch({headless:true});
for (const hover of [false,true]) {
  const s = await (await fetch(control+'/sessions',{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json'},body:JSON.stringify({taskId:'release-sync',seed:42})})).json();
  const ctx = await browser.newContext({viewport:{width:W,height:900},locale:'en-US',timezoneId:'UTC'});
  const page = await ctx.newPage();
  await page.goto(`${app}/s/${s.token}`);
  await page.getByRole('textbox',{name:'Search Northstar'}).waitFor({timeout:10000});
  const msg = page.locator('[id^="msg-"]').nth(1);
  if (hover) await msg.hover();
  await page.waitForTimeout(300);
  const ltr = await boxes(page);
  await page.evaluate(()=>{document.documentElement.dir='rtl';});
  if (hover) { await page.mouse.move(5,5); await page.waitForTimeout(100); await msg.hover(); }
  await page.waitForTimeout(300);
  const rtl = await boxes(page);
  if (hover) await page.screenshot({path:`${OUT}/relay-rtl-hover-probe.png`});
  const byI = new Map(rtl.map(b=>[b.i,b]));
  let n=0, mirrored=0, bad=[];
  for (const a of ltr){ const b=byI.get(a.i); if(!b) continue; n++;
    const expectX = W - a.x - a.w; const ok = Math.abs(b.x-expectX) <= 24 && Math.abs(b.y-a.y)<=24;
    if(ok) mirrored++; else bad.push(`${a.label} ltr.x=${a.x.toFixed(0)} rtl.x=${b.x.toFixed(0)} expected=${expectX.toFixed(0)} dy=${(b.y-a.y).toFixed(0)}`);
  }
  console.log(`hover=${hover}: interactive elements compared ${n}; mirrored within 24px ${mirrored}; not mirrored ${n-mirrored}`);
  console.log(bad.slice(0,25).join('\n'));
  await ctx.close();
}
await browser.close();
