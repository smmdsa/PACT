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
