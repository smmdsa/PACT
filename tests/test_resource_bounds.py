import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks import token_counts
from pact.compact import _values, dumps, loads
from pact.diagnostics import PactError
from pact.graph import load_document
from pact.schema import MAX_SOURCE_BYTES

ROOT = Path(__file__).resolve().parents[1]


class RecordingEncoding:
    def __init__(self):
        self.inputs = []

    def encode_ordinary(self, text):
        self.inputs.append(text)
        return [1]


class SuffixGuard(str):
    """Reject large suffix copies, independent of elapsed time or platform."""
    def strip(self, *args):
        return SuffixGuard(super().strip(*args))

    def lstrip(self, *args):
        return SuffixGuard(super().lstrip(*args))

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop, step = key.indices(len(self))
            if start > 0 and stop - start > 128:
                raise AssertionError('long remaining suffix copied')
        return super().__getitem__(key)

    def split(self, *args, **kwargs):
        parts = super().split(*args, **kwargs)
        if len(parts) == 2 and len(parts[1]) > 128:
            raise AssertionError('long remaining suffix copied')
        return parts


class ResourceBoundsTests(unittest.TestCase):
    def test_long_operand_list_does_not_copy_remaining_suffixes(self):
        for token in ('node:0', '"node:0"'):
            with self.subTest(token=token):
                self.assertEqual(_values(SuffixGuard(' '.join([token] * 10000))), ['node:0'] * 10000)

    def test_json_error_location_remains_relative_to_operand(self):
        with self.assertRaises(json.JSONDecodeError) as raised:
            _values('node:0 "unterminated')
        self.assertEqual(str(raised.exception), 'Unterminated string starting at: line 1 column 1 (char 0)')

    def test_operand_lexical_boundaries_preserved(self):
        self.assertEqual(_values(' \t"雪\\n# = :"\u2028node:0\u0085-12  ["a:b", "c"]  '),
                         ['雪\n# = :', 'node:0', -12, ['a:b', 'c']])
        self.assertEqual(_values('"before\u2028after" "quoted:ref" []'),
                         ['before\u2028after', 'quoted:ref', []])
        for source in ('"a"b', '[]node', '12node', 'node, other', '{"a":1,"a":2}', '"unterminated'):
            with self.subTest(source=source), self.assertRaises((PactError, ValueError)):
                _values(source)

    def test_quoted_colon_reference_roundtrip(self):
        doc = load_document(ROOT / 'examples/hello.pact.json')
        doc['nodes'][0]['id'] = 'value:0'
        doc['nodes'][2]['args'][0] = 'value:0'
        source = dumps(doc).replace('utf8.concat value:0', 'utf8.concat "value:0"')
        self.assertEqual(loads(source), doc)

    def test_oversized_sources_read_only_limit_plus_one_and_never_tokenize(self):
        for oversized in ('compact', 'json'):
            with self.subTest(oversized=oversized), tempfile.TemporaryDirectory() as directory:
                compact, interchange = Path(directory)/'source.pact', Path(directory)/'source.json'
                doc = load_document(ROOT/'examples/hello.pact.json')
                compact.write_text(dumps(doc), encoding='utf-8')
                interchange.write_text(json.dumps(doc), encoding='utf-8')
                target = compact if oversized == 'compact' else interchange
                target.write_bytes(b'x' * (MAX_SOURCE_BYTES * 3))
                opened = []
                real_open = Path.open

                class TrackingReader:
                    def __init__(self, stream):
                        self.stream = stream
                        self.consumed = 0
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        self.stream.close()
                    def read(self, size=-1):
                        result = self.stream.read(size)
                        self.consumed += len(result)
                        return result

                def tracking_open(path, *args, **kwargs):
                    stream = real_open(path, *args, **kwargs)
                    if path == target:
                        stream = TrackingReader(stream)
                        opened.append(stream)
                    return stream

                encoding = RecordingEncoding()
                with patch.object(Path, 'open', tracking_open), self.assertRaises(PactError) as raised:
                    token_counts.measure_pair('bounded', compact, interchange, encoding)
                self.assertEqual(raised.exception.diagnostic['code'], 'SOURCE_LIMIT')
                self.assertEqual(raised.exception.diagnostic['message'], 'Source exceeds 1 MiB.')
                self.assertEqual(sum(reader.consumed for reader in opened), MAX_SOURCE_BYTES + 1)
                self.assertEqual(encoding.inputs, [])

    def test_counting_and_validation_use_single_snapshot_of_each_file(self):
        doc = load_document(ROOT/'examples/hello.pact.json')
        source = ('# 雪\r\n' + dumps(doc).replace('\n', '\r\n')).encode('utf-8')
        sources = {'snapshot.pact': source, 'snapshot.json': json.dumps(doc).encode('utf-8')}
        reads = []
        def snapshot_open(path, *args, **kwargs):
            reads.append(path.name)
            self.assertNotIn(path.name, reads[:-1], 'source reopened after validation')
            return io.BytesIO(sources[path.name])
        encoding = RecordingEncoding()
        with patch.object(Path, 'open', snapshot_open):
            result = token_counts.measure_pair('snapshot', 'snapshot.pact', 'snapshot.json', encoding)
        self.assertEqual(reads, ['snapshot.pact', 'snapshot.json'])
        self.assertEqual(encoding.inputs, [source.decode('utf-8'), json.dumps(doc, ensure_ascii=False, separators=(',', ':'))])
        self.assertEqual(result['compact']['bytes'], len(source))
