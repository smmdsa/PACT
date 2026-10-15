"""Compile checked examples and build static Markdown documentation."""
import html
import json
import shutil
from pathlib import Path

from pact.browser import game_html
from pact.graph import load_document
from pact.module_build import build_module
from pact.__main__ import main as pact_cli
from tools.markdown_docs import render_markdown
from tools.demo_catalog import example_files, render_catalog
from tools.build_orbita import build_orbita

ROOT=Path(__file__).resolve().parents[1]


def metroid_results_html(pilot):
    data=json.loads((pilot/'results.json').read_text())
    rows=[];details=[]
    for trial in data['trials']:
        model=html.escape(trial['model_alias'])
        score=str(trial['checks_passed'])+'/'+str(trial['checks_total'])
        victory=next(check['pass'] for check in trial['checks'] if check['id']=='victory_after_boss_and_exit')
        rows.append(f'<tr><td>{model}</td><td>{score}</td><td>{trial["source_bytes"]:,}</td><td>{"Sí" if victory else "No"}</td></tr>')
        checks=''.join('<li>'+html.escape(check['id'])+' · '+('✓' if check['pass'] else '✕')+'</li>' for check in trial['checks'])
        details.append(f'<details><summary>{model} · comprobaciones</summary><ul>{checks}</ul></details>')
    return '<section style="margin-top:32px"><h2>Qué medimos</h2><p>Una entrega por modelo, sin reparar los juegos. Recorrido automatizado con entradas de movimiento: habilidades, puertas, combate, regreso, jefe, victoria y reinicio.</p><div style="overflow:auto"><table style="width:100%;text-align:left;line-height:2"><thead><tr><th>Alias solicitado</th><th>Checks</th><th>Bytes HTML</th><th>Victoria observada</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'+''.join(details)+'<p>Empate en estas comprobaciones; no es una clasificación general. No medimos tokens, costo, FPS ni calidad artística. <a href="results.json">Datos y ejecuciones de CI</a> · <a href="../metroidvania-pilot.html">Método y límites</a></p></section>'


DOCUMENTS=[('progress','Progress','CHANGELOG.md'),('roadmap','Roadmap','ROADMAP.md'),
 ('metroidvania-pilot','GPT Metroidvania pilot','docs/metroidvania-pilot.md'),
 ('orbita-design','Órbita: interface experiment','docs/orbita-design.md'),
 ('roadmap-audit','Implementation audit','docs/roadmap-audit.md'),
 ('trace-grading','Trace grading','docs/agent-trace-grading.md'),
 ('agent-sandbox','Isolated counter','docs/agent-sandbox.md'),
 ('isolation-probes','Isolation probes','docs/isolation-probes.md'),
 ('nominal-units','Nominal unit contracts','docs/nominal-units.md'),
 ('nominal-units-spec','Module 0.6 specification','docs/superpowers/specs/2026-10-15-nominal-units.md'),
 ('expected-traps','Expected trap cases','docs/expected-traps.md'),
 ('expected-traps-spec','Module 0.5 specification','docs/superpowers/specs/2026-10-15-expected-traps.md'),
 ('checked-assertions','Checked conditions','docs/checked-assertions.md'),
 ('export-evidence','Export evidence','docs/export-evidence.md'),
 ('browser-validation','Browser validation','docs/browser-validation.md'),
 ('portability','Portability','docs/portability.md'),
 ('locations','Source locations','docs/source-locations.md'),
 ('replay','Execution replay','docs/replay.md'),
 ('syntax','Syntax','docs/syntax.md'),('literals','Literal definitions','docs/literals.md'),
 ('inline-literals-and-resets','Inline literals and resets','docs/inline-literals-and-resets.md'),
 ('inspection','Selective inspection','docs/inspection.md'),('transactions','Transactions','docs/transactions.md'),
 ('compression','Data compression','docs/data-compression.md'),('security','Security','docs/security.md'),
 ('comparison','Language comparison','docs/traditional-comparison.md'),('benchmarks','Token benchmarks','benchmarks/README.md'),
 ('runtime','Runtime benchmarks','docs/runtime-performance.md'),('evaluation','Agent evaluation','docs/agent-evaluation.md'),
 ('agents','Contributing','docs/agent-contributions.md'),('resources','Resource bounds','docs/resource-bounds.md')]
STYLE='''
:root{color-scheme:dark;--bg:#0d111a;--panel:#151c29;--line:#2a3447;--text:#e5ebf5;--muted:#9eabc0;--accent:#a4b6ff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.75 system-ui,sans-serif}a{color:var(--accent);text-underline-offset:4px}a:focus-visible,button:focus-visible{outline:3px solid #c4a6ff;outline-offset:4px;border-radius:3px}.skip{position:absolute;left:-9999px}.skip:focus{left:20px;top:20px;z-index:5;background:var(--panel);padding:10px}.topbar{height:72px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 32px;background:#111723}.brand{font-weight:800;letter-spacing:2px;color:var(--text);text-decoration:none;font-size:22px}.brand small{font-size:11px;font-weight:400;color:var(--muted);letter-spacing:1px;margin-left:14px}.toplinks{display:flex;gap:24px;align-items:center;font-size:14px}.layout{display:grid;grid-template-columns:220px minmax(0,1fr) 200px;gap:32px;max-width:1500px;margin:auto;padding:32px}.sidebar{position:sticky;top:24px;align-self:start}.sidebar .label,.eyebrow{font-size:11px;color:var(--muted);letter-spacing:1.8px;text-transform:uppercase}.sidebar nav{display:flex;flex-direction:column;gap:3px;margin-top:14px}.sidebar nav a{padding:7px 12px;border-radius:6px;color:var(--muted);text-decoration:none;font-size:14px}.sidebar nav a:hover,.sidebar nav a[aria-current=page]{background:#202a3e;color:var(--text)}main{min-width:0;max-width:900px;width:100%;margin:auto}.toc{position:sticky;top:24px;align-self:start;border-left:1px solid var(--line);padding-left:16px;font-size:12px}.toc ul{list-style:none;padding:0;margin:10px 0}.toc li{margin:8px 0}.toc a{color:var(--muted);text-decoration:none}.toc .level3{padding-left:10px}.docmeta{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;margin-bottom:24px;color:var(--muted);font-size:12px}.markdown h1{font-size:38px;line-height:1.2;letter-spacing:-1px;margin:0 0 26px}.markdown h2{margin:44px 0 16px;font-size:26px;border-top:1px solid var(--line);padding-top:28px;line-height:1.3}.markdown h3{margin-top:30px;font-size:20px}.markdown h1,.markdown h2,.markdown h3{scroll-margin-top:24px}.markdown p,.markdown li{color:#c6d1e1}.markdown ul,.markdown ol{padding-left:24px}.markdown li{margin:7px 0}.markdown blockquote{border-left:3px solid var(--accent);background:var(--panel);padding:8px 20px;margin:24px 0}.markdown img{max-width:100%;height:auto}.markdown code{font:13px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace;color:#c8d2ff;background:#20283a;border:1px solid #303a51;border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}.markdown pre,pre{overflow-x:auto;white-space:pre;background:#101724;border:1px solid var(--line);border-radius:9px;padding:20px;font:13px/1.7 ui-monospace,monospace;margin:24px 0}.markdown pre code{background:none;border:none;padding:0;color:#d7e2f4;overflow-wrap:normal}.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:8px;margin:24px 0}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px 14px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:#1a2334;color:#d3dded}tr:last-child td{border-bottom:0}td{color:#bbc9db}.hero{padding:32px 0 20px}.hero h1{font-size:clamp(38px,5vw,65px);line-height:1.1;letter-spacing:-2px;margin:20px 0}.hero p{max-width:720px;font-size:18px;color:var(--muted)}.badge{display:inline-flex;padding:4px 10px;border:1px solid #46635b;border-radius:99px;color:#9cd7b7;font-size:11px;letter-spacing:.8px}.actions{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin:24px 0}.button{padding:10px 18px;border-radius:7px;background:var(--accent);color:#101729;text-decoration:none;font-weight:700;font-size:14px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:28px 0}.card{background:var(--panel);border:1px solid var(--line);padding:20px;border-radius:9px}.card strong{display:block;font-size:26px;line-height:1.3}.card span{display:block;color:var(--muted);font-size:12px;margin-top:7px}.section-title{font-size:25px;line-height:1.3;margin-top:44px}.notice{background:#182236;border:1px solid #38486c;border-radius:9px;padding:18px 20px;color:#c2cfe3;font-size:14px}footer{border-top:1px solid var(--line);padding:22px 0;margin-top:48px;font-size:12px;color:var(--muted)}@media(max-width:1200px){.layout{grid-template-columns:200px minmax(0,1fr)}.toc{display:none}}@media(max-width:760px){.layout{display:block;padding:22px 18px}.sidebar{position:static;margin-bottom:28px}.sidebar nav{flex-direction:row;overflow-x:auto;white-space:nowrap;padding-bottom:8px}.sidebar .label{display:none}.topbar{padding:0 18px}.brand small{display:none}.toplinks{gap:14px}.cards{grid-template-columns:1fr}.markdown h1{font-size:31px}.hero{padding-top:8px}}
'''


def page(title,body,current='index',toc=None):
    navigation='<a href="index.html"'+(' aria-current="page"' if current=='index' else '')+'>Overview</a>'
    navigation+='<a href="demos.html"'+(' aria-current="page"' if current=='demos' else '')+'>Demos &amp; Examples</a>'
    for slug,label,_ in DOCUMENTS:
        navigation+=f'<a href="{slug}.html"'+(' aria-current="page"' if current==slug else '')+f'>{html.escape(label)}</a>'
    contents=''.join(f'<li class="level{item["level"]}"><a href="#{html.escape(item["id"],quote=True)}">{html.escape(item["title"])}</a></li>' for item in toc or [] if item['level'] in (2,3))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="PACT: explicit graphs, checked effects and measured agent-first programming."><title>{html.escape(title)} · PACT</title><style>{STYLE}</style></head><body><a class="skip" href="#main-content">Skip to content</a><header class="topbar"><a class="brand" href="index.html">PACT <small>AGENT-FIRST LANGUAGE LAB</small></a><div class="toplinks"><a href="progress.html">Progress</a><a href="demos.html">Demos &amp; Examples</a><a href="https://github.com/smmdsa/PACT">GitHub ↗</a></div></header><div class="layout"><aside class="sidebar"><span class="label">Documentation</span><nav aria-label="Documentation">{navigation}</nav></aside><main id="main-content">{body}<footer>Research prototype · Source 0.2 / data 0.3 / literals 0.4 · Graph 0.0.1 / module 0.1.0 / 0.2.0 / 0.3.0 / 0.4.0 / 0.5.0 / 0.6.0</footer></main><aside class="toc" aria-label="On this page"><span class="eyebrow">On this page</span><ul>{contents}</ul></aside></div></body></html>'''



def main():
    output=ROOT/'site-output';output.mkdir(exist_ok=True)
    build_orbita(ROOT,output)
    game=load_document(ROOT/'examples/alien-harvest.inline.pact')
    binary,manifest=build_module(game)
    (output/'game.wasm').write_bytes(binary)
    (output/'game.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'game.html').write_bytes(game_html(game,binary,manifest))
    if pact_cli(['build',str(ROOT/'examples/hello.agent.pact'),'-o',str(output/'hello.wasm')])!=0:raise RuntimeError('Greeting build failed')
    mapping={path:slug+'.html' for slug,_,path in DOCUMENTS};mapping['README.md']='index.html'
    mapping.update({'orbita.html':'orbita.html','demos.html':'demos.html'})
    sources=example_files(ROOT)
    for path in sources:
        relative=path.relative_to(ROOT/'examples')
        destination=output/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,destination);mapping[str(path.relative_to(ROOT))]=relative.as_posix()
    (output/'demos.html').write_text(page('Demos & Examples',render_catalog(ROOT,sources),'demos'),encoding='utf-8')
    reports=output/'reports';reports.mkdir(exist_ok=True)
    metroid=output/'metroidvania';metroid.mkdir(exist_ok=True)
    pilot=ROOT/'benchmarks/metroidvania_pilot'
    shell=(pilot/'index.html').read_text().replace('<!--BENCHMARK_RESULTS-->',metroid_results_html(pilot))
    (metroid/'index.html').write_text(shell)
    for name in ('metro_a.html','metro_b.html'):
        shutil.copyfile(pilot/'candidates'/name,metroid/name)
    mapping['benchmarks/metroidvania_pilot/index.html']='metroidvania/index.html'
    shutil.copyfile(pilot/'prompt.txt',metroid/'prompt.txt')
    mapping['benchmarks/metroidvania_pilot/prompt.txt']='metroidvania/prompt.txt'
    shutil.copyfile(pilot/'results.json',metroid/'results.json')
    mapping['benchmarks/metroidvania_pilot/results.json']='metroidvania/results.json'
    for path in (ROOT/'benchmarks/results').glob('*.json'):
        shutil.copyfile(path,reports/path.name);mapping[str(path.relative_to(ROOT))]='reports/'+path.name
    for slug,title,path in DOCUMENTS:
        rendered,toc=render_markdown((ROOT/path).read_text(encoding='utf-8'),path,mapping)
        rendered=rendered.replace('<table>','<div class="table-wrap"><table>').replace('</table>','</table></div>')
        body=f'<div class="docmeta"><span>PACT / {html.escape(title)}</span><a href="https://github.com/smmdsa/PACT/blob/main/{path}">View source ↗</a></div><article class="markdown">{rendered}</article>'
        (output/(slug+'.html')).write_text(page(title,body,slug,toc),encoding='utf-8')
    report=json.loads((ROOT/'benchmarks/results/inline-o200k_base.json').read_text())
    metrics={row['representation']:row for row in report['results']};latest=metrics['compact_0_4_inline'];baseline=metrics['minified_json']
    reduction=100*(1-latest['tokens']/baseline['tokens'])
    code=html.escape((ROOT/'examples/hello.agent.pact').read_text())
    body=f'''<section class="hero"><span class="badge">IMPLEMENTED · INLINE SOURCE 0.4</span><h1>Explicit intent.<br>Checked execution.</h1><p>A language experiment for agents that inspect, edit and validate structured programs. Follow the evidence as PACT evolves.</p><div class="actions"><a class="button" href="demos.html">Explore demos &amp; examples</a><a href="game.html">Play Alien Harvest</a><a href="progress.html">Latest progress →</a><a href="syntax.html">Read the syntax</a></div></section><div class="cards"><div class="card"><strong>{latest['tokens']:,}</strong><span>Game source tokens · o200k_base</span></div><div class="card"><strong>{reduction:.1f}% less</strong><span>Compared with minified JSON of identical IR</span></div><div class="card"><strong>Same Wasm</strong><span>Stable IDs, revision and execution</span></div></div><div class="notice">Source compression is measured. Overall agent productivity is not established. PACT costs more source tokens than Python, JavaScript and C in our two small kernels.</div><h2 class="section-title">What shipped</h2><article class="markdown"><ul><li>Stable-ID literal definitions and inline integer arguments, compressed initial data and shared sprite symbols.</li><li>Checked runtime bulk resets in numeric module 0.2.0, with explicit migration from 0.1.0.</li><li>Selective function context and revision-checked patches with executable tests.</li><li>Reproducible token comparisons, runtime measurement and a protocol for external LLM trials.</li></ul></article><p><a href="literals.html">Literal definitions</a> · <a href="inline-literals-and-resets.html">Inline literals and resets</a> · <a href="compression.html">Data compression</a> · <a href="runtime.html">Runtime benchmark</a> · <a href="evaluation.html">Agent evaluation</a></p><h2 class="section-title">Hello from an alien language</h2><article class="markdown"><pre><code class="language-text">{code}</code></pre></article><p><a href="hello.agent.pact" download>Greeting source</a> · <a href="alien-harvest.inline.pact" download>Game source0.4</a> · <a href="game.html" download>Standalone game</a></p><h2 class="section-title">Traditional languages: measured honestly</h2><div class="table-wrap"><table><thead><tr><th>Tokens · o200k_base</th><th>PACT0.2</th><th>Python</th><th>JavaScript</th><th>C</th></tr></thead><tbody><tr><td>Greeting</td><td>78</td><td>10</td><td>11</td><td>27</td></tr><tr><td>Wrapping counter</td><td>163</td><td>74</td><td>76</td><td>138</td></tr></tbody></table></div><p>Frozen small programs; driver costs and policy asymmetries are reported separately. <a href="comparison.html">Full methodology →</a></p><h2 class="section-title">Next: measure useful agent work</h2><p>Correct edits, diagnosis, retrieved context, repair cycles and stale-change rejection matter alongside runtime and source size. Exploratory GPT counter and Metroidvania pilots are archived; formal provider trials remain pending. No general success leaderboard is claimed. <a href="evaluation.html">Trial protocol →</a></p><h2 class="section-title">Play the GPT Metroidvania experiments</h2><p>Two requested GPT models, one shared HTML/JavaScript brief, five connected rooms and one original delivery each. Human-playable examples with separate finite behavior evidence; this does not establish a PACT advantage.</p><div class="actions"><a class="button" href="metroidvania/index.html">Play both model games</a><a href="metroidvania-pilot.html">Read checks and limitations →</a></div>'''
    (output/'index.html').write_text(page('Agent-first programming',body),encoding='utf-8')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    print(json.dumps({'status':'built','site':str(output),'wasm_bytes':len(binary),'evidence':manifest['evidence']}))


if __name__=='__main__':main()
