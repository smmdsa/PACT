"""Discover published source examples and render the site's shared demo catalog."""
import html
import json


def example_files(root):
    return sorted(path for path in (root/'examples').rglob('*') if path.is_file() and path.suffix in ('.pact','.json'))


def render_catalog(root,sources):
    results=json.loads((root/'benchmarks/metroidvania_pilot/results.json').read_text())
    measured={trial['trial_id']:f"{trial['checks_passed']}/{trial['checks_total']} checks" for trial in results['trials']}
    games=[
        ('orbita','Órbita · a future to cultivate','PACT / WebAssembly','A spatial interface for six possible futures. Cultivate ideas, change perspective and explore reversible decisions.',
         'orbita.html','orbita.pact','orbita-design.html','Checked interaction kernel','orbita-art'),
        ('alien-harvest','Alien Harvest','PACT / WebAssembly','A platformer with checked state, enemies, collectibles and a boss. Keyboard and touch controls.',
         'game.html','alien-harvest.inline.pact','browser-validation.html','Input-only victory verified','harvest'),
        ('metroid-gpt61','Ember Vault · GPT-6.1','HTML / JavaScript','Explore five connected rooms, unlock a double jump, recover the key and defeat the sentinel.',
         'metroidvania/metro_a.html','metroidvania/metro_a.html','metroidvania-pilot.html',measured['metro_a'],'vault-a'),
        ('metroid-astra','Ember Vault · GPT-6 Astra','HTML / JavaScript','A second original response to the same Metroidvania brief. One generation, with no source repairs.',
         'metroidvania/metro_b.html','metroidvania/metro_b.html','metroidvania-pilot.html',measured['metro_b'],'vault-b'),
    ]
    cards=[]
    for number,(identifier,title,language,description,url,source,evidence,status,art) in enumerate(games,1):
        cards.append(f'''<article class="demo-card" data-catalog-item data-kind="playable" id="{identifier}">
<div class="demo-art {art}" aria-hidden="true"><span>0{number}</span><b>{html.escape(language)}</b></div>
<div class="demo-content"><span class="demo-label">Playable · {html.escape(status)}</span><h3>{html.escape(title)}</h3><p>{html.escape(description)}</p>
<div class="demo-actions"><a class="button" href="{url}" data-demo="{identifier}">Play here</a><a href="{evidence}">Evidence</a><a href="{source}" download>Download source</a></div></div></article>''')
    downloads=[]
    for path in sources:
        target=path.relative_to(root/'examples').as_posix()
        downloads.append(f'<li data-catalog-item data-kind="source"><a href="{html.escape(target,quote=True)}" download>{html.escape(target)}</a></li>')
    return '''<style>
.catalog-intro h1{font-size:clamp(34px,5vw,54px);line-height:1.15;letter-spacing:-1.5px;margin:15px 0}.catalog-intro p{color:var(--muted);max-width:700px}.catalog-tools{padding:20px;background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:26px 0}.catalog-tools label{display:block;font-weight:650;font-size:14px}.catalog-tools input{width:100%;padding:13px 14px;margin:9px 0 14px;border:1px solid #43516a;border-radius:6px;background:var(--bg);color:var(--text);font:inherit}.catalog-tools input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.catalog-filters{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.catalog-filters button,.demo-stop{font:inherit;font-size:13px;background:transparent;border:1px solid #43516a;border-radius:5px;padding:7px 12px;color:var(--text);cursor:pointer}.catalog-filters button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}#catalog-count{margin-left:auto;font-size:12px;color:var(--muted)}.demo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.demo-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}.demo-art{height:116px;display:flex;justify-content:space-between;align-items:end;padding:18px 20px;background:linear-gradient(125deg,#183949,#101b2c);border-bottom:1px solid var(--line);color:#b9e9d8}.demo-art span{font:48px/1 ui-monospace,monospace;opacity:.6}.demo-art b{font-size:11px;letter-spacing:1px}.orbita-art{background:#e7e4d9;color:#9b432a}.vault-a{background:linear-gradient(125deg,#3d3041,#182638);color:#f0d4a1}.vault-b{background:linear-gradient(125deg,#244244,#1c283c);color:#9ce9df}.demo-content{padding:20px}.demo-label{font-size:11px;color:#b9c7df}.demo-content h3{font-size:21px;line-height:1.3;margin:9px 0}.demo-content p{font-size:14px;color:var(--muted);line-height:1.65}.demo-actions{display:flex;align-items:center;gap:14px;flex-wrap:wrap;font-size:12px;margin-top:20px}.demo-actions .button{font-size:13px}.catalog-source ul{padding-left:20px;overflow-wrap:anywhere}.catalog-source li{margin:8px 0;font:13px/1.7 ui-monospace,monospace}.catalog-source details{padding:16px 20px;background:var(--panel);border:1px solid var(--line);border-radius:9px}.catalog-source summary{cursor:pointer;font-weight:600}.catalog-guides{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;margin:18px 0}.demo-player{scroll-margin-top:20px;border:1px solid var(--line);border-radius:10px;padding:18px;margin:28px 0;background:var(--panel)}.demo-player header{display:flex;justify-content:space-between;align-items:center;gap:16px}.demo-player h2{font-size:20px;margin:0}.demo-player iframe{display:block;background:#090f1c;width:100%;height:650px;border:0;margin-top:16px;border-radius:6px}.demo-player p{font-size:12px;color:var(--muted);margin-bottom:0}.demo-card[hidden],li[hidden],section[hidden]{display:none}@media(max-width:1000px){.demo-grid{grid-template-columns:1fr}}@media(max-width:760px){.demo-player{padding:10px}.demo-player iframe{height:560px}#catalog-count{margin-left:0;width:100%}}
</style>
<section class="catalog-intro"><span class="eyebrow">THE PACT DEMO LIBRARY</span><h1>Demos &amp; Examples</h1><p>One place to explore interactive interfaces, play the games, explore model-generated applications and find every published source example.</p><p><a href="metroidvania/index.html">Compare the two Metroidvania outputs →</a></p></section>
<div class="catalog-tools"><label for="catalog-search">Search demos and examples</label><input id="catalog-search" type="search" placeholder="Game, model, feature or filename" autocomplete="off"><div class="catalog-filters" aria-label="Catalog filters"><button type="button" data-filter="all" aria-pressed="true">All</button><button type="button" data-filter="playable" aria-pressed="false">Playable</button><button type="button" data-filter="source" aria-pressed="false">Source examples</button><output id="catalog-count" aria-live="polite"></output></div></div>
<section class="demo-player" id="demo-player" aria-label="Selected demo" hidden><header><h2 id="demo-title"></h2><button class="demo-stop" type="button" id="demo-stop">Close demo</button></header><iframe id="demo-frame" title="Selected playable demo" sandbox="allow-scripts"></iframe><p>Click inside a demo to focus its controls. Open a different demo to start a fresh session. Metroidvania examples require a keyboard; Alien Harvest also supports touch.</p></section>
<p id="catalog-empty" hidden>No matching examples. Try another search or filter.</p>
<section data-catalog-section><h2 class="section-title">Playable applications</h2><div class="demo-grid">'''+''.join(cards)+'''</div><p style="color:var(--muted);font-size:13px">Órbita is an authored PACT interface experiment. The GPT games are original HTML/JavaScript experiments. Their finite checks do not establish a general model ranking or a PACT advantage.</p></section>
<section class="catalog-source" data-catalog-section><h2 class="section-title">Code examples &amp; fixtures</h2><p>Greeting, wrapping counters, checked conditions, export cases and Alien Harvest representations. These are downloadable source examples and replay/patch fixtures; they are not all browser applications.</p><div class="catalog-guides"><a href="syntax.html">Source syntax</a><a href="checked-assertions.html">Checked conditions</a><a href="replay.html">Replay examples</a><a href="transactions.html">Patch workflow</a></div><details id="catalog-files"><summary>Browse all source files and fixtures</summary><ul>'''+''.join(downloads)+'''</ul></details></section>
<script>
(()=>{
const search=document.querySelector('#catalog-search'),items=[...document.querySelectorAll('[data-catalog-item]')],filters=[...document.querySelectorAll('[data-filter]')];let kind='all';
const update=()=>{const query=search.value.trim().toLowerCase();let count=0;for(const item of items){const visible=(kind==='all'||item.dataset.kind===kind)&&item.textContent.toLowerCase().includes(query);item.hidden=!visible;if(visible)count++;}for(const section of document.querySelectorAll('[data-catalog-section]'))section.hidden=![...section.querySelectorAll('[data-catalog-item]')].some(item=>!item.hidden);document.querySelector('#catalog-count').textContent=count+' entries';document.querySelector('#catalog-empty').hidden=count!==0;if(query||kind==='source')document.querySelector('#catalog-files').open=true;};
search.addEventListener('input',update);for(const button of filters)button.addEventListener('click',()=>{kind=button.dataset.filter;for(const other of filters)other.setAttribute('aria-pressed',String(other===button));update();});
const launches=[...document.querySelectorAll('[data-demo]')],player=document.querySelector('#demo-player'),frame=document.querySelector('#demo-frame');
const launch=link=>{document.querySelector('#demo-title').textContent=link.closest('article').querySelector('h3').textContent;frame.title=document.querySelector('#demo-title').textContent;player.hidden=false;frame.src=link.getAttribute('href');history.replaceState(null,'','#'+link.dataset.demo);player.scrollIntoView({block:'start'});};
for(const link of launches)link.addEventListener('click',event=>{if(event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();launch(link);});
document.querySelector('#demo-stop').addEventListener('click',()=>{frame.removeAttribute('src');player.hidden=true;history.replaceState(null,'','#');});
update();const selected=launches.find(link=>link.dataset.demo===location.hash.slice(1));if(selected)launch(selected);
})();
</script>'''
