from .schema import require


def validate_presentation(p,layout,tiles,exports):
    if not p:return
    def check(condition,message):require(condition,'PRESENTATION_INVALID',message)
    def cell(key,extent=1,mutable=False):
        check(isinstance(key,str) and key in layout,'Unknown presentation cell.')
        check(layout[key]['count']>=extent and (not mutable or layout[key]['mutable']),'Invalid cell extent/authority.')
    check(isinstance(exports,list) and all(isinstance(key,str) for key in exports),'Invalid exports.')
    required={'title','subtitle','width','height','scale','map','camera','phase','clock','event','views','markers','hud','inputs'}
    check(isinstance(p,dict) and set(p)==required,'Invalid presentation fields.')
    check(isinstance(p['title'],str) and isinstance(p['subtitle'],str),'Invalid presentation text.')
    for key in ('width','height','scale'):check(type(p[key]) is int and 1<=p[key]<=2048,'Invalid viewport/scale.')
    check('game.init' in exports and 'game.tick' in exports,'Game host requires init/tick exports.')
    for key in ('camera','phase','clock','event'):cell(p[key])
    m=p['map'];check(isinstance(m,dict) and set(m)=={'cell','columns','rows','tile_size','tiles'},'Invalid map.')
    for key in ('columns','rows','tile_size'):check(type(m[key]) is int and 1<=m[key]<=512,'Invalid map extent.')
    cell(m['cell'],m['columns']*m['rows']);check(layout[m['cell']]['count']==m['columns']*m['rows'],'Map size differs from state extent.')
    check(isinstance(m['tiles'],dict),'Invalid tile mapping.')
    for key,value in m['tiles'].items():check(isinstance(key,str) and key.isdecimal() and int(key)>0 and isinstance(value,str) and value in tiles,'Invalid map tile.')
    check(isinstance(p['views'],list) and len(p['views'])<=128,'Invalid views.')
    ids=set()
    for v in p['views']:
        fields={'id','count','x','y','frames','size'}
        optional={'start','visible','frame','mirror','blink','mode','hidden_modes'}
        check(isinstance(v,dict) and fields<=set(v) and set(v)<=fields|optional,'Invalid view fields.')
        check(isinstance(v['id'],str) and v['id'] not in ids,'Duplicate view ID.');ids.add(v['id'])
        check(type(v['count']) is int and 1<=v['count']<=256,'Invalid view count.')
        start=v.get('start',0);check(type(start) is int and start>=0,'Invalid view start.')
        check(type(v['size']) is int and 1<=v['size']<=128,'Invalid sprite size.')
        check(isinstance(v['frames'],list) and v['frames'] and all(isinstance(key,str) and key in tiles for key in v['frames']),'Missing sprite frame.')
        for key in ('x','y','visible','frame','mirror','blink','mode'):
            if key in v:cell(v[key],start+v['count'])
        if 'mode' in v:check(isinstance(v.get('hidden_modes'),list) and all(type(x) is int for x in v['hidden_modes']),'Invalid mode visibility.')
    check(isinstance(p['markers'],list) and len(p['markers'])<=256,'Invalid markers.')
    for mark in p['markers']:
        check(isinstance(mark,dict) and set(mark)=={'x','y','tile','size'},'Invalid marker.')
        check(all(type(mark[key]) is int for key in ('x','y','size')) and 1<=mark['size']<=128 and isinstance(mark['tile'],str) and mark['tile'] in tiles,'Invalid marker tile/size.')
    check(isinstance(p['hud'],dict) and set(p['hud'])=={'lives','gems','boss','checkpoint'},'Invalid HUD.')
    for key in ('lives','gems','checkpoint'):cell(p['hud'][key])
    cell(p['hud']['boss'],6);cell('enemy.alive',6)
    check(isinstance(p['inputs'],dict) and set(p['inputs'])=={'left','right','up','down','jump','action','start'},'Invalid input profile.')
    keys=set()
    for action,codes in p['inputs'].items():
        cell('input.'+action,1,True)
        check(layout['input.'+action]['count']==1,'Inputs are scalar cells.')
        check(isinstance(codes,list) and 1<=len(codes)<=8 and all(isinstance(code,str) and 1<=len(code)<=40 for code in codes),'Invalid key bindings.')
        for code in codes:check(code not in keys,'Ambiguous key binding.');keys.add(code)
