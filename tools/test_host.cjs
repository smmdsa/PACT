// Integration harness: real Wasm/Canvas; minimal DOM adapter, not a real browser.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const {createCanvas,ImageData}=require('@napi-rs/canvas');
class Classes{constructor(){this.values=new Set()}add(v){this.values.add(v)}remove(v){this.values.delete(v)}toggle(v,on){if(on===undefined)on=!this.values.has(v);on?this.add(v):this.remove(v)}contains(v){return this.values.has(v)}}
class Element{constructor(){this.classList=new Classes();this.dataset={};this.textContent='';this.children={}}set innerHTML(value){this.html=value;this.firstChild=new Element()}get innerHTML(){return this.html}querySelector(key){return this.children[key]||(this.children[key]=new Element())}setPointerCapture(){}click(){this.onclick?.()} }
const elements=Object.fromEntries(['overlay','lives','gems','checkpoint','boss','runtime','time','pause','sound','source','error'].map(id=>['#'+id,new Element()]));
elements['#game']=createCanvas(480,270);elements['#atlas']=createCanvas(128,32);
const touch=['left','right','up','down','jump','action'].map(action=>{const e=new Element();e.dataset.action=action;return e});
const events={};let nextFrame,now=0;
const doc={hidden:false,querySelector:id=>elements[id],querySelectorAll:()=>touch,createElement:tag=>tag==='canvas'?createCanvas(8,8):new Element()};
const fakeAudio=()=>({state:'running',currentTime:0,resume(){},createOscillator(){return {frequency:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){},start(){},stop(){}}},createGain(){return {gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}},connect(){}}}});
const window={addEventListener(id,fn){events[id]=fn},AudioContext:function(){return fakeAudio()}};
const context=vm.createContext({window,document:doc,WebAssembly,Uint8Array,Uint8ClampedArray,DataView,ImageData,Set,Map,Math,Number,Object,String,Boolean,Array,Blob,URL,TextDecoder,console,atob,performance:{now:()=>now},requestAnimationFrame:fn=>{nextFrame=fn},setTimeout});
const html=fs.readFileSync(process.argv[2]||'build/Alien-Harvest-PACT.html','utf8');
for(const code of [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(match=>match[1]))new vm.Script(code).runInContext(context);
(async()=>{
  for(let n=0;n<100&&!window.PACTGame;n++)await new Promise(resolve=>setTimeout(resolve,5));
  assert(window.PACTGame,'Host started');const game=window.PACTGame;
  assert.equal(game.get('game.phase'),0);elements['#overlay'].firstChild.querySelector('button').click();assert.equal(game.get('game.phase'),1);
  const event=code=>({code,repeat:false,preventDefault(){}});events.keydown(event('ArrowRight'));events.keydown(event('KeyD'));events.keyup(event('ArrowRight'));
  const start=game.get('player.x');for(let n=0;n<10;n++){now+=17;nextFrame(now)}assert(game.get('player.x')>start,'Equivalent key remains held');events.keyup(event('KeyD'));
  game.pause(true);game.restart();game.step({right:1},30);assert(game.get('player.x')>48*256);
  const left=touch.find(b=>b.dataset.action==='left');left.onpointerdown({pointerId:2,preventDefault(){}});game.pause(false);now+=17;nextFrame(now);left.onpointerup({pointerId:2});game.pause(true);
  game.restart();for(let n=0;n<800&&game.get('game.phase')===1;n++)game.step({right:1});assert.equal(game.get('game.phase'),3,'Ordinary input path reaches defeat');
  elements['#overlay'].firstChild.querySelector('button').click();assert.equal(game.get('game.phase'),1);assert.equal(game.get('player.lives'),3);
  game.pause(true);game.restart();const replay=JSON.parse(fs.readFileSync('build/playthrough.json'));for(const input of replay.inputs)game.step(input);assert.equal(game.get('game.phase'),2,'Replay reaches victory through inputs');assert.equal(game.get('game.gems'),3);assert.equal(game.get('enemy.health',5),0);
  if(process.argv[3])fs.writeFileSync(process.argv[3],elements['#game'].toBuffer('image/png'));
  console.log(JSON.stringify({status:'passed',adapter:'Node minimal DOM + real native Canvas',start:true,keyboard:true,touch:true,defeat:true,restart:true,victory:true,gems:game.get('game.gems'),lives:game.get('player.lives')}));
})().catch(e=>{console.error(e);process.exitCode=1});
