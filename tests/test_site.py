import subprocess
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


class SiteTests(unittest.TestCase):
    def test_site_greeting_includes_host_validation_manifest(self):
        build = subprocess.run([sys.executable, '-m', 'tools.build_site'], cwd=ROOT,
                               capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        result = subprocess.run(['node', 'host/run.mjs', 'site-output/hello.wasm', '--allow', 'stdout'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'hola mundo, from an alien language\n')
