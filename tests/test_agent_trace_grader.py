import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class AgentTraceGraderTests(unittest.TestCase):
    def module(self):
        try:return importlib.import_module('benchmarks.agent_trace_grader')
        except ImportError:self.fail('Independent external trace grading is missing')

    def trace(self, language='pact'):
        oracle=json.loads((ROOT/'benchmarks/agent_trials/cases.json').read_text())
        return {'format':'pact.agent-execution-trace/0.1','task':'counter-four','language':language,
                'candidate_sha256':hashlib.sha256(b'untrusted candidate').hexdigest(),
                'oracle_sha256':hashlib.sha256((ROOT/'benchmarks/agent_trials/cases.json').read_bytes()).hexdigest(),
                'executor':{'command':'external verifier candidate','revision':'pinned-v1','log_sha256':'a'*64},
                'execution_status':'completed','initial_counter':oracle['initial_counter'],
                'cases':oracle['cases'],
                'reset_case':{'args':oracle['embedded_test_after_edit']['args'],'status':'ok',
                              'counter':oracle['embedded_test_after_edit']['counter']}}

    def test_matching_traces_grade_behavior_only_for_all_languages(self):
        m=self.module()
        for language in ('pact','python','javascript','c'):
            with self.subTest(language=language):
                result=m.grade_trace(self.trace(language),b'untrusted candidate')
                self.assertTrue(result['behavior_pass'])
                self.assertIsNone(result['candidate_pass'])
                self.assertFalse(result['execution_authenticated'])
                self.assertEqual(result['case_results'],[True]*10)

    def test_changed_bounds_state_and_missing_cases_fail(self):
        m=self.module();trace=self.trace();trace['cases'][4]['counter'][0]+=1
        result=m.grade_trace(trace,b'untrusted candidate')
        self.assertFalse(result['behavior_pass']);self.assertFalse(result['case_results'][4])
        trace=self.trace();trace['cases']=trace['cases'][:2]
        result=m.grade_trace(trace,b'untrusted candidate')
        self.assertFalse(result['behavior_pass']);self.assertEqual(result['missing_cases'],8)

    def test_timeout_without_trace_remains_a_failed_observation(self):
        trace=self.trace();trace.update(execution_status='timeout',initial_counter=None,cases=[],reset_case=None)
        result=self.module().grade_trace(trace,b'untrusted candidate')
        self.assertFalse(result['behavior_pass']);self.assertEqual(result['execution_status'],'timeout')
        self.assertEqual(result['missing_cases'],10)

    def test_identity_mismatch_and_boolean_values_reject(self):
        m=self.module()
        for mutate in (lambda t:t.update(candidate_sha256='0'*64),
                       lambda t:t.update(oracle_sha256='0'*64),
                       lambda t:t['cases'][0]['args'].__setitem__(0,True)):
            trace=self.trace();mutate(trace)
            with self.assertRaises(ValueError):m.grade_trace(trace,b'untrusted candidate')

    def test_changed_reset_initial_or_case_order_fail(self):
        m=self.module()
        for mutate in (lambda t:t['initial_counter'].__setitem__(0,0),
                       lambda t:t['reset_case']['counter'].__setitem__(0,0),
                       lambda t:t['cases'].reverse()):
            trace=self.trace();mutate(trace)
            self.assertFalse(m.grade_trace(trace,b'untrusted candidate')['behavior_pass'])

    def test_cli_grades_bytes_without_executing_candidate(self):
        trace=self.trace()
        # This is deliberately invalid source; a trace match cannot approve it.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);candidate=root/'candidate.pact';candidate.write_bytes(b'untrusted candidate')
            path=root/'trace.json';path.write_bytes(json.dumps(trace).replace('\n','\r\n').encode())
            output=subprocess.run([sys.executable,'-m','benchmarks.agent_trace_grader',str(path),
                                   '--candidate',str(candidate)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(output.returncode,0,output.stderr)
            report=json.loads(output.stdout)
            self.assertIsNone(report['candidate_pass'])
            self.assertEqual(report['trace_bytes_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            trace['cases']=[];path.write_text(json.dumps(trace))
            output=subprocess.run([sys.executable,'-m','benchmarks.agent_trace_grader',str(path),
                                   '--candidate',str(candidate)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(output.returncode,2)

    def test_duplicate_keys_oversized_files_and_unknown_fields_reject(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);candidate=root/'candidate';candidate.write_bytes(b'untrusted candidate');path=root/'trace'
            for data in (b'{"task":1,"\\u0074ask":2}',b' '*1_048_577,b'{'):
                path.write_bytes(data)
                with self.assertRaises(ValueError):m.grade_files(path,candidate)
        trace=self.trace();trace['pass']=True
        with self.assertRaises(ValueError):m.grade_trace(trace,b'untrusted candidate')

    def test_all_execution_errors_remain_failed_even_with_matching_states(self):
        for status in ('compile_error','error','timeout'):
            trace=self.trace();trace['execution_status']=status
            self.assertFalse(self.module().grade_trace(trace,b'untrusted candidate')['behavior_pass'])

