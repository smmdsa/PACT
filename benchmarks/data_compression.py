"""Measure three equivalent representations without changing execution semantics."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from benchmarks.token_counts import BenchmarkError, TIKTOKEN_VERSION, _load_snapshot, _read_source, load_tokenizer
from pact.diagnostics import PactError
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.revision import revision

ROOT = Path(__file__).resolve().parents[1]


def report(encoding):
    document = _load_snapshot(_read_source(ROOT/'examples/alien-harvest.pact.json'), 'game.json')
    snapshots = {'minified_json':json.dumps(document,ensure_ascii=False,separators=(',',':')).encode(),
                 'compact_0_2':_read_source(ROOT/'examples/alien-harvest.pact'),
                 'compact_0_3':_read_source(ROOT/'examples/alien-harvest.data.pact')}
    binary = compile_module(analyze_module(document))
    rows = []
    for name, source in snapshots.items():
        restored = _load_snapshot(source, 'source.json' if name=='minified_json' else 'source.pact')
        if restored != document or compile_module(analyze_module(restored)) != binary:
            raise BenchmarkError('REPRESENTATION_MISMATCH', f'{name}: IR or Wasm differs')
        rows.append({'representation':name,'bytes':len(source),
                     'tokens':len(encoding.encode_ordinary(source.decode('utf-8'))),
                     'sha256':hashlib.sha256(source).hexdigest()})
    return {'format':'pact.data-compression-baseline/0.1.0','example':'alien-harvest',
            'tokenizer':{'package':'tiktoken','version':TIKTOKEN_VERSION,'encoding':encoding.name},
            'scope':'exact equivalent sources; excludes prompts, tools and model edits',
            'agent_task_trials_run':False,'same_ir':True,'same_wasm':True,
            'semantic_revision_sha256':revision(document),
            'wasm_sha256':hashlib.sha256(binary).hexdigest(),'results':rows}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoding',choices=['o200k_base','cl100k_base'],default='o200k_base')
    args=parser.parse_args(argv)
    try:
        print(json.dumps(report(load_tokenizer(args.encoding)),ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (BenchmarkError,PactError,OSError,UnicodeError) as error:
        diagnostic=error.diagnostic if isinstance(error,PactError) else {
            'status':'rejected','code':getattr(error,'code','BENCHMARK_IO'),'message':str(error)}
        print(json.dumps(diagnostic),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
