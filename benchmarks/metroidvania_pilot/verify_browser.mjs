import { chromium } from 'playwright';
import { createRequire } from 'node:module';
import { writeFile, readFile } from 'node:fs/promises';

// This is exploratory observation, not authentication or universal correctness.
// The candidate controls METROID_TEST and can forge its reported observations.
// Chromium uses --no-sandbox because this worker runs as an unprivileged UID in
// an externally isolated, networkless, read-only Docker container. The host must
// enforce CPU/memory/PID/tmp/output/wall limits; this script is not a sandbox.
const require = createRequire(import.meta.url);
const output = {
  format: 'pact.metroid-browser-observations/0.1', checks: [],
  runtime: { chromium: 'unavailable', playwright: require('playwright/package.json').version },
  screenshots: [], page_errors: [],
};
const bounded = value => String(value).slice(0, 500);
const result = (id, pass, detail) => output.checks.push({ id, pass: !!pass, detail: bounded(detail) });
let browser;
let screenshotBytes = 0;
async function resources(id) {
  const values={};
  for(const name of ['pids.current','pids.max','pids.events','memory.current','memory.events']) {
    try{values[name]=(await readFile('/sys/fs/cgroup/'+name,'utf8')).trim();}catch{values[name]='unavailable';}
  }
  result('verifier_resources_'+id,true,JSON.stringify(values));
}
async function deadline(promise, ms = 5000) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`operation exceeded ${ms}ms`)), ms);
  })]); } finally { clearTimeout(timer); }
}
async function observe(id, fn) {
  try { const r = await fn(); result(id, r.pass, r.detail); }
  catch (error) { result(id, false, error.message); }
}
async function newPage(test = true) {
  const page = await browser.newPage({ viewport: { width: 960, height: 540 }, serviceWorkers: 'block' });
  page.setDefaultTimeout(5000);
  // Context routing covers a popup's first request as well as this page.
  await page.context().route('**/*', route => route.request().url().startsWith('file:') ? route.continue() : route.abort());
  page.on('popup', popup => { popup.close().catch(() => {}); });
  page.on('dialog', dialog => { dialog.dismiss().catch(() => {}); });
  page.on('pageerror', error => {
    if (output.page_errors.length < 10) output.page_errors.push(bounded(error.message));
  });
  try{await page.goto(`file:///tmp/candidate.html${test ? '?test=1' : ''}`, { waitUntil: 'load', timeout: 5000 });}
  catch(error){await resources('navigation_failure');throw error;}
  return page;
}
async function screenshot(page, id) {
  try {
    const png = await deadline(page.screenshot({ type: 'png', timeout: 5000 }));
    // Omit unusually large images; never let candidate imagery flood stdout.
    if (output.screenshots.length < 2 && png.length <= 220000 && screenshotBytes + png.length <= 440000) {
      screenshotBytes += png.length;
      output.screenshots.push({ id, png_base64: png.toString('base64') });
    }
  } catch (error) { result(`screenshot_${id}`, false, error.message); }
}

// Every route advances ordinary inputs only. Snapshot is sampled after every
// frame, with explicit caps, so a failed mechanic yields a bounded observation.
async function action(page, name) {
  return deadline(page.evaluate(name => {
    const api = window.METROID_TEST;
    if (!api || !['reset', 'step', 'snapshot'].every(k => typeof api[k] === 'function')) throw Error('missing METROID_TEST interface');
    let s = api.snapshot();
    const snap = () => { s = api.snapshot(); return s; };
    const frame = (input = {}) => { api.step(1, input); return snap(); };
    const frames = (n, input = {}) => { for (let i = 0; i < n; i++) frame(input); return s; };
    const reset = () => { api.reset(); return snap(); };
    const until = (predicate, input, cap = 300) => {
      for (let i = 0; i < cap && !predicate(s); i++) frame(input);
      if (!predicate(s)) throw Error(`route cap: room=${s.room} x=${s.x} y=${s.y} deaths=${s.deaths}`);
      return s;
    };
    const walk = (x, cap = 300) => {
      let stuck = 0, last = s.x;
      for (let i = 0; i < cap && Math.abs(s.x - x) > 4; i++) {
        const input = { left: s.x > x, right: s.x < x, attack: true };
        if (stuck > 12 && s.onGround) { input.jump = true; stuck = 0; }
        frame(input);
        stuck = Math.abs(s.x - last) < 0.1 ? stuck + 1 : 0; last = s.x;
      }
      if (Math.abs(s.x - x) > 4) throw Error(`walk cap: target=${x} room=${s.room} x=${s.x}`);
      return s;
    };
    const boots = () => {
      reset(); until(v => v.room === 'west', { left: true, attack: true });
      until(v => v.boots === true, { left: true, attack: true });
      if (s.room !== 'west') throw Error('boots were not acquired in west');
    };
    const hub = () => {
      if (s.room === 'west') until(v => v.room === 'hub', { right: true, attack: true });
      if (s.room !== 'hub') throw Error(`expected hub, got ${s.room}`);
      walk(480);
    };
    const lower = () => { hub(); frame({ down: true }); if (s.room !== 'lower') throw Error('Down did not enter lower'); };
    const compact = () => ({ room:s.room, x:s.x, y:s.y, hp:s.hp, boots:s.boots, key:s.key, bossHp:s.bossHp, won:s.won, deaths:s.deaths });
    const answer = (pass, detail) => ({ pass, detail: typeof detail === 'string' ? detail : JSON.stringify(detail) });
    if (name === 'boot') {
      reset();
      const keys = 'room x y vx vy hp maxHp boots key bossHp won deaths checkpoint visited tick onGround jumpsUsed'.split(' ');
      const valid = keys.every(k => Object.hasOwn(s, k)) && Array.isArray(s.visited) && s.visited.length === 1 && s.visited[0] === 'hub' && s.room === 'hub' && s.x === 480 && s.y === 468 && s.hp === 3 && s.maxHp === 3 && s.boots === false && s.key === false && s.won === false && s.deaths === 0;
      const a = api.snapshot(), b = api.snapshot();
      return answer(valid && a !== b && Object.getPrototypeOf(a) === Object.prototype, compact());
    }
    if (name === 'determinism') {
      const run = () => { reset(); const trace=[]; for(let i=0;i<80;i++) {frame({right:i<30,left:i>=50,jump:i===5,attack:true}); trace.push(JSON.stringify(s));} return trace; };
      const a=run(), b=run(); return answer(JSON.stringify(a)===JSON.stringify(b), 'Compared 80 per-frame snapshots across reset and identical inputs');
    }
    if (name === 'movement') {
      reset(); const x=s.x; frames(10,{right:true}); const moved=s.x-x; frame({jump:true});
      return answer(moved===40 && s.y<468 && s.vy<0, {moved, y:s.y,vy:s.vy});
    }
    if (name === 'air_jump_locked') {
      reset(); frame({jump:true}); frame(); const before=s.vy; frame({jump:true});
      return answer(s.jumpsUsed===1 && s.vy>before && !s.boots, {before,after:s.vy,jumpsUsed:s.jumpsUsed});
    }
    if (name === 'east_gate_locked') {
      reset(); frames(160,{right:true,attack:true}); return answer(s.room==='hub'&&!s.boots&&!s.won,compact());
    }
    if (name === 'contact_damage') {
      reset(); until(v=>v.room==='west',{left:true});
      until(v=>v.hp<3||v.deaths>0,{left:true},150);
      const damaged=s.hp; frames(20);
      return answer(damaged===2&&s.hp===2&&s.deaths===0,{damaged,after20:s.hp,deaths:s.deaths});
    }
    if (name === 'boots') { boots(); return answer(s.boots===true && !s.key && !s.won,compact()); }
    if (name === 'air_jump_unlocked') {
      frames(50); frame({jump:true}); frames(5); const before=s.vy; frame({jump:true});
      return answer(s.boots===true && s.jumpsUsed===2 && s.vy<before && s.vy<=-9, {before,after:s.vy,jumpsUsed:s.jumpsUsed});
    }
    if (name === 'vertical_exit') { frames(50); lower(); return answer(s.room==='lower'&&Math.abs(s.x-80)<=24,compact()); }
    if (name === 'pit_and_key') {
      if(s.room!=='lower') throw Error('lower route prerequisite missing');
      const deaths=s.deaths; walk(376); frame({right:true,jump:true,attack:true});
      until(v=>v.x>=520 || v.room!=='lower' || v.deaths!==deaths,{right:true,attack:true},100);
      if(s.room!=='lower'||s.deaths!==deaths) throw Error('died or left lower while crossing pit');
      until(v=>v.key===true,{right:true,attack:true},150);
      return answer(s.key===true&&s.boots===true&&s.deaths===deaths&&!s.won,compact());
    }
    if (name === 'backtracking') {
      if(s.room!=='lower'||!s.key) throw Error('key route prerequisite missing');
      frames(40); walk(520); frame({left:true,jump:true,attack:true});
      until(v=>v.x<=376 || v.room!=='lower',{left:true,attack:true},100);
      if(s.room!=='lower') throw Error('died during return pit crossing');
      walk(80); frame({up:true}); return answer(s.room==='hub'&&Math.abs(s.x-480)<=24&&s.boots&&s.key,compact());
    }
    if (name === 'sanctum_locked') {
      boots(); hub(); until(v=>v.room==='east',{right:true,attack:true}); frames(260,{right:true,attack:true});
      return answer(s.room==='east'&&s.boots&&!s.key&&!s.won,compact());
    }
    if (name === 'boss_damage') {
      if(s.room!=='hub'||!s.key) throw Error('backtracking prerequisite missing');
      until(v=>v.room==='east',{right:true,attack:true});
      until(v=>v.room==='sanctum',{right:true,attack:true});
      const initial=s.bossHp; walk(724); frames(25,{attack:true});
      return answer(initial===5&&s.bossHp<initial&&!s.won,{initial,...compact()});
    }
    if (name === 'victory') {
      if(s.room!=='sanctum') throw Error('boss route prerequisite missing');
      const notEarly=s.won===false; frames(150,{attack:true}); const defeated=s.bossHp===0, beforeExit=s.won===false;
      until(v=>v.won===true,{right:true,attack:true},100);
      return answer(notEarly&&defeated&&beforeExit&&s.won===true&&s.bossHp===0,compact());
    }
    if (name === 'full_reset') {
      reset(); const clean=()=>s.room==='hub'&&s.x===480&&s.y===468&&s.hp===3&&!s.boots&&!s.key&&!s.won&&s.deaths===0&&s.visited.length===1&&s.visited[0]==='hub';
      const afterProgress=clean(); boots(); lower();
      // Deliberate action-only fall into the pit; do not auto-jump when stuck.
      until(v=>v.x>=430||v.deaths>0,{right:true,attack:true},150);
      until(v=>v.deaths>0,{},180); const died=s.deaths===1&&s.boots===true&&s.room==='hub'&&s.hp===3&&s.visited.includes('lower');
      reset(); return answer(afterProgress&&died&&clean(),{afterProgress,observedDeath:died,...compact()});
    }
    throw Error(`unknown trusted action ${name}`);
  }, name));
}

try {
  let raw = ''; let bytes = 0;
  for await (const chunk of process.stdin) {
    bytes += chunk.length;
    if (bytes > 1450000) throw Error('stdin exceeds bounded request size');
    raw += chunk.toString('utf8');
  }
  const request = JSON.parse(raw);
  if (!request || Object.keys(request).length !== 1 || typeof request.candidate_base64 !== 'string' || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(request.candidate_base64)) throw Error('expected one canonical candidate_base64 field');
  const candidate = Buffer.from(request.candidate_base64, 'base64');
  if (!candidate.length || candidate.length > 1048576) throw Error('candidate must contain 1..1048576 bytes');
  await writeFile('/tmp/candidate.html', candidate, { mode: 0o600 });
  browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  output.runtime.chromium = browser.version();
  await writeFile('/tmp/control.html','<!doctype html><title>trusted control</title><script>window.TRUSTED_CONTROL=true</script>');
  const control = await browser.newPage();
  for (const routed of [false,true]) {
    if (routed) await control.context().route('**/*', route=>route.request().url().startsWith('file:')?route.continue():route.abort());
    let okay=false;
    try {
      await control.goto('file:///tmp/control.html?mode='+routed,{waitUntil:'load',timeout:5000});
      okay=await control.evaluate(()=>window.TRUSTED_CONTROL===true);
      result('verifier_control_'+(routed?'routed':'unrouted'),okay,'Trusted minimal file loaded');
    } catch(error) { result('verifier_control_'+(routed?'routed':'unrouted'),false,error.message); }
    if(!okay) throw Error('Trusted browser control failed before candidate evaluation');
  }
  await control.close();
  await writeFile('/tmp/canvas-control.html','<!doctype html><canvas width="960" height="540"></canvas><script>const c=document.querySelector("canvas").getContext("2d");c.shadowBlur=20;c.fillText("trusted canvas",20,40);c.fillRect(10,10,200,200);window.TRUSTED_CANVAS=true;</script>');
  const canvasControl=await browser.newPage();
  try{
    await canvasControl.goto('file:///tmp/canvas-control.html',{waitUntil:'load',timeout:5000});
    result('verifier_control_canvas',await canvasControl.evaluate(()=>window.TRUSTED_CANVAS===true),'Trusted 2D canvas rendered');
  }catch(error){result('verifier_control_canvas',false,error.message);await resources('canvas_failure');throw error;}
  await canvasControl.close();
  await resources('before_candidate');
  const page = await newPage();
  await observe('boot_interface', () => action(page,'boot'));
  await screenshot(page,'hub');
  await observe('deterministic_reset_inputs', () => action(page,'determinism'));
  await observe('contact_damage_and_invulnerability', () => action(page,'contact_damage'));
  await observe('real_keyboard_movement', async () => {
    const live = await newPage(false);
    try {
      const before=await deadline(live.evaluate(()=>window.METROID_TEST.snapshot().x));
      await live.keyboard.down('ArrowRight'); await live.waitForTimeout(200); await live.keyboard.up('ArrowRight');
      const after=await deadline(live.evaluate(()=>window.METROID_TEST.snapshot().x));
      return {pass: Number.isFinite(before)&&Number.isFinite(after)&&after>before, detail:`ArrowRight held 200ms: x=${before} -> ${after}`};
    } finally { await live.close(); }
  });
  for (const [id,name] of [
    ['movement_jump','movement'],['second_air_jump_locked','air_jump_locked'],['east_gate_before_boots','east_gate_locked'],
    ['west_boots_pickup','boots'],['second_air_jump_with_boots','air_jump_unlocked'],['vertical_room_transition','vertical_exit'],
    ['lower_pit_and_key','pit_and_key'],['return_backtracking','backtracking'],
  ]) await observe(id,()=>action(page,name));
  await observe('sanctum_gate_before_key', async()=>{
    const gate=await newPage(); try{return await action(gate,'sanctum_locked');}finally{await gate.close();}
  });
  await observe('boss_hp_decreases',()=>action(page,'boss_damage'));
  await observe('victory_after_boss_and_exit',()=>action(page,'victory'));
  await screenshot(page,'final_progress');
  await observe('full_reset_clears_inventory_deaths',()=>action(page,'full_reset'));
} catch (error) {
  result('bootstrap', false, error.message);
} finally {
  if (browser) await deadline(browser.close(),3000).catch(()=>{});
  process.stdout.write(JSON.stringify(output)+'\n');
}
