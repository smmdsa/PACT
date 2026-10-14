import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from pact.browser import game_html
from tests.test_graph import ROOT
from tools.make_game import game_document


class BrowserPackageTests(unittest.TestCase):
    def test_embedded_javascript_parses(self):
        html=game_html(game_document(),b'wasm',{'format':'test','presentation':{}}).decode()
        scripts=re.findall(r'<script>(.*?)</script>',html,re.S)
        self.assertEqual(len(scripts),2)
        with tempfile.TemporaryDirectory() as tmp:
            for i,code in enumerate(scripts):
                file=Path(tmp)/f'part{i}.js';file.write_text(code)
                result=subprocess.run(['node','--check',str(file)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_delivery_has_no_external_script_or_image_dependencies(self):
        html=game_html(game_document(),b'wasm',{'format':'test'}).decode()
        self.assertNotRegex(html,r'<script[^>]+src=')
        self.assertNotRegex(html,r'<img[^>]+src=')
        self.assertIn('WebAssembly.instantiate',html)
        self.assertIn('pact-source',html)
