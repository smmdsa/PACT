import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InspectionCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'pact', *args], cwd=ROOT,
                              capture_output=True, text=True)

    def test_symbols_lists_functions_in_compact_and_json_sources(self):
        for suffix in ('pact', 'pact.json'):
            result = self.run_cli('symbols', f'examples/alien-harvest.{suffix}')
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['format'], 'pact.symbols/0.1.0')
            self.assertEqual(len(data['functions']), 14)
            self.assertTrue(data['context_only'])

    def test_inspect_function_and_reject_missing_id(self):
        result = self.run_cli('inspect', 'examples/alien-harvest.pact', '--function', 'player.move')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['selected_function']['id'], 'player.move')
        self.assertFalse(data['buildable'])
        result = self.run_cli('inspect', 'examples/alien-harvest.pact', '--function', 'missing')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)['status'], 'rejected')
