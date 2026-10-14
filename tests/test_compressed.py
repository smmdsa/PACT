import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.graph import analyze
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.revision import revision
from pact.wasm import compile_plan
from tools.make_game import game_document

ROOT = Path(__file__).resolve().parents[1]


class CompressedTests(unittest.TestCase):
    def compressed(self, document):
        try:
            return dumps(document, compressed=True)
        except TypeError:
            self.fail('Compressed frontend is not implemented')

    def test_exact_ir_revision_and_wasm_roundtrip(self):
        for name in ('hello','alien-harvest'):
            document = json.loads((ROOT/f'examples/{name}.pact.json').read_text())
            source = self.compressed(document)
            self.assertTrue(source.startswith('pact 0.3\n'))
            restored = loads(source)
            self.assertEqual(restored,document)
            self.assertEqual(revision(restored),revision(document))
            compiler, validator = (compile_module,analyze_module) if name=='alien-harvest' else (compile_plan,analyze)
            self.assertEqual(compiler(validator(restored)),compiler(validator(document)))
            self.assertEqual(dumps(document),(ROOT/f'examples/{name}.pact').read_text())

    def test_game_compresses_both_sections_and_malformed_sections_reject(self):
        document = json.loads((ROOT/'examples/alien-harvest.pact.json').read_text())
        source = self.compressed(document)
        self.assertIn('\ncells.packed ',source)
        self.assertIn('\nassets.shared ',source)
        self.assertLess(len(source.encode()),len(dumps(document).encode()))
        plain_cells = 'cells '+json.dumps(document['cells'])+'\n'
        packed_cells = next(line for line in source.split('\n') if line.startswith('cells.packed '))+'\n'
        variants = [source.replace('pact 0.3','pact 0.2',1),source+plain_cells,
                    dumps(document).replace('pact 0.2','pact 0.3',1)+packed_cells,
                    source.replace('params []','params []\n'+packed_cells.rstrip(),1)]
        for invalid in variants:
            with self.assertRaises(PactError):loads(invalid)

    def test_cli_conversion_and_existing_patch_accept_compressed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'game.pact'
            for args in [ ['convert','examples/alien-harvest.pact','--to','compact-data','-o',str(target)],
                          ['patch',str(target),'--patch','examples/patches/jump.patch.json','--dry-run'],
                          ['patch',str(target),'--patch','examples/patches/jump.patch.json','--to','compact-data','-o',str(Path(tmp)/'candidate.pact')] ]:
                result=subprocess.run([sys.executable,'-m','pact',*args],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(target.read_text().startswith('pact 0.3\n'))

    def test_inline_literals_exact_ir_revision_and_wasm_roundtrip(self):
        for name in ('hello', 'alien-harvest'):
            document = json.loads((ROOT / f'examples/{name}.pact.json').read_text())
            source = dumps(document, inline=True)
            self.assertTrue(source.startswith('pact 0.4\n'))
            restored = loads(source)
            self.assertEqual(restored, document)
            self.assertEqual(revision(restored), revision(document))
            compiler, validator = (compile_module, analyze_module) if name == 'alien-harvest' else (compile_plan, analyze)
            self.assertEqual(compiler(validator(restored)), compiler(validator(document)))
            self.assertEqual(dumps(document), (ROOT / f'examples/{name}.pact').read_text())
            if name == 'alien-harvest':
                self.assertEqual(source, (ROOT / 'examples/alien-harvest.inline.pact').read_text())
                self.assertEqual(dumps(document, compressed=True), (ROOT / 'examples/alien-harvest.data.pact').read_text())
                self.assertNotIn(' = i32.const ', source)
                self.assertLess(len(source.encode('utf-8')), len(dumps(document, compressed=True).encode('utf-8')))

    def test_shared_const_remains_standalone_while_suffix_const_inlines(self):
        document = game_document()
        fn = next(item for item in document['functions'] if item['id'] == 'math.abs')
        fn['nodes'] = [
            {'id': 'n0000', 'op': 'local.get', 'name': 'v'},
            {'id': 'n0001', 'op': 'i32.const', 'value': 0},
            {'id': 'n0002', 'op': 'i32.lt_s', 'args': ['n0000', 'n0001']},
            {'id': 'n0004', 'op': 'i32.sub_wrap', 'args': ['n0001', 'n0000']},
            {'id': 'n0005', 'op': 'flow.if', 'args': ['n0002', 'n0004', 'n0000']},
        ]
        source = dumps(document, inline=True)
        self.assertIn('n0001 = i32.const 0\n', source)
        self.assertEqual(loads(source), document)

    def test_inline_literals_reject_malformed_and_wrong_version(self):
        document = game_document()
        valid_04 = dumps(document, inline=True)
        for header in ('pact 0.2', 'pact 0.3'):
            with self.assertRaises(PactError):
                loads(valid_04.replace('pact 0.4', header, 1))
        bad_cases = [
            valid_04.replace('n0002 = i32.lt_s n0000 n0001=0', 'n0002 = i32.lt_s n0000 n0000=0', 1),
            valid_04.replace('n0002 = i32.lt_s n0000 n0001=0', 'n0002 = i32.lt_s n0000 n0002=0', 1),
            valid_04.replace('n0002 = set input.left n0000=0 n0001=0', 'n0002 = set input.left n0000=0 n0000=0', 1),
            valid_04.replace('n0002 = set input.left n0000=0 n0001=0', 'n0002 = set n0000=0 n0001=0', 1),
            valid_04.replace('n0001=0', 'n0001=00', 1),
            valid_04.replace('n0001=0', 'n0001=+1', 1),
            valid_04.replace('n0001=0', 'n0001=-0', 1),
            valid_04.replace('n0001=0', 'n0001=2147483648', 1),
            valid_04.replace('n0001=0', 'n0001=-2147483649', 1),
        ]
        for invalid in bad_cases:
            with self.subTest(invalid=invalid[:80]), self.assertRaises(PactError):
                loads(invalid)

    def test_cli_convert_and_patch_accept_compact_inline(self):
        with tempfile.TemporaryDirectory() as tmp:
            inline_path = Path(tmp) / 'game.inline.pact'
            patched_path = Path(tmp) / 'candidate.inline.pact'
            for args in [
                ['convert', 'examples/alien-harvest.pact', '--to', 'compact-inline', '-o', str(inline_path)],
                ['patch', str(inline_path), '--patch', 'examples/patches/jump.patch.json', '--dry-run'],
                ['patch', str(inline_path), '--patch', 'examples/patches/jump.patch.json', '--to', 'compact-inline', '-o', str(patched_path)],
            ]:
                result = subprocess.run([sys.executable, '-m', 'pact', *args], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(inline_path.read_text().startswith('pact 0.4\n'))
            self.assertTrue(patched_path.read_text().startswith('pact 0.4\n'))
