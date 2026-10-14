import hashlib
import importlib
import io
import json
import shutil
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


class RuntimePerformanceTests(unittest.TestCase):
    def benchmark(self):
        try:
            return importlib.import_module('benchmarks.runtime_performance')
        except ImportError:
            self.fail('Runtime performance benchmark missing')

    def test_independent_oracle_covers_odd_calls_and_wrap(self):
        benchmark = self.benchmark()
        self.assertEqual(benchmark.oracle(1)['state'], [-2147483647, -2147483647])
        self.assertEqual(benchmark.oracle(1000)['state'], [-2147482150, -2147482147])
        with self.assertRaisesRegex(benchmark.BenchmarkError, 'oracle'):
            benchmark.verify_sample({'state':[0, 0], 'checksum':0, 'elapsed_ns':1, 'pid':1}, 1000)

    def test_corrupt_checksum_and_noninteger_state_are_rejected(self):
        benchmark = self.benchmark()
        valid = {**benchmark.oracle(1), 'elapsed_ns': 1, 'pid': 1}
        for change in ({'checksum': 0}, {'state': [-2147483647.0, -2147483647]},
                       {'checksum': float(valid['checksum'])}, {'elapsed_ns': -1}, {'pid': 0}):
            with self.subTest(change=change), self.assertRaises(benchmark.BenchmarkError):
                benchmark.verify_sample({**valid, **change}, 1)

    @unittest.skipUnless(shutil.which('node'), 'Node required for actual Wasm')
    def test_actual_runs_validate_states_checksums_and_provenance(self):
        benchmark = self.benchmark()
        report = benchmark.make_report(iterations=1000, samples=2, require_c=bool(shutil.which('gcc')))
        self.assertEqual(report['iterations'], 1000)
        self.assertEqual(report['samples'], 2)
        self.assertEqual(report['warmup_iterations'], 1000)
        self.assertIn('cpu_model', report['environment'])
        self.assertIn('python', report['runtime_versions'])
        self.assertEqual(len(report['results']), 4)
        pids = []
        for row in report['results']:
            if row['status'] == 'skipped':
                self.assertEqual(row['language'], 'c')
                continue
            self.assertEqual(row['status'], 'verified')
            self.assertEqual(len(row['runs']), 2)
            for sample in row['runs']:
                self.assertEqual(sample['state'], [-2147482150, -2147482147])
                self.assertEqual(sample['checksum'], 5995)
                self.assertIsInstance(sample['elapsed_ns'], int)
                pids.append(sample['pid'])
            for key in ('source', 'harness'):
                entry = row[key]
                data = (benchmark.ROOT / entry['path']).read_bytes()
                self.assertEqual(entry['sha256'], hashlib.sha256(data).hexdigest())
            if row['language'] in ('pact', 'c'):
                self.assertEqual(len(row['binary']['sha256']), 64)
                self.assertGreater(row['binary']['bytes'], 0)
            for key in ('min_ns', 'median_ns', 'p95_ns'):
                self.assertIsInstance(row['timing'][key], (int, float))
        self.assertEqual(len(pids), len(set(pids)))

    def test_bounds_and_dependency_failures_are_explicit(self):
        benchmark = self.benchmark()
        for iterations, samples in ((0, 1), (10000001, 1), (1, 0), (1, 21), (True, 1)):
            with self.subTest(iterations=iterations, samples=samples):
                with self.assertRaises(benchmark.BenchmarkError):
                    benchmark.make_report(iterations=iterations, samples=samples)
        real_which = shutil.which
        with patch.object(benchmark.shutil, 'which', side_effect=lambda name: None if name == 'gcc' else real_which(name)):
            with self.assertRaisesRegex(benchmark.BenchmarkError, 'gcc'):
                benchmark.make_report(iterations=1, samples=1, require_c=True)
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            self.assertEqual(benchmark.main(['--iterations', '0']), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(json.loads(error.getvalue())['code'], 'INVALID_PARAMETERS')
