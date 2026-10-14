import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const site=path.join(root,'site-output');
const output=path.join(root,'build/browser-smoke');
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
const report={format:'pact.browser-smoke/0.1.0',started_at_utc:new Date().toISOString(),
  engine:'chromium',browser_version:browser.version(),playwright_version:'1.61.1',
  scope:'Headless local-file smoke: docs layout, game rendering, keyboard/pointer controls and pause. No visual baseline or audio-quality grading.',
  game_html_sha256:createHash('sha256').update(await fs.readFile(path.join(site,'game.html'))).digest('hex'),
  checks:[]};
const record=(name, details={})=>report.checks.push({name,status:'passed',...details});
try {
  for(const viewport of [{width:1400,height:1000},{width:390,height:844}]) {
    const mobile=viewport.width===390;
    const context=await browser.newContext({viewport,hasTouch:mobile,isMobile:mobile});
    const page=await context.newPage();
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
    await page.goto(pathToFileURL(path.join(site,'syntax.html')).href);
    await page.locator('article.markdown table').first().waitFor({state:'visible'});
    const layout=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
    assert(layout.scroll<=layout.width+1,`Docs overflow at ${viewport.width}: ${layout.scroll}`);
    await page.screenshot({path:path.join(output,`docs-${viewport.width}.png`),fullPage:true});
    record('docs-layout',{viewport,document_width:layout.scroll});

    await page.goto(pathToFileURL(path.join(site,'game.html')).href);
    await page.waitForFunction(()=>Boolean(window.PACTGame));
    assert.equal(await page.evaluate(()=>PACTGame.get('game.phase')),0);
    const paletteSize=await page.evaluate(()=>{
      const canvas=document.querySelector('#game');
      const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      const colors=new Set();
      for(let i=0;i<pixels.length;i+=4)colors.add(`${pixels[i]},${pixels[i+1]},${pixels[i+2]},${pixels[i+3]}`);
      return colors.size;
    });
    assert(paletteSize>8,'Canvas has no rendered scene');
    record('canvas-rendered',{viewport,distinct_colors:paletteSize});
    await page.locator('#play').click();
    await page.waitForFunction(()=>PACTGame.get('game.phase')===1);
    const initial=await page.evaluate(()=>PACTGame.get('player.x'));
    if(mobile) {
      const button=page.locator('[data-action="right"]');
      const bounds=await button.boundingBox();assert(bounds);
      await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
      await page.mouse.down();
      await page.waitForFunction(x=>PACTGame.get('player.x')>x,initial);
      await page.mouse.up();
    } else {
      await page.keyboard.down('ArrowRight');
      await page.waitForFunction(x=>PACTGame.get('player.x')>x,initial);
      await page.keyboard.up('ArrowRight');
    }
    record(mobile?'pointer-movement':'keyboard-movement',{viewport});
    if(mobile) {
      await page.waitForFunction(()=>PACTGame.get('player.grounded')===1);
      const y=await page.evaluate(()=>PACTGame.get('player.y'));
      const bounds=await page.locator('[data-action="jump"]').boundingBox();assert(bounds);
      await page.touchscreen.tap(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
      await page.waitForFunction(value=>PACTGame.get('player.y')<value,y);
      record('touch-jump',{viewport});
    }
    await page.locator('#pause').click();
    const snapshot=await page.evaluate(()=>({x:PACTGame.get('player.x'),tick:PACTGame.get(PACTGame.manifest.presentation.clock)}));
    await page.waitForTimeout(150);
    assert.deepEqual(await page.evaluate(()=>({x:PACTGame.get('player.x'),tick:PACTGame.get(PACTGame.manifest.presentation.clock)})),snapshot);
    record('pause-freezes-state',{viewport});
    await page.screenshot({path:path.join(output,`game-${viewport.width}.png`),fullPage:true});
    assert.deepEqual(errors,[],`Browser errors at ${viewport.width}`);
    record('no-browser-errors',{viewport});
    await context.close();
  }
  report.status='passed';
} catch(error) {
  report.status='failed';report.failure=String(error.stack||error);process.exitCode=1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(output,'result.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}
