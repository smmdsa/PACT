import importlib
import json
from pathlib import Path
import unittest

from pact.compact import loads, dumps

ROOT=Path(__file__).resolve().parents[1]


class AgentCandidatePolicyTests(unittest.TestCase):
    def test_python_policy_accepts_only_canonical_ast_edit(self):
        source=(ROOT/'benchmarks/agent_trials/counter.py').read_bytes()
        correct=source.replace(b'range(3)',b'range(4)')
        self.assertTrue(self.module().audit_candidate(correct,language='python')['policy_pass'])
        self.assertTrue(self.module().audit_candidate(b'# comment\n'+correct,language='python')['policy_pass'])
        for candidate in (source,correct+b'\nimport os\n',b'not valid python!',correct.replace(b'amount)',b'index)')):
            self.assertFalse(self.module().audit_candidate(candidate,language='python')['policy_pass'])
    def module(self):
        try:return importlib.import_module('benchmarks.agent_candidate_policy')
        except ImportError:self.fail('Candidate source policy is missing')

    def candidate(self):
        source=(ROOT/'benchmarks/agent_trials/counter.pact').read_text()
        return source.replace('repeat 3 iteration','repeat 4 iteration').replace(
            '[-2147483647,-2147483647]','[-2147483646,-2147483647]').encode()

    def test_required_edit_passes_in_compact_and_json(self):
        source=self.candidate();document=loads(source.decode())
        for candidate in (source,json.dumps(document).encode(),source.replace(b'\n',b'\r\n')):
            report=self.module().audit_candidate(candidate)
            self.assertTrue(report['policy_pass'])
            self.assertIsNone(report['candidate_pass'])
            self.assertEqual(report['scope'],'counter-four canonical IR edit/0.1')

    def test_baseline_and_stale_embedded_test_reject(self):
        source=(ROOT/'benchmarks/agent_trials/counter.pact').read_bytes()
        for candidate in (source,source.replace(b'repeat 3 iteration',b'repeat 4 iteration')):
            self.assertFalse(self.module().audit_candidate(candidate)['policy_pass'])

    def test_unrelated_semantic_changes_reject(self):
        original=loads(self.candidate().decode())
        for change in ('initial','interface','effects','identity','version','tests'):
            document=json.loads(json.dumps(original))
            if change=='initial':document['cells'][0]['values'][0]=0
            if change=='interface':document['exports']=[]
            if change=='effects':document['functions'][0]['writes']=[]
            if change=='identity':document['tests'][0]['id']='renamed'
            if change=='version':document['format']='pact.module/0.2.0'
            if change=='tests':document['tests']=[]
            with self.subTest(change=change):
                self.assertFalse(self.module().audit_candidate(json.dumps(document).encode())['policy_pass'])

    def test_invalid_oversized_duplicate_and_non_utf8_reject(self):
        for source in (b'broken',b' '*1_048_577,b'\xff',b'{"format":1,"format":2}'):
            with self.subTest(source=source[:20]):
                self.assertFalse(self.module().audit_candidate(source)['policy_pass'])
