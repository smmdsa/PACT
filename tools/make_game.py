import json
from pathlib import Path
from tools.graph_builder import Function, declare_writes

SCALE=256
COLS,ROWS=176,17


def game_document():
    constants={
        'units.pixel':256,'units.tile':4096,'player.width':3072,'player.height':3584,
        'player.speed':640,'player.jump':-1664,'world.gravity':96,'world.max_fall':2304,
        'world.width':COLS*16*256,'world.height':ROWS*16*256,'view.width':480*256,
        'enemy.count':6,'item.count':9,'gem.count':7,
    }
    cells=[]
    def cell(key,values,mutable=True):
        cells.append({'id':key,'values':list(values) if isinstance(values,(list,tuple)) else [values],'mutable':mutable})
    for key in ['left','right','up','down','jump','action','start']:cell('input.'+key,0)
    for key,value in {'game.phase':0,'game.tick':0,'game.gems':0,'game.checkpoint':0,
        'event.code':0,'camera.x':0,'checkpoint.x':48*SCALE,'checkpoint.y':210*SCALE,
        'player.x':48*SCALE,'player.y':210*SCALE,'player.vx':0,'player.vy':0,'player.facing':1,
        'player.frame':0,'player.grounded':1,'player.coyote':0,'player.jump_buffer':0,
        'player.lives':3,'player.invulnerable':0,'player.carried':-1}.items():cell(key,value)
    enemy_x=[340,720,1152,1696,2180,2630]
    cell('enemy.spawn_x',[x*SCALE for x in enemy_x],False)
    cell('enemy.x',[x*SCALE for x in enemy_x]);cell('enemy.y',[210*SCALE]*5+[200*SCALE])
    cell('enemy.vx',[128,-128,128,-128,128,64]);cell('enemy.alive',[1]*6)
    cell('enemy.health',[1]*5+[3]);cell('enemy.frame',[0]*6)
    item_x=[180,520,880,1376,1830,2250,2500,2600,2690]
    cell('item.spawn_x',[x*SCALE for x in item_x],False)
    cell('item.x',[x*SCALE for x in item_x]);cell('item.y',[216*SCALE]*9)
    for key in ['vx','vy','mode','timer']:cell('item.'+key,[0]*9)
    gem_x=[240,560,896,1280,1616,2016,2480]
    gem_y=[156,196,156,196,156,196,196]
    cell('gem.x',[x*SCALE for x in gem_x],False);cell('gem.y',[y*SCALE for y in gem_y],False)
    cell('gem.active',[1]*7)
    terrain=[0]*(COLS*ROWS)
    for x in range(COLS):
        for y in range(14,ROWS):terrain[y*COLS+x]=1
    for left,right in [(26,30),(59,64),(100,104),(144,148)]:
        for x in range(left,right):
            for y in range(14,ROWS):terrain[y*COLS+x]=0
    for left,right in [(12,21),(52,56),(94,98),(122,130)]:
        for x in range(left,right):terrain[11*COLS+x]=1
        for y in range(10,14):terrain[y*COLS+right-2]=2
    for x in (40,73,112,136):terrain[13*COLS+x]=1
    cell('level.tiles',terrain,False)
    functions=[]
    def save(f,body): functions.append(f.finish(body))
    f=Function('math.abs',['v'],'i32');a=f.local('v');save(f,f.if_(f.lt(a,0),f.sub(0,a),a))
    f=Function('math.min',['a','b'],'i32');a,b=f.local('a'),f.local('b');save(f,f.if_(f.lt(a,b),a,b))
    f=Function('math.max',['a','b'],'i32');a,b=f.local('a'),f.local('b');save(f,f.if_(f.gt(a,b),a,b))
    f=Function('world.tile',['x','y'],'i32');x,y=f.local('x'),f.local('y')
    outside=f.or_(f.lt(x,0),f.ge(x,f.c('world.width')),f.ge(y,f.c('world.height')))
    idx=f.add(f.mul(f.div(y,f.c('units.tile')),COLS),f.div(x,f.c('units.tile')))
    save(f,f.if_(f.lt(y,0),0,f.if_(outside,0,f.get('level.tiles',idx))))
    f=Function('world.solid',['x','y'],'i32');save(f,f.eq(f.call('world.tile',f.local('x'),f.local('y')),1))
    f=Function('math.overlap',['ax','ay','aw','ah','bx','by','bw','bh'],'i32')
    ax,ay,aw,ah,bx,by,bw,bh=[f.local(x) for x in f.params]
    save(f,f.and_(f.lt(ax,f.add(bx,bw)),f.gt(f.add(ax,aw),bx),f.lt(ay,f.add(by,bh)),f.gt(f.add(ay,ah),by)))
    f=Function('game.init')
    save(f,f.seq(*(f.put(c['id'],value,i) for c in cells if c['mutable'] for i,value in enumerate(c['values']))))
    f=Function('player.damage')
    damage=f.seq(f.put('player.lives',f.sub(f.get('player.lives'),1)),f.put('player.invulnerable',90),
        f.put('player.vy',-1024),f.put('event.code',3),f.if_(f.le(f.get('player.lives'),0),f.seq(f.put('game.phase',3),f.put('event.code',7))))
    save(f,f.if_(f.eq(f.get('player.invulnerable'),0),damage))
    f=Function('player.move',locals_=['nx','ny','edge','climb'])
    x,y=f.get('player.x'),f.get('player.y');w,h=f.c('player.width'),f.c('player.height')
    vx=f.mul(f.sub(f.get('input.right'),f.get('input.left')),f.c('player.speed'))
    update=[f.put('player.vx',vx),f.if_(f.ne(vx,0),f.put('player.facing',f.if_(f.gt(vx,0),1,-1))),
        f.put('player.coyote',f.if_(f.get('player.grounded'),6,f.max(0,f.sub(f.get('player.coyote'),1)))),
        f.put('player.jump_buffer',f.if_(f.get('input.jump'),6,f.max(0,f.sub(f.get('player.jump_buffer'),1))))]
    climb=f.and_(f.eq(f.call('world.tile',f.add(x,6*SCALE),f.add(y,8*SCALE)),2),f.or_(f.get('input.up'),f.get('input.down')))
    update.append(f.assign('climb',climb))
    update.append(f.if_(f.local('climb'),f.put('player.vy',f.mul(f.sub(f.get('input.down'),f.get('input.up')),384)),
        f.seq(f.put('player.vy',f.min(f.add(f.get('player.vy'),f.c('world.gravity')),f.c('world.max_fall'))),
        f.if_(f.and_(f.gt(f.get('player.coyote'),0),f.gt(f.get('player.jump_buffer'),0)),
              f.seq(f.put('player.vy',f.c('player.jump')),f.put('player.coyote',0),f.put('player.jump_buffer',0),f.put('event.code',1))))))
    update.append(f.assign('nx',f.max(0,f.min(f.add(x,f.get('player.vx')),f.sub(f.c('world.width'),w)))))
    edge=f.if_(f.gt(f.get('player.vx'),0),f.sub(f.add(f.local('nx'),w),1),f.local('nx'))
    update.append(f.assign('edge',edge))
    hit=f.or_(f.call('world.solid',f.local('edge'),f.add(y,256)),f.call('world.solid',f.local('edge'),f.sub(f.add(y,h),1)))
    resolved=f.if_(f.gt(f.get('player.vx'),0),f.sub(f.mul(f.div(f.local('edge'),f.c('units.tile')),f.c('units.tile')),w),
        f.mul(f.add(f.div(f.local('edge'),f.c('units.tile')),1),f.c('units.tile')))
    update.append(f.if_(f.and_(f.ne(f.get('player.vx'),0),hit),f.assign('nx',resolved)))
    update.append(f.put('player.x',f.local('nx')))
    update.extend([f.put('player.grounded',0),f.assign('ny',f.add(y,f.get('player.vy')))])
    v_edge=f.if_(f.ge(f.get('player.vy'),0),f.sub(f.add(f.local('ny'),h),1),f.local('ny'))
    update.append(f.assign('edge',v_edge))
    vhit=f.or_(f.call('world.solid',f.add(f.get('player.x'),256),f.local('edge')),
              f.call('world.solid',f.sub(f.add(f.get('player.x'),w),256),f.local('edge')))
    landing=f.if_(f.ge(f.get('player.vy'),0),
        f.seq(f.assign('ny',f.sub(f.mul(f.div(f.local('edge'),f.c('units.tile')),f.c('units.tile')),h)),f.put('player.grounded',1)),
        f.assign('ny',f.mul(f.add(f.div(f.local('edge'),f.c('units.tile')),1),f.c('units.tile'))))
    update.append(f.if_(vhit,f.seq(landing,f.put('player.vy',0))))
    update.append(f.put('player.y',f.local('ny')))
    frame=f.if_(f.ge(f.get('player.carried'),0),3,
        f.if_(f.eq(f.get('player.grounded'),0),2,f.if_(f.ne(f.get('player.vx'),0),f.op('rem_s',f.div(f.get('game.tick'),8),2),0)))
    update.append(f.put('player.frame',frame))
    save(f,f.seq(*update))
    f=Function('items.interact',locals_=['i','held'])
    i=f.local('i');held=f.local('held')
    throw=f.seq(f.put('item.mode',2,held),f.put('item.x',f.add(f.get('player.x'),f.mul(f.get('player.facing'),10*SCALE)),held),
        f.put('item.y',f.add(f.get('player.y'),2*SCALE),held),f.put('item.vx',f.mul(f.get('player.facing'),1536),held),
        f.put('item.vy',-384,held),f.put('player.carried',-1),f.put('event.code',2))
    near=f.and_(f.eq(f.get('player.carried'),-1),f.eq(f.get('item.mode',i),0),
        f.lt(f.abs(f.sub(f.get('item.x',i),f.get('player.x'))),24*SCALE),f.lt(f.abs(f.sub(f.get('item.y',i),f.get('player.y'))),32*SCALE))
    pickup=f.if_(near,f.seq(f.put('player.carried',i),f.put('item.mode',1,i),f.put('event.code',2)))
    save(f,f.if_(f.get('input.action'),f.seq(f.assign('held',f.get('player.carried')),f.if_(f.ge(held,0),throw,f.repeat(9,'i',pickup)))))
    f=Function('items.update',locals_=['i','e','nx','ny'])
    i,e=f.local('i'),f.local('e')
    carried=f.seq(f.put('item.x',f.add(f.get('player.x'),2*SCALE),i),f.put('item.y',f.sub(f.get('player.y'),10*SCALE),i))
    respawn=f.seq(f.put('item.timer',f.sub(f.get('item.timer',i),1),i),f.if_(f.le(f.get('item.timer',i),0),
        f.seq(f.put('item.mode',0,i),f.put('item.x',f.get('item.spawn_x',i),i),f.put('item.y',216*SCALE,i),f.put('item.vx',0,i),f.put('item.vy',0,i))))
    projectile=[f.put('item.vy',f.add(f.get('item.vy',i),64),i),f.put('item.x',f.add(f.get('item.x',i),f.get('item.vx',i)),i),
        f.put('item.y',f.add(f.get('item.y',i),f.get('item.vy',i)),i)]
    collision=f.and_(f.eq(f.get('item.mode',i),2),f.get('enemy.alive',e),
        f.call('math.overlap',f.get('item.x',i),f.get('item.y',i),8*SCALE,8*SCALE,
               f.get('enemy.x',e),f.get('enemy.y',e),f.if_(f.eq(e,5),24*SCALE,14*SCALE),f.if_(f.eq(e,5),24*SCALE,14*SCALE)))
    impact=f.seq(f.put('enemy.health',f.sub(f.get('enemy.health',e),1),e),f.if_(f.le(f.get('enemy.health',e),0),f.put('enemy.alive',0,e)),
        f.put('item.mode',3,i),f.put('item.timer',90,i),f.put('event.code',4))
    projectile.append(f.repeat(6,'e',f.if_(collision,impact)))
    floor_hit=f.and_(f.eq(f.get('item.mode',i),2),f.ge(f.get('item.vy',i),0),
        f.call('world.solid',f.add(f.get('item.x',i),4*SCALE),f.add(f.get('item.y',i),8*SCALE-1)))
    land=f.seq(f.put('item.y',f.sub(f.mul(f.div(f.add(f.get('item.y',i),8*SCALE-1),f.c('units.tile')),f.c('units.tile')),8*SCALE),i),
        f.put('item.mode',0,i),f.put('item.vx',0,i),f.put('item.vy',0,i))
    projectile.append(f.if_(floor_hit,land))
    projectile.append(f.if_(f.or_(f.gt(f.get('item.y',i),f.c('world.height')),f.lt(f.get('item.x',i),0),f.gt(f.get('item.x',i),f.c('world.width'))),
        f.seq(f.put('item.mode',3,i),f.put('item.timer',30,i))))
    mode=f.get('item.mode',i)
    body=f.if_(f.eq(mode,1),carried,f.if_(f.eq(mode,2),f.seq(*projectile),f.if_(f.eq(mode,3),respawn)))
    save(f,f.repeat(9,'i',body))
    f=Function('enemies.update',locals_=['i','edge'])
    i=f.local('i');width=f.if_(f.eq(i,5),24*SCALE,14*SCALE)
    x,y=f.get('enemy.x',i),f.get('enemy.y',i)
    edge=f.if_(f.gt(f.get('enemy.vx',i),0),f.add(x,width),f.sub(x,256))
    turn=f.or_(f.lt(x,f.sub(f.get('enemy.spawn_x',i),36*SCALE)),f.gt(x,f.add(f.get('enemy.spawn_x',i),36*SCALE)),
        f.eq(f.call('world.solid',edge,224*SCALE),0),f.call('world.solid',edge,f.add(y,8*SCALE)))
    overlap=f.call('math.overlap',f.get('player.x'),f.get('player.y'),f.c('player.width'),f.c('player.height'),x,y,width,width)
    body=f.if_(f.get('enemy.alive',i),f.seq(f.if_(turn,f.put('enemy.vx',f.sub(0,f.get('enemy.vx',i)),i)),
        f.put('enemy.x',f.add(x,f.get('enemy.vx',i)),i),f.put('enemy.frame',f.op('rem_s',f.div(f.get('game.tick'),12),2),i),
        f.if_(overlap,f.call('player.damage'))))
    save(f,f.repeat(6,'i',body))
    f=Function('world.progress',locals_=['i'])
    i=f.local('i')
    gem_hit=f.and_(f.get('gem.active',i),f.call('math.overlap',f.get('player.x'),f.get('player.y'),f.c('player.width'),f.c('player.height'),
        f.get('gem.x',i),f.get('gem.y',i),8*SCALE,8*SCALE))
    gems=f.repeat(7,'i',f.if_(gem_hit,f.seq(f.put('gem.active',0,i),f.put('game.gems',f.add(f.get('game.gems'),1)),f.put('event.code',8))))
    checkpoint=f.if_(f.and_(f.eq(f.get('game.checkpoint'),0),f.ge(f.get('player.x'),1260*SCALE)),
        f.seq(f.put('game.checkpoint',1),f.put('checkpoint.x',1296*SCALE),f.put('event.code',5)))
    fallen=f.seq(f.put('player.lives',f.sub(f.get('player.lives'),1)),f.put('player.x',f.get('checkpoint.x')),
        f.put('player.y',f.get('checkpoint.y')),f.put('player.vx',0),f.put('player.vy',0),f.put('player.invulnerable',60),
        f.if_(f.ge(f.get('player.carried'),0),f.seq(f.put('item.mode',3,f.get('player.carried')),f.put('item.timer',30,f.get('player.carried')),f.put('player.carried',-1))),
        f.put('event.code',3),f.if_(f.le(f.get('player.lives'),0),f.seq(f.put('game.phase',3),f.put('event.code',7))))
    victory=f.and_(f.eq(f.get('enemy.alive',5),0),f.ge(f.get('game.gems'),3),f.ge(f.get('player.x'),2752*SCALE),f.gt(f.get('player.lives'),0))
    save(f,f.seq(gems,checkpoint,f.if_(f.gt(f.get('player.y'),320*SCALE),fallen),
        f.if_(victory,f.seq(f.put('game.phase',2),f.put('event.code',6)))))
    f=Function('game.tick')
    running=f.seq(f.put('event.code',0),f.put('game.tick',f.add(f.get('game.tick'),1)),
        f.put('player.invulnerable',f.max(0,f.sub(f.get('player.invulnerable'),1))),f.call('player.move'),f.call('items.interact'),
        f.call('items.update'),f.call('enemies.update'),f.call('world.progress'),
        f.put('camera.x',f.max(0,f.min(f.sub(f.get('player.x'),160*SCALE),f.sub(f.c('world.width'),f.c('view.width'))))))
    start=f.if_(f.get('input.start'),f.seq(f.call('game.init'),f.put('game.phase',1)))
    save(f,f.if_(f.eq(f.get('game.phase'),1),running,start))
    declare_writes(functions)
    colors={'Ink':'#162238','Cream':'#fff1ca','Skin':'#edba86','Teal':'#65dfbd','Leaf':'#308d78','Deep':'#22645b',
            'Gold':'#ffc56b','Rust':'#c86656','Berry':'#be6fa5','White':'#ffffff','Blue':'#629ac2','Night':'#354867'}
    symbols={'.':None,'i':'Ink','c':'Cream','s':'Skin','t':'Teal','l':'Leaf','d':'Deep','g':'Gold','r':'Rust','b':'Berry','w':'White','u':'Blue','n':'Night'}
    designs={
        'hero0':['..tttt..','.tttttt.','..ssisi.','..ssss..','.iitii..','ttttttt.','..t..t..','.ii..ii.'],
        'hero1':['..tttt..','.tttttt.','..ssisi.','..ssss..','.iitii..','.tttttt.','.t....t.','ii....ii'],
        'hero2':['..tttt..','.tttttt.','..ssisi.','..ssss..','ttiititt','.tttttt.','..tttt..','.ii..ii.'],
        'hero3':['..tttt..','.tttttt.','..ssisi.','..ssss..','tiiiiitt','.tttttt.','..t..t..','.ii..ii.'],
        'enemy0':['..rrrr..','.rrrrrr.','rrwiwirr','rrriirrr','.rrrrrr.','..rrrr..','.ii..ii.','ii....ii'],
        'enemy1':['..rrrr..','.rrrrrr.','rrwiwirr','rrriirrr','.rrrrrr.','..rrrr..','ii....ii','.ii..ii.'],
        'boss':['.gg..gg.','gbbbbbbg','bwiwwiwb','bbbrrbbb','.bwwwwb.','bbbbbbbb','.bb..bb.','iii..iii'],
        'turnip':['..l.l...','...ll...','..cccc..','.cccccc.','.ccggcc.','..cccc..','...cc...','...c....'],
        'gem':['...g....','..gcg...','.gcccg..','gccwccg.','.gcccg..','..gcg...','...g....','........'],
        'ground':['tltltltl','llllllld','dddddddd','dnndddnd','dddndddd','ddddnndd','nddddddn','dddndddd'],
        'soil':['dddddddd','dnndddnd','dddddddd','dddndddd','ddddnndd','nddddddn','dddddddd','dddndddd'],
        'ladder':['.g....g.','.gggggg.','.g....g.','.g....g.','.gggggg.','.g....g.','.g....g.','.gggggg.'],
        'flag':['...i....','...itt..','...ittt.','...itt..','...i....','...i....','...i....','..iii...'],
        'door':['.gggggg.','ggnnnngg','gnnnnnng','gnnnngng','gnnnnnng','gnnnnnng','gnnnnnng','gggggggg'],
        'flower':['...b....','..bgb...','...b....','...l....','..ll....','...ll...','...l....','..ll....'],
        'heart':['.rr..rr.','rrrrrrrr','rrrrrrrr','.rrrrrr.','..rrrr..','...rr...','........','........'],
    }
    assets={'palettes':[{'id':'harvest','colors':colors}], 'tiles':[{'id':key,'palette':'harvest','symbols':symbols,'pixels':rows} for key,rows in designs.items()]}
    presentation={
        'title':'Alien Harvest','subtitle':'La cosecha del otro mundo','width':480,'height':270,'scale':256,
        'map':{'cell':'level.tiles','columns':COLS,'rows':ROWS,'tile_size':16,'tiles':{'1':'ground','2':'ladder'}},
        'camera':'camera.x','phase':'game.phase','clock':'game.tick','event':'event.code',
        'views':[
            {'id':'gems','count':7,'x':'gem.x','y':'gem.y','visible':'gem.active','frames':['gem'],'size':8},
            {'id':'items','count':9,'x':'item.x','y':'item.y','mode':'item.mode','hidden_modes':[3],'frames':['turnip'],'size':8},
            {'id':'enemies','count':5,'x':'enemy.x','y':'enemy.y','visible':'enemy.alive','frame':'enemy.frame','mirror':'enemy.vx','frames':['enemy0','enemy1'],'size':16},
            {'id':'boss','count':1,'start':5,'x':'enemy.x','y':'enemy.y','visible':'enemy.alive','frames':['boss'],'size':24},
            {'id':'player','count':1,'x':'player.x','y':'player.y','frame':'player.frame','mirror':'player.facing','blink':'player.invulnerable','frames':['hero0','hero1','hero2','hero3'],'size':16}],
        'markers':[{'x':1296,'y':208,'tile':'flag','size':16},{'x':2760,'y':192,'tile':'door','size':32}],
        'hud':{'lives':'player.lives','gems':'game.gems','boss':'enemy.health','checkpoint':'game.checkpoint'},
        'inputs':{'left':['ArrowLeft','KeyA'],'right':['ArrowRight','KeyD'],'up':['ArrowUp','KeyW'],'down':['ArrowDown','KeyS'],
                  'jump':['Space'],'action':['KeyX','KeyJ'],'start':['Enter']},
    }
    tests=[
        {'id':'jump.grounded','function':'player.move','set':{'player.grounded':[1],'input.jump':[1]},'expect':{'player.vy':[-1664]}},
        {'id':'damage.once','function':'player.damage','set':{'player.invulnerable':[0]},'expect':{'player.lives':[2],'player.invulnerable':[90]}},
    ]
    return {'format':'pact.module/0.2.0','constants':constants,'cells':cells,'functions':functions,
            'exports':[fn['id'] for fn in functions],'assets':assets,'presentation':presentation,'tests':tests}


if __name__=='__main__':
    target=Path('examples/alien-harvest.pact.json')
    target.write_text(json.dumps(game_document(),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(target)
