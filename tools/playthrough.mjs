import fs from 'node:fs';
const manifest=JSON.parse(fs.readFileSync(process.argv[3]));
const {instance}=await WebAssembly.instantiate(fs.readFileSync(process.argv[2]),{});
const memory=new DataView(instance.exports.memory.buffer),L=manifest.layout;
const get=(id,i=0)=>memory.getInt32(L[id].offset+i*4,true);
const setInput=(values)=>{for(const id of ['left','right','up','down','jump','action','start'])memory.setInt32(L['input.'+id].offset,values[id]?1:0,true)};
const step=(v)=>{setInput(v);instance.exports['game.tick']()};
instance.exports['game.init']();step({start:1});
const trace=[],inputs=[];let cooldown=0,prevLives=3;
for(let tick=0;tick<12000&&get('game.phase')===1;tick++){
  const x=get('player.x')/256,y=get('player.y')/256,ground=get('player.grounded'),carried=get('player.carried');
  const bossX=get('enemy.x',5)/256,bossAlive=get('enemy.alive',5);
  let v={right:1};cooldown=Math.max(0,cooldown-1);
  if(bossAlive&&x>2400){
    if(carried<0){
      let closest=-1,distance=Infinity;
      for(let i=6;i<9;i++)if(get('item.mode',i)===0){const d=Math.abs(get('item.x',i)/256-x);if(d<distance){distance=d;closest=i}}
      if(closest>=0){const target=get('item.x',closest)/256;v={left:x>target+8,right:x<target-8};if(distance<20&&Math.abs(get('item.y',closest)/256-y)<32&&!cooldown){v.action=1;cooldown=12}}
      else v={};
    }else{
      const distance=bossX-x;
      v={right:distance>72,left:distance<45};
      if(distance>=45&&distance<=90&&ground&&!cooldown){if(get('player.facing')<0)v.right=1;else{v.action=1;cooldown=20}}
    }
  }
  if(ground){
    const dir=v.left?-1:1;
    const edge=x+(dir>0?20:-8),tileX=Math.floor(edge/16);
    if((v.right||v.left)&&tileX>=0&&tileX<176&&get('level.tiles',14*176+tileX)===0)v.jump=1;
    if((v.right||v.left)&&tileX>=0&&tileX<176&&get('level.tiles',Math.floor((y+12)/16)*176+tileX)===1)v.jump=1;
    for(let i=0;i<5;i++)if(get('enemy.alive',i)&&Math.abs(get('enemy.x',i)/256-x)<23)v.jump=1;
    if(get('game.gems')<3)for(let i=0;i<7;i++)if(get('gem.active',i)&&get('gem.y',i)/256>=180&&Math.abs(get('gem.x',i)/256-x)<13)v.jump=1;
  }
  if(!ground&&get('player.vy')>0&&v.right){const here=Math.floor((x+4)/16),ahead=Math.floor((x+20)/16);if(here>=0&&ahead<176&&get('level.tiles',14*176+here)===1&&get('level.tiles',14*176+ahead)===0)v.right=0}
  step(v);inputs.push(v);
  if(tick%240===0||get('player.lives')!==prevLives){trace.push({tick,x:Math.round(x),y:Math.round(y),lives:get('player.lives'),gems:get('game.gems'),boss:get('enemy.health',5),carried});prevLives=get('player.lives')}
}
const result={phase:get('game.phase'),ticks:get('game.tick'),x:get('player.x')/256,lives:get('player.lives'),gems:get('game.gems'),boss:get('enemy.health',5),checkpoint:get('game.checkpoint'),trace};
console.log(JSON.stringify(result,null,2));
if(process.argv[4])fs.writeFileSync(process.argv[4],JSON.stringify({format:'pact.input-replay/0.1.0',inputs,result}));
if(result.phase!==2)process.exitCode=1;
