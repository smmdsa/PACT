"""Compile checked examples and create a dependency-free GitHub Pages site."""
import html
import json
import shutil
from pathlib import Path

from pact.browser import game_html
from pact.graph import load_document
from pact.module_build import build_module
from pact.__main__ import main as pact_cli

ROOT = Path(__file__).resolve().parents[1]
STYLE = '''
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#10121c;color:#e9edf5;font:17px/1.65 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:48px 24px}a{color:#a8c7ff}nav{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:54px}nav a{text-decoration:none}h1{font-size:clamp(44px,8vw,78px);line-height:1.05;letter-spacing:-3px;margin:18px 0}h2{line-height:1.2}p{max-width:760px}.tag{color:#bda8ff;letter-spacing:2px;font-size:13px;text-transform:uppercase}.lead{font-size:22px;color:#b6bfd4}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px;margin:34px 0}table{border-collapse:collapse;width:100%;max-width:760px;margin:24px 0}td,th{text-align:left;padding:10px;border-bottom:1px solid #30394e}.card{background:#1a1e2e;border:1px solid #30394e;border-radius:12px;padding:24px}.card strong{font-size:27px;display:block}.button{display:inline-block;background:#adbcff;color:#13162a;border-radius:8px;padding:12px 22px;text-decoration:none;font-weight:700;margin:8px 12px 8px 0}pre{font:14px/1.7 ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#181c2a;border:1px solid #30394e;border-radius:12px;padding:24px}footer{border-top:1px solid #30394e;margin-top:50px;padding-top:20px;color:#aab4ca}small{color:#aab4ca}
'''


def page(title, body):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="description" content="PACT: explicit graphs, checked effects and compact agent-first source.">'
            f'<title>{html.escape(title)} · PACT</title><style>{STYLE}</style></head><body><main>'
            '<nav><a href="index.html">PACT</a><a href="syntax.html">Syntax</a>'
            '<a href="security.html">Security</a><a href="roadmap.html">Roadmap</a><a href="inspection.html">Agent tools</a>'
            '<a href="https://github.com/smmdsa/PACT">GitHub ↗</a></nav>' + body +
            '<footer>Experimental language · Compact frontend0.2 / data0.3 / inline0.4 · Graph 0.0.1 / module 0.2.0</footer>'
            '</main></body></html>')


def main():
    output = ROOT/'site-output'
    output.mkdir(exist_ok=True)
    game = load_document(ROOT/'examples/alien-harvest.data.pact')
    binary, manifest = build_module(game)
    (output/'game.wasm').write_bytes(binary)
    (output/'game.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'game.html').write_bytes(game_html(game,binary,manifest))
    if pact_cli(['build', str(ROOT/'examples/hello.pact'), '-o', str(output/'hello.wasm')]) != 0:
        raise RuntimeError('Greeting build failed.')
    for name in ('hello.pact','hello.pact.json','alien-harvest.pact','alien-harvest.pact.json','alien-harvest.data.pact'):
        shutil.copyfile(ROOT/'examples'/name,output/name)
    documents = [('syntax','docs/syntax.md'),('security','docs/security.md'),('roadmap','ROADMAP.md'),('inspection','docs/inspection.md'),('agents','docs/agent-contributions.md'),('benchmarks','benchmarks/README.md'),('transactions','docs/transactions.md'),('comparison','docs/traditional-comparison.md'),('resources','docs/resource-bounds.md'),('compression','docs/data-compression.md')]
    for slug, path in documents:
        text = (ROOT/path).read_text(encoding='utf-8')
        body = f'<h1>{slug.title()}</h1><p><a href="https://github.com/smmdsa/PACT/blob/main/{path}">View formatted document on GitHub ↗</a></p><pre>{html.escape(text)}</pre>'
        (output/f'{slug}.html').write_text(page(slug.title(),body),encoding='utf-8')
    hello = html.escape((ROOT/'examples/hello.pact').read_text(encoding='utf-8'))
    body = '''<span class="tag">Agent-first programming · research prototype</span>
<h1>Explicit intent.<br>Checked execution.</h1>
<p class="lead">PACT pairs compact source with a validated graph and deterministic WebAssembly. Explore the language through a real platformer.</p>
<a class="button" href="game.html">Play Alien Harvest</a><a href="syntax.html">Read the specification →</a>
<div class="grid"><div class="card"><strong>42% fewer bytes</strong>Compact game source versus minified JSON. Measured tokens: 24,851 versus 35,903 with o200k_base; full task cost remains unmeasured.</div><div class="card"><strong>Explicit effects</strong>Declared writes, bounded execution and checked array access.</div><div class="card"><strong>Same execution</strong>Compact and JSON sources reconstruct identical IR and Wasm.</div></div>
<h2>Hello from an alien language</h2>'''+f'<pre>{hello}</pre>'+'''
<p><a href="hello.pact" download>Download greeting source</a> · <a href="alien-harvest.pact" download>Download platformer source</a> · <a href="game.html" download>Download standalone game</a></p>
<h2>Run it locally</h2><pre>python3 -m pact build examples/hello.pact -o build/hello.wasm
node host/run.mjs build/hello.wasm --allow stdout</pre>
<p>Python 3.10+ and Node 20+. No third-party packages needed. The generated game HTML runs independently in a WebAssembly-capable browser.</p>
<h2>Inspect only what you need</h2><pre>python3 -m pact symbols examples/alien-harvest.pact
python3 -m pact inspect examples/alien-harvest.pact --function player.move</pre><p>Get stable function IDs, call dependencies, effects and relevant test summaries without the complete map and atlas. <a href="inspection.html">Inspection specification</a> · <a href="benchmarks.html">Benchmark protocol</a> · <a href="agents.html">Contribute with an agent</a></p><h2>Same game, less source context</h2><p>Bounded RLE and shared symbol maps reduce the game to 18,328 o200k_base tokens from 24,851. The IR, revision, atlas and Wasm are identical. <a href="compression.html">Data compression specification</a> · <a href="alien-harvest.data.pact" download>Compressed game source</a></p><h2>Checked changes, without overwriting source</h2><pre>python3 -m pact patch examples/alien-harvest.pact --patch examples/patches/jump.patch.json --dry-run</pre><p>Revision guards, full candidate validation and actual Wasm tests. <a href="transactions.html">Transaction specification →</a></p><h2>Traditional languages: measured honestly</h2><table><thead><tr><th>Source tokens · o200k_base</th><th>PACT</th><th>Python</th><th>JavaScript</th><th>C</th></tr></thead><tbody><tr><td>Greeting</td><td>78</td><td>10</td><td>11</td><td>27</td></tr><tr><td>Wrapping counter</td><td>163</td><td>74</td><td>76</td><td>138</td></tr></tbody></table><p>PACT costs more source tokens in these two kernels. Drivers are measured separately; the language policies differ. This is not an agent-productivity comparison. <a href="comparison.html">Methodology and full results →</a></p><h2>A concrete test of the language</h2><p>Alien Harvest includes jumping, climbing, throwable vegetables, enemies, a checkpoint and a boss. Its gameplay and internal pixel atlas are declared in PACT. The host supplies rendering, input and sound.</p>
<p><small>Prototype limitations: no proof of agent productivity, no general semantic responsibility checker, no full standard library or package manager. Real-browser compatibility and visual QA remain open. No open-source license has been selected yet.</small></p>'''
    (output/'index.html').write_text(page('Agent-first programming',body),encoding='utf-8')
    (output/'.nojekyll').write_text('',encoding='utf-8')
    print(json.dumps({'status':'built','site':str(output),'wasm_bytes':len(binary),'evidence':manifest['evidence']}))


if __name__ == '__main__':
    main()
