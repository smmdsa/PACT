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
  scope:'Headless local-file smoke: catalog filtering and embedded player, docs layout, game rendering, keyboard/pointer controls and pause. No visual baseline or audio-quality grading.',
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
    await page.goto(pathToFileURL(path.join(site,'demos.html')).href);
    const games=page.locator('[data-kind="playable"]:visible');
    assert.equal(await games.count(),4);
    await page.getByLabel('Search demos and examples').fill('astra');
    assert.equal(await games.count(),1);
    assert.match(await games.innerText(),/GPT-6 Astra/);
    await page.getByLabel('Search demos and examples').fill('no-such-demo-xyz');
    assert.equal(await page.locator('#catalog-empty').isVisible(),true);
    await page.getByLabel('Search demos and examples').fill('');
    await page.getByRole('button',{name:'Source examples',exact:true}).click();
    assert.equal(await games.count(),0);
    assert((await page.locator('[data-kind="source"]:visible').count())>0);
    await page.getByRole('button',{name:'Playable',exact:true}).click();
    assert.equal(await games.count(),4);
    const catalogLayout=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
    assert(catalogLayout.scroll<=catalogLayout.width+1,`Catalog overflow at ${viewport.width}`);
    // Only the authored PACT demo executes in this worker; GPT outputs use the isolated Docker verifier.
    await page.locator('[data-demo="alien-harvest"]').click();
    await page.frameLocator('#demo-frame').locator('#play').waitFor({state:'visible'});
    assert.equal(await page.locator('#demo-title').innerText(),'Alien Harvest');
    assert.equal(await page.locator('#demo-frame').getAttribute('sandbox'),'allow-scripts');
    await page.getByRole('button',{name:'Close demo',exact:true}).click();
    assert.equal(await page.locator('#demo-frame').getAttribute('src'),null);
    assert.equal(await page.locator('#demo-player').isVisible(),false);
    record('catalog-search-filter-layout-and-player',{viewport});

    await page.goto(pathToFileURL(path.join(site,'orbita.html')).href);
    await page.locator('body[data-ready="true"]').waitFor();
    assert.equal(await page.locator('#remaining').innerText(),'6');
    const selectIdea=async index=>page.locator(`#idea-nodes [data-idea="${index}"]`).click();
    await selectIdea(4);
    assert.equal(await page.locator('#idea-title').innerText(),'Crear en común');
    await page.locator('#invest').click();
    assert.equal(await page.locator('#remaining').innerText(),'5');
    assert.equal(await page.locator('#idea-level').innerText(),'1 / 3');
    await page.getByRole('button',{name:'Entrelazar',exact:true}).click();
    assert.equal(await page.locator('#space').getAttribute('data-lens'),'2');
    await page.locator('#undo').click();
    assert.equal(await page.locator('#remaining').innerText(),'6');
    await page.locator('#redo').click();
    assert.equal(await page.locator('#remaining').innerText(),'5');
    await page.locator('#undo').click();await selectIdea(2);await page.locator('#invest').click();
    assert.equal(await page.locator('#redo').isDisabled(),true);
    await page.locator('#list-toggle').click();
    await page.locator('#idea-list [data-idea="5"]').click();
    assert.equal(await page.locator('#idea-title').innerText(),'Tecnología amable');
    await page.locator('#idea-list [data-idea="5"]').press('ArrowLeft');
    assert.equal(await page.locator('#idea-title').innerText(),'Crear en común');
    await page.locator('#about-open').click();assert.equal(await page.locator('#about').isVisible(),true);
    await page.locator('#about .dialog-close').click();
    await page.locator('#engine-open').click();
    assert.match(await page.locator('#build-evidence').innerText(),/6 casos ejecutados/);
    await page.locator('#engine .dialog-close').click();
    await page.locator('#reset').click();
    for(let i=0;i<3;i++)await page.locator('#invest').click();
    assert.equal(await page.locator('#invest').isDisabled(),true);
    await selectIdea(1);
    for(let i=0;i<3;i++)await page.locator('#invest').click();
    assert.equal(await page.locator('#remaining').innerText(),'0');
    await selectIdea(2);assert.equal(await page.locator('#invest').isDisabled(),true);
    await selectIdea(1);await page.locator('#release').click();
    assert.equal(await page.locator('#remaining').innerText(),'1');
    await page.locator('#reset').click();
    assert.equal(await page.locator('#remaining').innerText(),'6');
    assert.equal(await page.locator('#idea-title').innerText(),'Memoria viva');
    await page.locator('#list-toggle').click();
    const orbitLayout=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
    assert(orbitLayout.scroll<=orbitLayout.width+1,`Órbita overflow at ${viewport.width}`);
    await page.screenshot({path:path.join(output,`orbita-${viewport.width}.png`),fullPage:true});
    record('orbita-pact-decisions-history-budget-keyboard-dialogs-and-layout',{viewport});

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
