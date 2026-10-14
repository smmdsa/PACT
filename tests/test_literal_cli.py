import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class LiteralCliTests(unittest.TestCase):
    def test_literal_conversion_and_patch_preserve_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'game.agent.pact'
            for args in [ ['convert','examples/alien-harvest.pact','--to','compact-agent','-o',str(source)],
                          ['patch',str(source),'--patch','examples/patches/jump.patch.json','--dry-run'] ]:
                result=subprocess.run([sys.executable,'-m','pact',*args],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(source.read_text().startswith('pact 0.4\n'))
            from pact.graph import load_document
            self.assertEqual(load_document(source),load_document(ROOT/'examples/alien-harvest.pact'))
