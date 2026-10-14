import hashlib
import importlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


class TraditionalComparisonTests(unittest.TestCase):
    def benchmark(self):
        try:
            return importlib.import_module('benchmarks.traditional')
        except ImportError:
            self.fail('Traditional-language benchmark missing')

    def test_exact_file_boundary_and_hash_including_newlines(self):
        benchmark = self.benchmark()
        class Encoding:
            def encode_ordinary(self, value):
                self.value = value
                return [1, 2]
        encoding = Encoding()
        source = '# 雪\r\nprint("<|endoftext|>")\r\n'.encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source.py'
            path.write_bytes(source)
            measured = benchmark.measure_file(path, encoding)
        self.assertEqual(encoding.value, source.decode())
        self.assertEqual(measured, {'bytes':len(source), 'tokens':2,
                                  'sha256':hashlib.sha256(source).hexdigest()})

    def test_windows_trace_transport_preserves_evidence_and_lone_carriage_returns(self):
        benchmark = self.benchmark()
        actual=b'ok 1 2\r\nodd\rvalue\r\n'
        with patch.object(benchmark.sys,'platform','win32'):
            self.assertEqual(benchmark.normalize_trace(actual), b'ok 1 2\nodd\rvalue\n')
        with patch.object(benchmark.sys,'platform','linux'):
            self.assertEqual(benchmark.normalize_trace(actual), actual)

    def test_frozen_oracle_rejects_jointly_wrong_implementations(self):
        benchmark = self.benchmark()
        for language in ('pact', 'python', 'javascript', 'c'):
            with self.subTest(language=language):
                with self.assertRaisesRegex(benchmark.BenchmarkError, 'frozen expected'):
                    benchmark.verify_trace('counter', language, b'ok 0 0\n', b'ok 1 0\n')

    @unittest.skipUnless(shutil.which('node'), 'Node required for real Wasm execution')
    def test_all_real_sources_match_frozen_traces(self):
        benchmark = self.benchmark()
        results = benchmark.execute_suite(require_c=bool(shutil.which('gcc')))
        expected = json.loads((benchmark.FIXTURES/'cases.json').read_text())
        self.assertEqual(len(results), 8)
        for row in results:
            if row['status'] == 'skipped':
                self.assertEqual(row['language'], 'c')
                continue
            self.assertEqual(row['status'], 'verified')
            self.assertEqual(row['stdout'], expected[row['task']]['stdout'])
        counter = expected['counter']
        self.assertEqual(counter['calls'][:4], [[0,1], [1,-1], [0,-2], [1,-2147483648]])
        self.assertIn('ok -2147483647 -2147483647\n', counter['stdout'])
        self.assertIn('ok 2147483643 -2\n', counter['stdout'])
        self.assertEqual(counter['stdout'].count('bounds 2147483643 -2\n'), 4)

    def test_missing_required_c_compiler_is_an_explicit_failure(self):
        benchmark = self.benchmark()
        real_which = shutil.which
        with patch.object(benchmark.shutil, 'which', side_effect=lambda name: None if name=='gcc' else real_which(name)):
            with self.assertRaisesRegex(benchmark.BenchmarkError, 'gcc'):
                benchmark.execute_suite(require_c=True)

    @unittest.skipUnless(shutil.which('node'), 'Node required for real Wasm execution')
    def test_changed_python_arithmetic_fails_the_independent_oracle(self):
        benchmark = self.benchmark()
        with tempfile.TemporaryDirectory() as directory:
            fixtures = Path(directory)/'fixtures'
            shutil.copytree(benchmark.FIXTURES, fixtures)
            source = fixtures/'counter.py'
            source.write_text(source.read_text().replace('range(3)', 'range(2)'))
            with patch.object(benchmark, 'FIXTURES', fixtures):
                with self.assertRaisesRegex(benchmark.BenchmarkError, 'counter/python.*frozen expected'):
                    benchmark.execute_suite()

    def test_cli_dependency_failure_emits_no_measurement(self):
        benchmark = self.benchmark()
        output, error = io.StringIO(), io.StringIO()
        with patch.object(benchmark, 'load_tokenizer', side_effect=benchmark.BenchmarkError('TOKENIZER_MISSING', 'missing')), \
             redirect_stdout(output), redirect_stderr(error):
            self.assertEqual(benchmark.main([]), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(json.loads(error.getvalue())['code'], 'TOKENIZER_MISSING')

    @unittest.skipUnless(shutil.which('node'), 'Node required for real Wasm execution')
    def test_report_counts_full_sources_and_separate_drivers(self):
        benchmark = self.benchmark()
        class Encoding:
            name = 'test_encoding'
            def encode_ordinary(self, text):
                return list(text)
        report = benchmark.make_report(Encoding())
        self.assertFalse(report['equivalent_security_contracts'])
        self.assertFalse(report['agent_task_trials_run'])
        for row in report['results']:
            source = (benchmark.ROOT/row['source']['path']).read_bytes()
            self.assertEqual(row['source']['sha256'], hashlib.sha256(source).hexdigest())
            self.assertEqual(row['source']['bytes'], len(source))
            self.assertEqual(row['source']['tokens'], len(source.decode()))
            for driver in row['drivers']:
                data = (benchmark.ROOT/driver['path']).read_bytes()
                self.assertEqual(driver['sha256'], hashlib.sha256(data).hexdigest())
            if row['language']=='pact':
                self.assertTrue(row['policy_metadata_subset']['overlaps_source'])
            elif row['task']=='greeting':
                self.assertEqual(row['drivers'], [])
