"""Time the trusted counter kernel in fresh processes, with independent validation."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
from time import perf_counter_ns

from pact.diagnostics import PactError
from pact.graph import load_document
from pact.module_build import build_module

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'benchmarks/traditional'
HARNESSES = ROOT / 'benchmarks/runtime'
SUFFIXES = {'pact': '.pact', 'python': '.py', 'javascript': '.mjs', 'c': '.c'}
C_FLAGS = ['-std=c11', '-O2', '-fno-lto', '-Wall', '-Wextra', '-Werror']


class BenchmarkError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate_parameters(iterations, samples):
    if type(iterations) is not int or not 1 <= iterations <= 10000000:
        raise BenchmarkError('INVALID_PARAMETERS', 'iterations must be an integer in 1..10000000')
    if type(samples) is not int or not 1 <= samples <= 20:
        raise BenchmarkError('INVALID_PARAMETERS', 'samples must be an integer in 1..20')


def oracle(iterations):
    """Closed-form call counts; does not execute or import any counter kernel."""
    counts = [(iterations + 1) // 2, iterations // 2]
    initial = [2147483646, -2147483647]
    state = [(value + 3 * count + 2**31) % 2**32 - 2**31
             for value, count in zip(initial, counts)]
    checksum = (3 * (state[0] % 2**32) + state[1] % 2**32) % 2**32
    return {'state': state, 'checksum': checksum}


def verify_sample(sample, iterations):
    expected = oracle(iterations)
    if (not isinstance(sample, dict) or sample.get('state') != expected['state']
            or sample.get('checksum') != expected['checksum']
            or any(type(value) is not int for value in sample.get('state', []))
            or type(sample.get('checksum')) is not int):
        raise BenchmarkError('ORACLE_MISMATCH', 'counter output differs from independent mathematical oracle')
    if (type(sample.get('elapsed_ns')) is not int or sample['elapsed_ns'] < 0
            or type(sample.get('pid')) is not int or sample['pid'] <= 0):
        raise BenchmarkError('INVALID_MEASUREMENT', 'sample requires nonnegative integer elapsed_ns and positive pid')


def run(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=120, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BenchmarkError('EXECUTION_FAILED', f'{command[0]}: {error}') from None
    if result.returncode or result.stderr:
        raise BenchmarkError('EXECUTION_FAILED', f'{command[0]} exited {result.returncode}: '
                             + result.stderr.decode('utf-8', errors='replace'))
    return result.stdout.decode('utf-8')


def file_record(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def binary_record(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def cpu_model():
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or None


def make_report(iterations=100000, samples=5, require_c=False):
    validate_parameters(iterations, samples)
    node, gcc = shutil.which('node'), shutil.which('gcc')
    if not node:
        raise BenchmarkError('RUNTIME_MISSING', 'Node is required for JavaScript and actual PACT Wasm execution')
    if require_c and not gcc:
        raise BenchmarkError('RUNTIME_MISSING', 'gcc is required by --require-c')
    started_at = datetime.now(timezone.utc).isoformat()
    wall_start = perf_counter_ns()
    warmup = min(iterations, 10000)
    versions = {'python': sys.version.split()[0], 'node': run([node, '--version']).strip(),
                'gcc': run([gcc, '--version']).splitlines()[0] if gcc else None}
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for language, suffix in SUFFIXES.items():
            source = FIXTURES / ('counter' + suffix)
            harness = HARNESSES / ('counter-pact.mjs' if language == 'pact' else 'counter' + suffix)
            row = {'language': language, 'source': file_record(source), 'harness': file_record(harness)}
            if language == 'c' and not gcc:
                rows.append({**row, 'status': 'skipped', 'reason': 'gcc unavailable'})
                continue
            if language == 'pact':
                artifact, manifest = build_module(load_document(source))
                binary = work / 'counter.wasm'
                binary.write_bytes(artifact)
                manifest_path = work / 'counter.manifest.json'
                manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
                row['binary'] = binary_record(binary)
                row['manifest_sha256'] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                command = [node, str(harness), str(binary), str(manifest_path)]
            elif language == 'c':
                binary = work / 'counter-c'
                run([gcc, *C_FLAGS, str(source), str(harness), '-o', str(binary)])
                row['binary'] = binary_record(binary)
                row['compiler_flags'] = C_FLAGS.copy()
                command = [str(binary)]
            else:
                row['binary'] = None
                row['binary_note'] = 'interpreted source; runtime binary is not included'
                command = [sys.executable if language == 'python' else node, str(harness)]
            runs = []
            for _ in range(samples):
                try:
                    sample = json.loads(run([*command, str(iterations), str(warmup)]))
                except json.JSONDecodeError as error:
                    raise BenchmarkError('INVALID_MEASUREMENT', f'{language}: invalid sample JSON: {error}') from None
                verify_sample(sample, iterations)
                runs.append(sample)
            durations = sorted(sample['elapsed_ns'] for sample in runs)
            timing = {'min_ns': min(durations), 'median_ns': statistics.median(durations),
                      'p95_ns': durations[math.ceil(0.95 * samples) - 1],
                      'p95_method': 'nearest rank: sorted[ceil(0.95*samples)-1]'}
            timing['median_ns_per_call'] = timing['median_ns'] / iterations
            rows.append({**row, 'status': 'verified', 'runs': runs, 'timing': timing})
    return {
        'format': 'pact.runtime-performance/0.1', 'metric': 'kernel_elapsed_ns',
        'started_at_utc': started_at, 'harness_wall_elapsed_ns': perf_counter_ns() - wall_start,
        'iterations': iterations, 'samples': samples, 'warmup_iterations': warmup,
        'workload': 'advance(i % 2, 1); signed-i32 initial state [2147483646,-2147483647]; three wrapping additions per call',
        'oracle': {**oracle(iterations), 'method': 'closed-form 3*ceil(N/2) and 3*floor(N/2) updates modulo 2^32'},
        'timed_scope': 'internal loop and calls only; PACT includes the JavaScript-to-Wasm export bridge',
        'excluded': ['compilation', 'process startup', 'module loading / Wasm instantiation', 'warmup',
                     'counter reset', 'final-state reading, checksum and output'],
        'sample_policy': 'every sample is a fresh process; warmup then reset initial counter outside timer',
        'timers': {'python': 'time.perf_counter_ns', 'pact': 'process.hrtime.bigint',
                   'javascript': 'process.hrtime.bigint', 'c': 'clock_gettime(CLOCK_MONOTONIC)'},
        'runtime_versions': versions,
        'environment': {'os': platform.system(), 'os_release': platform.release(),
                        'architecture': platform.machine(), 'cpu_model': cpu_model()},
        'harness': file_record(Path(__file__)),
        'compiler_sources': [file_record(path) for path in sorted((ROOT / 'pact').glob('*.py'))],
        'limitations': [
            'One chosen tiny counter kernel on one local machine does not establish universal language ranks or production performance.',
            'Five default samples are too few for a stable tail estimate; nearest-rank p95 equals the maximum for up to 19 samples.',
            'Loop overhead and host-call costs are included; PACT Wasm uses a JavaScript host bridge per call.',
            'Warmup length does not guarantee a particular JIT optimization tier; fresh processes may optimize during measurement.',
            'No CPU affinity, frequency control or isolation from other local workloads is applied.',
            'C uses GCC -O2 without LTO and separate kernel/harness translation units; compiler optimization differs across runtimes.',
            'Valid indices and amount 1 only; equal outputs do not establish equal safety contracts or invalid-input costs.',
            'Compilation and startup are excluded from kernel timings and included only in harness wall elapsed metadata.',
        ],
        'results': rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=100000, help='calls per sample, 1..10000000')
    parser.add_argument('--samples', type=int, default=5, help='fresh process samples, 1..20')
    parser.add_argument('--require-c', action='store_true', help='fail when gcc is unavailable')
    args = parser.parse_args(argv)
    try:
        report = make_report(args.iterations, args.samples, args.require_c)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (BenchmarkError, PactError, OSError, UnicodeError, ValueError) as error:
        diagnostic = error.diagnostic if isinstance(error, PactError) else {
            'status': 'rejected', 'code': getattr(error, 'code', 'BENCHMARK_IO'), 'message': str(error)}
        print(json.dumps(diagnostic, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
