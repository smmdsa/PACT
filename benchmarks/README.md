# Efficiency benchmarks

`python3 -m benchmarks.source_sizes` reports UTF-8 byte sizes and validates equivalent sources. Bytes are not tokens.

## Reproducible representation token baseline

From the repository root, install the optional tokenizer separately from the dependency-free compiler:

```sh
python3 -m pip install --target /tmp/pact-benchmark-deps -r benchmarks/requirements.txt
PYTHONPATH=/tmp/pact-benchmark-deps TIKTOKEN_CACHE_DIR=/tmp/pact-tiktoken-cache python3 -m benchmarks.token_counts --encoding o200k_base
PYTHONPATH=/tmp/pact-benchmark-deps TIKTOKEN_CACHE_DIR=/tmp/pact-tiktoken-cache python3 -m benchmarks.token_counts --encoding cl100k_base
```

These POSIX commands use `tiktoken==0.12.0`. First use downloads encoding resources; subsequent runs can reuse that cache. Missing dependencies, a different tokenizer version or unavailable resources produce a diagnostic and a nonzero exit code. There is no byte-based fallback. Unit tests use an injected recording encoder to exercise boundaries without installing the optional dependency; their counts are not measurement results.

The benchmark validates both representations and requires identical IR before counting. It measures the exact checked-in compact UTF-8 file, including comments and line endings, versus `json.dumps(document, ensure_ascii=False, separators=(',', ':'))` without a trailing newline. JSON object order is preserved. Each representation records its SHA256, bytes and actual `encode_ordinary` token count. Special-token-looking source strings are ordinary text. Output order and formatting are deterministic. Encoding names do not imply a model assignment.

Measured on 2026-10-14, with raw reports in [results/o200k_base.json](results/o200k_base.json) and [results/cl100k_base.json](results/cl100k_base.json):

| Encoding | Example | Compact tokens | Minified JSON tokens |
| --- | --- | ---: | ---: |
| o200k_base | hello | 105 | 135 |
| o200k_base | alien-harvest | 24,851 | 35,903 |
| cl100k_base | hello | 107 | 133 |
| cl100k_base | alien-harvest | 24,840 | 35,876 |

These counts exclude prompts, tool framing, model output and repair cycles. They describe these two sources, not agent task success, cost or general language efficiency. No agent-success trials were run.

The separate `selective_context` report measures `pact inspect examples/alien-harvest.pact --function player.move` using the exact CLI JSON serialization plus its terminating newline. It includes context-only/buildable flags and omitted-data categories. This is a contextual subset with omitted data, not an equivalent executable representation; its size cannot establish that an agent has enough information for a task. The report's hash permits comparison with captured CLI output.

| Context | UTF-8 bytes | o200k_base tokens | cl100k_base tokens |
| --- | ---: | ---: | ---: |
| alien-harvest / player.move | 17,340 | 6,229 | 6,076 |

## Future task protocol (not executed)

Freeze the repository revision, baseline source hashes, task text, verifier, model/version/settings, tokenizer/version, tool schemas, context policy, budgets and trial count before starting. Run at least five independent fresh trials per task and representation, randomize order, and retain every failure and retry. Give compact and JSON trials the same task and semantic tool capabilities. Edit only a disposable candidate source; keep the baseline and verifier outside the agent's writable files. Do not run `tools/make_game.py`, which would overwrite authored changes.

Two minimal tasks with independent executable acceptance criteria:

| ID | Editable baseline | Exact instruction | Acceptance |
| --- | --- | --- | --- |
| greeting | `examples/hello.pact` or equivalent `.pact.json` | Change the greeting prefix to `hello world, `; preserve the suffix and IDs and update its exact-output contract. | Candidate IR equals baseline with only node `v0` and contract `c0` values changed; compiled Wasm stdout is exactly `hello world, from an alien language\n`. |
| jump | `examples/alien-harvest.pact` or equivalent `.pact.json` | Set `player.jump` to -1792 and update `jump.grounded` expected vertical velocity; preserve every other semantic field. | Candidate IR equals baseline with only those two values changed; build executes declared tests against actual Wasm, and an independently supplied grounded-jump probe observes `player.vy == [-1792]`. |

Run this frozen verifier from the repository root with task ID and candidate path. It accepts either representation and judges execution rather than an agent's assertions:

```sh
python3 - greeting /tmp/candidate.pact <<'PY'
import json, subprocess, sys, tempfile
from pathlib import Path
from pact.compact import validate_document
from pact.graph import load_document
from pact.module_build import build_module
from tests.test_module_execution import execute

task, candidate_path = sys.argv[1:]
assert task in ('greeting', 'jump')
name = 'hello' if task == 'greeting' else 'alien-harvest'
expected = load_document(Path('examples') / (name + '.pact.json'))
candidate = load_document(candidate_path)
validate_document(candidate)
if task == 'greeting':
    next(n for n in expected['nodes'] if n['id'] == 'v0')['value'] = 'hello world, '
    next(c for c in expected['contracts'] if c['id'] == 'c0')['value'] = 'hello world, from an alien language\n'
    assert candidate == expected, 'Unexpected semantic changes'
    with tempfile.TemporaryDirectory() as directory:
        wasm = Path(directory) / 'candidate.wasm'
        built = subprocess.run([sys.executable, '-m', 'pact', 'build', candidate_path, '-o', str(wasm)], capture_output=True, timeout=15)
        assert built.returncode == 0, built.stderr
        run = subprocess.run(['node', 'host/run.mjs', str(wasm), '--allow', 'stdout'], capture_output=True, timeout=15)
        assert run.returncode == 0, run.stderr
        assert run.stdout == b'hello world, from an alien language\n'
else:
    expected['constants']['player.jump'] = -1792
    next(t for t in expected['tests'] if t['id'] == 'jump.grounded')['expect']['player.vy'] = [-1792]
    assert candidate == expected, 'Unexpected semantic changes'
    build_module(candidate)
    run, _ = execute(candidate, [{'fn': 'player.move', 'set': {'player.grounded': [1], 'input.jump': [1]}}])
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)['state']['player.vy'] == [-1792]
print('accepted')
PY
```

Change `greeting` to `jump` for the second task. Do not use `python -O`, which disables the verifier's assertions. The existing `execute` helper instantiates compiled Wasm in Node and reads final state; it does not substitute reference-VM assertions.

Verifier self-checks on 2026-10-14 accepted independently authored greeting and jump candidates in both compact and JSON formats. These four probes validate the checker workflow; they are not agent-success trials.

Record complete prompts, source/tool responses, output tokens, repair cycles, elapsed time, provider usage/cost and final verifier status per trial. Report success rates with all trials and failures, and token totals including tool interactions. The representation baseline above is separate from these future task results. Conventional-language comparisons require equivalent behavior and selective tool capabilities before any efficiency claim.
