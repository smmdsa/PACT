"""Loading preserves source identity; semantic upgrades are explicit."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from benchmarks.token_counts import measure_pair
from pact.compact import dumps, loads
from pact.graph import load_document
from pact.module import analyze_module, migrate_module
from pact.module_wasm import compile_module
from pact.revision import revision
from pact.transactions import apply_patch
from tests.test_module import tiny
from tests.test_token_counts import RecordingEncoding

ROOT = Path(__file__).resolve().parents[1]


class MigrationCompatibilityTests(unittest.TestCase):
    def test_default_load_preserves_legacy_ir_revision_and_wasm(self):
        original = tiny()
        with tempfile.TemporaryDirectory() as directory:
            for name, source in [('legacy.json', json.dumps(original)), ('legacy.pact', dumps(original))]:
                path = Path(directory) / name
                path.write_text(source, encoding='utf-8')
                restored = load_document(path)
                self.assertEqual(restored, original)
                self.assertEqual(revision(restored), revision(original))
                self.assertEqual(compile_module(analyze_module(restored)), compile_module(analyze_module(original)))
                self.assertEqual(load_document(path, migrate_legacy=True), migrate_module(original))
        self.assertEqual(loads(dumps(original)), original)
        self.assertEqual(loads(dumps(original), migrate_legacy=True), migrate_module(original))
        self.assertEqual(compile_module(analyze_module(migrate_module(original))),
                         compile_module(analyze_module(original)))

    def test_inline_literals_preserve_both_numeric_module_versions(self):
        for original in (tiny(), migrate_module(tiny())):
            with self.subTest(format=original['format']):
                original['functions'][0]['nodes'][2] = {'id': 'a', 'op': 'i32.const', 'value': 7}
                source = dumps(original, inline=True)
                self.assertIn('a=7', source)
                self.assertEqual(loads(source), original)
                self.assertEqual(revision(loads(source)), revision(original))

    def test_frozen_game_sources_and_original_patch_remain_compatible(self):
        document = load_document(ROOT / 'examples/alien-harvest.pact')
        self.assertEqual(document['format'], 'pact.module/0.1.0')
        self.assertEqual(document, load_document(ROOT / 'examples/alien-harvest.pact.json'))
        baseline_wasm = compile_module(analyze_module(document))
        for suffix in ('data.pact', 'inline.pact'):
            restored = load_document(ROOT / f'examples/alien-harvest.{suffix}')
            self.assertEqual(document, restored)
            self.assertEqual(compile_module(analyze_module(restored)), baseline_wasm)
        patch = json.loads((ROOT / 'examples/patches/jump.patch.json').read_text())
        self.assertEqual(patch['expected_revision_sha256'], revision(document))
        candidate = apply_patch(document, patch)
        self.assertEqual(candidate['format'], document['format'])
        self.assertNotEqual(revision(candidate), revision(document))

    def test_frozen_token_hashes_still_describe_checked_in_snapshots(self):
        for report_name, source_name in [('o200k_base.json', 'alien-harvest.pact'),
                                          ('data-o200k_base.json', 'alien-harvest.data.pact')]:
            report = json.loads((ROOT / 'benchmarks/results' / report_name).read_text())
            if report_name.startswith('data-'):
                records = {row['representation']: row for row in report['results']}
                row = {'compact': records['compact_0_3'], 'minified_json': records['minified_json']}
            else:
                row = next(row for row in report['results'] if row['example'] == 'alien-harvest')
            encoding = RecordingEncoding()
            measured = measure_pair('alien-harvest', ROOT / 'examples' / source_name,
                                    ROOT / 'examples/alien-harvest.pact.json', encoding)
            self.assertEqual(measured['compact']['sha256'], row['compact']['sha256'])
            self.assertEqual(measured['minified_json']['sha256'], row['minified_json']['sha256'])
            self.assertEqual(encoding.inputs[0], (ROOT / 'examples' / source_name).read_text())
            self.assertEqual(hashlib.sha256(encoding.inputs[1].encode()).hexdigest(), row['minified_json']['sha256'])
