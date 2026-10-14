"""Execute frozen small kernels and count complete sources and separate drivers."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from benchmarks.token_counts import BenchmarkError, TIKTOKEN_VERSION, load_tokenizer
from pact.diagnostics import PactError
from pact.graph import load_document
from pact.module_build import build_module

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT/'benchmarks/traditional'
LANGUAGES = {'pact':'.pact', 'python':'.py', 'javascript':'.mjs', 'c':'.c'}


def measure_bytes(source, encoding):
    return {'bytes':len(source), 'tokens':len(encoding.encode_ordinary(source.decode('utf-8'))),
            'sha256':hashlib.sha256(source).hexdigest()}


def measure_file(path, encoding):
    return measure_bytes(Path(path).read_bytes(), encoding)


def verify_trace(task, language, actual, expected):
    if actual != expected:
        raise BenchmarkError('TRACE_MISMATCH', f'{task}/{language}: output differs from frozen expected trace')


def run(command, stdin=b''):
    try:
        result = subprocess.run(command, input=stdin, capture_output=True, timeout=15, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BenchmarkError('EXECUTION_FAILED', f'{command[0]}: {error}') from None
    if result.returncode or result.stderr:
        raise BenchmarkError('EXECUTION_FAILED', f'{command[0]} exited {result.returncode}: '
                             + result.stderr.decode('utf-8', errors='replace'))
    return result.stdout


def execute_suite(require_c=False):
    if not shutil.which('node'):
        raise BenchmarkError('RUNTIME_MISSING', 'Node is required for JavaScript and actual PACT Wasm execution')
    gcc = shutil.which('gcc')
    if require_c and not gcc:
        raise BenchmarkError('RUNTIME_MISSING', 'gcc is required by --require-c')
    cases = json.loads((FIXTURES/'cases.json').read_bytes())
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for task in ('greeting', 'counter'):
            stdin = (''.join(f'{index} {amount}\n' for index, amount in cases[task].get('calls', []))).encode()
            expected = cases[task]['stdout'].encode('utf-8')
            for language, suffix in LANGUAGES.items():
                row = {'task':task, 'language':language}
                source = FIXTURES/(task+suffix)
                if language == 'c' and not gcc:
                    rows.append({**row, 'status':'skipped', 'reason':'gcc unavailable'})
                    continue
                if language == 'pact':
                    binary = work/(task+'.wasm')
                    if task == 'greeting':
                        run([sys.executable, '-m', 'pact', 'build', str(source), '-o', str(binary)])
                        command = ['node', str(ROOT/'host/run.mjs'), str(binary), '--allow', 'stdout']
                    else:
                        artifact, manifest = build_module(load_document(source))
                        binary.write_bytes(artifact)
                        manifest_path = work/'counter.manifest.json'
                        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                        command = ['node', str(FIXTURES/'counter-driver-pact.mjs'), str(binary), str(manifest_path)]
                elif language == 'python':
                    command = [sys.executable, str(source if task=='greeting' else FIXTURES/'counter-driver.py')]
                elif language == 'javascript':
                    command = ['node', str(source if task=='greeting' else FIXTURES/'counter-driver.mjs')]
                else:
                    executable = work/(task+'-c')
                    compile_command = [gcc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2', str(source)]
                    if task == 'counter':
                        compile_command.append(str(FIXTURES/'counter-driver.c'))
                    run(compile_command+['-o', str(executable)])
                    command = [str(executable)]
                actual = run(command, stdin)
                verify_trace(task, language, actual, expected)
                rows.append({**row, 'status':'verified', 'stdout':actual.decode('utf-8'),
                             'trace_sha256':hashlib.sha256(actual).hexdigest()})
    return rows


def make_report(encoding, require_c=False):
    executions = execute_suite(require_c)
    rows = []
    for execution in executions:
        task, language = execution['task'], execution['language']
        source = FIXTURES/(task+LANGUAGES[language])
        if task == 'greeting':
            drivers = [ROOT/'host/run.mjs'] if language=='pact' else []
        else:
            driver = 'counter-driver-pact.mjs' if language=='pact' else 'counter-driver'+LANGUAGES[language]
            drivers = [FIXTURES/driver]
        row = {**execution, 'source':{'path':str(source.relative_to(ROOT)), **measure_file(source, encoding)},
               'drivers':[{'path':str(path.relative_to(ROOT)), **measure_file(path, encoding)} for path in drivers]}
        if language == 'pact':
            # This is an overlapping annotated subset, never an additive decomposition.
            prefixes = (b'responsibility ', b'effects ', b'contracts ', b'writes ', b'tests ', b'assets ', b'presentation ')
            subset = b''.join(line for line in source.read_bytes().splitlines(keepends=True) if line.startswith(prefixes))
            row['policy_metadata_subset'] = {**measure_bytes(subset, encoding), 'overlaps_source':True,
                                             'scope':'exact complete declaration lines; not separable token savings'}
        rows.append(row)
    return {
        'format':'pact.traditional-comparison/0.1', 'metric':'source_tokens',
        'tokenizer':{'package':'tiktoken', 'version':TIKTOKEN_VERSION, 'encoding':encoding.name},
        'scope':'complete exact UTF-8 files including whitespace and final newline; drivers counted separately',
        'agent_task_trials_run':False, 'equivalent_security_contracts':False,
        'oracle':{'path':'benchmarks/traditional/cases.json', **measure_file(FIXTURES/'cases.json', encoding)},
        'harness':{'path':'benchmarks/traditional.py', **measure_file(Path(__file__), encoding)},
        'validation_runner':{'path':'tools/check_module.mjs', **measure_file(ROOT/'tools/check_module.mjs', encoding)},
        'runtime_versions':{'python':sys.version.split()[0], 'node':run(['node','--version']).decode().strip(),
                            'gcc':run(['gcc','--version']).decode().splitlines()[0] if shutil.which('gcc') else None},
        'limitations':[
            'Two small chosen kernels are not representative of languages or the full game.',
            'Equal frozen traces cover only the listed signed-i32 inputs, not equivalent capabilities, tests or safety.',
            'PACT includes checked declarations and a contract/test; other sources do not implement that policy.',
            'Driver and harness measurements exclude runtime/compiler/library binaries, prompts and tool framing.',
            'Source and driver token counts are independent; tokenization of concatenations is not additive.',
            'No editing, debugging, real-model productivity, timing or total task-cost experiment was run.'
        ],
        'results':rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoding', choices=('o200k_base','cl100k_base'), default='o200k_base')
    parser.add_argument('--require-c', action='store_true', help='fail instead of recording skipped C execution when gcc is absent')
    args = parser.parse_args(argv)
    try:
        report = make_report(load_tokenizer(args.encoding), args.require_c)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (BenchmarkError, PactError, OSError, UnicodeError, ValueError) as error:
        diagnostic = error.diagnostic if isinstance(error, PactError) else {
            'status':'rejected', 'code':getattr(error, 'code', 'BENCHMARK_IO'), 'message':str(error)}
        print(json.dumps(diagnostic, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
