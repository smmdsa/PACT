import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pact.compact import dumps
from pact.diagnostics import PactError
from pact.graph import load_document

ROOT = Path(__file__).resolve().parents[1]


class RecordingEncoding:
    name = 'test_encoding'

    def __init__(self):
        self.inputs = []

    def encode_ordinary(self, text):
        self.inputs.append(text)
        return [1, 2, 3]


class TokenCountsTests(unittest.TestCase):
    def benchmark(self):
        try:
            return importlib.import_module('benchmarks.token_counts')
        except ImportError:
            self.fail('Token benchmark has not been implemented')

    def test_counts_exact_utf8_sources_and_records_hashes(self):
        benchmark = self.benchmark()
        doc = load_document(ROOT/'examples/hello.pact.json')
        encoding = RecordingEncoding()
        with tempfile.TemporaryDirectory() as directory:
            compact = Path(directory)/'hello.pact'
            interchange = Path(directory)/'hello.json'
            source = ('# 雪\r\n' + dumps(doc).replace('\n', '\r\n')).encode('utf-8')
            compact.write_bytes(source)
            interchange.write_text(json.dumps(doc, indent=4), encoding='utf-8')
            result = benchmark.measure_pair('hello', compact, interchange, encoding)
        minified = json.dumps(doc, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        self.assertEqual(encoding.inputs, [source.decode('utf-8'), minified.decode('utf-8')])
        for key, data in [('compact', source), ('minified_json', minified)]:
            self.assertEqual(result[key], {'bytes': len(data), 'tokens': 3,
                                         'sha256': hashlib.sha256(data).hexdigest()})

    def test_rejects_different_valid_ir_before_counting(self):
        benchmark = self.benchmark()
        doc = load_document(ROOT/'examples/hello.pact.json')
        doc['nodes'][0]['value'] = 'different'
        doc['contracts'][0]['value'] = 'different' + doc['nodes'][1]['value']
        encoding = RecordingEncoding()
        with tempfile.TemporaryDirectory() as directory:
            interchange = Path(directory)/'hello.json'
            interchange.write_text(json.dumps(doc), encoding='utf-8')
            with self.assertRaisesRegex(benchmark.BenchmarkError, 'representations differ'):
                benchmark.measure_pair('hello', ROOT/'examples/hello.pact', interchange, encoding)
        self.assertEqual(encoding.inputs, [])

    def test_validates_the_same_compact_bytes_that_are_counted(self):
        benchmark = self.benchmark()
        changed = load_document(ROOT/'examples/hello.pact.json')
        changed['nodes'][0]['value'] = 'changed'
        changed['contracts'][0]['value'] = 'changed' + changed['nodes'][1]['value']
        encoding = RecordingEncoding()
        real_open = Path.open
        def snapshot_open(path, *args, **kwargs):
            if path == ROOT/'examples/hello.pact':
                return io.BytesIO(dumps(changed).encode('utf-8'))
            return real_open(path, *args, **kwargs)
        with patch.object(Path, 'open', snapshot_open):
            with self.assertRaisesRegex(benchmark.BenchmarkError, 'representations differ'):
                benchmark.measure_pair('hello', ROOT/'examples/hello.pact', ROOT/'examples/hello.pact.json', encoding)
        self.assertEqual(encoding.inputs, [])

    def test_rejects_equally_invalid_ir_before_counting(self):
        benchmark = self.benchmark()
        doc = load_document(ROOT/'examples/hello.pact.json')
        doc['entry'] = 'missing'
        encoding = RecordingEncoding()
        with tempfile.TemporaryDirectory() as directory:
            compact, interchange = Path(directory)/'bad.pact', Path(directory)/'bad.json'
            # Use a metadata alteration whose raw compact form needs no validation to author.
            source = (ROOT/'examples/hello.pact').read_text()
            source = '\n'.join('entry "missing"' if line.startswith('entry ') else line for line in source.split('\n'))
            compact.write_text(source, encoding='utf-8')
            interchange.write_text(json.dumps(doc), encoding='utf-8')
            with self.assertRaises(PactError):
                benchmark.measure_pair('bad', compact, interchange, encoding)
        self.assertEqual(encoding.inputs, [])

    def test_dependency_and_resource_diagnostics(self):
        benchmark = self.benchmark()
        with patch.object(benchmark.importlib, 'import_module', side_effect=ImportError('missing')):
            with self.assertRaisesRegex(benchmark.BenchmarkError, 'requirements.txt'):
                benchmark.load_tokenizer('o200k_base')
        with patch.object(benchmark.importlib, 'import_module') as imported, \
             patch.object(benchmark.metadata, 'version', return_value=benchmark.TIKTOKEN_VERSION):
            imported.return_value.get_encoding.side_effect = OSError('offline')
            with self.assertRaisesRegex(benchmark.BenchmarkError, 'resources'):
                benchmark.load_tokenizer('o200k_base')

    def test_wrong_version_is_not_silently_used(self):
        benchmark = self.benchmark()
        with patch.object(benchmark.importlib, 'import_module'), \
             patch.object(benchmark.metadata, 'version', return_value='0.0.0'):
            with self.assertRaisesRegex(benchmark.BenchmarkError, benchmark.TIKTOKEN_VERSION):
                benchmark.load_tokenizer('o200k_base')

    def test_context_counts_exact_cli_serialization_as_nonbuildable_subset(self):
        benchmark = self.benchmark()
        self.assertTrue(callable(getattr(benchmark, 'measure_context', None)), 'Selective context measurement missing')
        encoding = RecordingEncoding()
        source = ROOT/'examples/alien-harvest.pact'
        cli = subprocess.run([sys.executable, '-m', 'pact', 'inspect', str(source), '--function', 'player.move'],
                             cwd=ROOT, capture_output=True, check=True)
        result = benchmark.measure_context('alien-harvest', source, 'player.move', encoding)
        self.assertEqual(encoding.inputs, [cli.stdout.decode('utf-8')])
        self.assertEqual(result['bytes'], len(cli.stdout))
        self.assertEqual(result['sha256'], hashlib.sha256(cli.stdout).hexdigest())
        self.assertEqual(result['tokens'], 3)
        self.assertTrue(result['context_only'])
        self.assertFalse(result['buildable'])
        self.assertEqual(result['function'], 'player.move')
        self.assertIn('cell_initial_values', result['omitted'])

    def test_cli_is_deterministic_and_has_no_success_claim(self):
        benchmark = self.benchmark()
        outputs = []
        for _ in range(2):
            output = io.StringIO()
            with patch.object(benchmark, 'load_tokenizer', return_value=RecordingEncoding()), redirect_stdout(output):
                self.assertEqual(benchmark.main([]), 0)
            outputs.append(output.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        report = json.loads(outputs[0])
        self.assertEqual(report['tokenizer'], {'package': 'tiktoken', 'version': benchmark.TIKTOKEN_VERSION,
                                               'encoding': 'test_encoding'})
        self.assertEqual(report['metric'], 'representation_tokens')
        self.assertEqual([row['example'] for row in report['results']], ['hello', 'alien-harvest'])
        self.assertFalse(report['agent_task_trials_run'])
        self.assertEqual(report['selective_context'][0]['function'], 'player.move')

    def test_cli_failure_emits_diagnostic_without_counts(self):
        benchmark = self.benchmark()
        output, error = io.StringIO(), io.StringIO()
        with patch.object(benchmark, 'load_tokenizer', side_effect=benchmark.BenchmarkError('TOKENIZER_MISSING', 'missing')), \
             redirect_stdout(output), redirect_stderr(error):
            self.assertEqual(benchmark.main([]), 1)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(json.loads(error.getvalue())['code'], 'TOKENIZER_MISSING')
