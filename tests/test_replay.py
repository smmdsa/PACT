import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import hashlib
from unittest.mock import patch

from pact.diagnostics import PactError
from pact.compact import dumps
from pact.revision import revision
from tests.test_module import tiny
from tests.test_module_execution import execute
from tests.test_checked_assertions import checked, wasm_calls

ROOT=Path(__file__).resolve().parents[1]


class ReplayTests(unittest.TestCase):
    def test_shipped_recording_traps_after_first_success(self):
        module=importlib.import_module('pact.replay')
        report=module.replay_file(ROOT/'examples/counter.checked.pact',ROOT/'examples/counter.checked.replay.json')
        self.assertEqual(report['status'],'trapped')
        self.assertEqual(report['final_state'],{'counter':[10]})
        self.assertEqual(report['events'][0]['result'],None)
        self.assertEqual(report['events'][1]['diagnostic']['code'],'ASSERTION_FAILED')

    def replay(self, document, calls, **kwargs):
        try:
            module=importlib.import_module('pact.replay')
        except ImportError:
            self.fail('Reference replay is missing')
        record={'format':'pact.replay-input/0.1.0','expected_revision_sha256':revision(document),'calls':calls}
        return module.replay_document(document,record,**kwargs)

    def test_sequential_replay_is_deterministic_and_matches_wasm(self):
        document=tiny();calls=[{'function':'step','args':[]}]*2
        result=self.replay(document,calls)
        self.assertEqual(result,self.replay(document,calls))
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['final_state'],{'counter':[17]})
        self.assertNotEqual(result['events'][0]['state_sha256'],result['events'][1]['state_sha256'])
        output,_=execute(document,[{'fn':'step'}]*2)
        self.assertEqual(output.returncode,0,output.stderr)
        self.assertEqual(result['final_state'],json.loads(output.stdout)['state'])

    def test_guard_trap_stops_calls_and_matches_wasm_state(self):
        document=checked();calls=[{'function':'step','args':[1]},{'function':'step','args':[0]},
                                 {'function':'step','args':[1]}]
        result=self.replay(document,calls)
        self.assertEqual(result['status'],'trapped')
        self.assertEqual(len(result['events']),2)
        self.assertEqual(result['final_state'],{'counter':[10]})
        diagnostic=result['events'][-1]['diagnostic']
        self.assertEqual((diagnostic['code'],diagnostic['function'],diagnostic['node']),
                         ('ASSERTION_FAILED','step','check'))
        wasm=wasm_calls(document,[1,0])
        self.assertEqual(result['final_state'],wasm[-1]['state'])

    def test_bounds_trap_has_definition_identity(self):
        document=tiny();document['functions'][0]['nodes'][0]['value']=-1
        result=self.replay(document,[{'function':'step','args':[]}])
        diagnostic=result['events'][0]['diagnostic']
        self.assertEqual((diagnostic['code'],diagnostic['function'],diagnostic['node']),
                         ('STATE_BOUNDS','step','s'))
        self.assertEqual(result['final_state'],{'counter':[3]})

    def test_invalid_records_reject_before_execution(self):
        module=importlib.import_module('pact.replay');document=tiny()
        valid={'format':'pact.replay-input/0.1.0','expected_revision_sha256':revision(document),
               'calls':[{'function':'step','args':[]}]}
        for changes in ({'expected_revision_sha256':'0'*64},{'calls':[{'function':'missing','args':[]}]},
                        {'calls':[{'function':'step','args':[True]}]}, {'calls':valid['calls']*65}):
            with self.subTest(changes=changes),self.assertRaises(PactError):
                module.replay_document(document,dict(valid,**changes))

    def test_failed_postcondition_keeps_prior_writes_like_wasm(self):
        document=checked('flow.assert')
        document['functions'][0]['nodes'][-1]['args']=['s','check']
        result=self.replay(document,[{'function':'step','args':[0]}])
        self.assertEqual(result['status'],'trapped')
        self.assertEqual(result['final_state'],{'counter':[10]})
        self.assertEqual(result['final_state'],wasm_calls(document,[0])[0]['state'])

    def test_budget_is_shared_across_calls_and_retains_state(self):
        module=importlib.import_module('pact.replay')
        with patch.object(module,'MAX_EVALUATIONS',8):
            result=self.replay(tiny(),[{'function':'step','args':[]}]*3)
        self.assertEqual(result['status'],'limited')
        self.assertEqual(result['evaluations'],8)
        self.assertEqual(result['final_state'],{'counter':[10]})
        self.assertEqual(result['events'][-1]['diagnostic']['code'],'REPLAY_LIMIT')
        self.assertEqual(len(result['events']),2)

    def test_real_budget_limits_nested_repeats(self):
        document=tiny();fn=document['functions'][0];fn['locals']=['i','j']
        fn['nodes'] += [{'id':'inner','op':'flow.repeat','count':256,'counter':'j','args':['s']},
                        {'id':'outer','op':'flow.repeat','count':256,'counter':'i','args':['inner']}]
        fn['entry']='outer'
        result=self.replay(document,[{'function':'step','args':[]}])
        self.assertEqual(result['status'],'limited')
        self.assertEqual(result['evaluations'],100_000)
        self.assertGreater(result['final_state']['counter'][0],3)
        self.assertLess(result['final_state']['counter'][0],3+65536*7)

    def test_boolean_argument_rejects_even_with_matching_arity(self):
        with self.assertRaises(PactError) as raised:
            self.replay(checked(),[{'function':'step','args':[True]}])
        self.assertEqual(raised.exception.diagnostic['code'],'INTEGER_INVALID')

    def test_record_file_duplicate_keys_and_oversized_bytes_reject(self):
        module=importlib.import_module('pact.replay')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_text(json.dumps(tiny()))
            recording=Path(tmp)/'record.json'
            for source,code in [(b'{"calls":[],"\\u0063alls":[]}', 'JSON_DUPLICATE_KEY'),
                                (b' '*1_048_577,'SOURCE_LIMIT'),(b'{','SOURCE_INVALID')]:
                with self.subTest(code=code):
                    recording.write_bytes(source)
                    with self.assertRaises(PactError) as raised:module.replay_file(path,recording)
                    self.assertEqual(raised.exception.diagnostic['code'],code)

    def test_arithmetic_trap_identifies_node(self):
        document=tiny();fn=document['functions'][0]
        fn['nodes'][0]['value']=0
        fn['nodes'][3].update(op='i32.div_s',args=['a','z'])
        fn['nodes']=[node for node in fn['nodes'] if node['id']!='v']
        result=self.replay(document,[{'function':'step','args':[]}])
        diagnostic=result['events'][0]['diagnostic']
        self.assertEqual((diagnostic['code'],diagnostic['function'],diagnostic['node']),
                         ('ARITHMETIC_TRAP','step','sum'))
        self.assertEqual(result['final_state'],{'counter':[3]})

    def test_store_checks_bounds_before_evaluating_trapping_value(self):
        document=tiny();fn=document['functions'][0]
        fn['nodes'][0]['value']=1
        fn['nodes'].append({'id':'zero','op':'i32.const','value':0})
        fn['nodes'][3].update(op='i32.div_s',args=['a','zero'])
        fn['nodes']=[node for node in fn['nodes'] if node['id']!='v']
        result=self.replay(document,[{'function':'step','args':[]}])
        diagnostic=result['events'][0]['diagnostic']
        self.assertEqual((diagnostic['code'],diagnostic['node']),('STATE_BOUNDS','s'))
        output,_=execute(document,[{'fn':'step'}])
        self.assertNotEqual(output.returncode,0)
        self.assertIn(b'unreachable',output.stderr)

    def test_file_replay_qualifies_helper_and_preserves_exact_crlf_hash(self):
        module=importlib.import_module('pact.replay');document=checked()
        helper=copy.deepcopy(document['functions'][0]);helper['id']='helper'
        fn=document['functions'][0]
        fn['nodes']=[{'id':'p','op':'local.get','name':'predicate'},
                     {'id':'check','op':'call','target':'helper','args':['p']}]
        document['functions'].append(helper)
        record={'format':'pact.replay-input/0.1.0','expected_revision_sha256':revision(document),
                'calls':[{'function':'step','args':[0]}]}
        with tempfile.TemporaryDirectory() as tmp:
            record_path=Path(tmp)/'record.json';record_path.write_text(json.dumps(record))
            for name,source in [('source.json',json.dumps(document,indent=2).replace('"id": "check"','"id": "\\u0063heck"')),
                                ('source.pact',dumps(document))]:
                with self.subTest(name=name):
                    data=source.replace('\n','\r\n').encode();path=Path(tmp)/name;path.write_bytes(data)
                    result=module.replay_file(path,record_path)
                    self.assertEqual(result['source_sha256'],hashlib.sha256(data).hexdigest())
                    diagnostic=result['events'][0]['diagnostic']
                    self.assertEqual(diagnostic['function'],'helper')
                    self.assertEqual(diagnostic['source_location']['function'],'helper')
                    p=diagnostic['source_location'];line=data.decode().split('\n')[p['line']-1]
                    token=line[p['column']-1:p['end_column']-1]
                    self.assertEqual(token,'"\\u0063heck"' if name.endswith('.json') else 'check')

    def test_cli_reports_completed_trapped_and_invalid_records(self):
        document=checked();record={'format':'pact.replay-input/0.1.0',
            'expected_revision_sha256':revision(document),'calls':[{'function':'step','args':[1]}]}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_text(json.dumps(document))
            recording=Path(tmp)/'record.json'
            for argument,code,status in [(1,0,'completed'),(0,2,'trapped')]:
                record['calls'][0]['args']=[argument];recording.write_text(json.dumps(record))
                result=subprocess.run([sys.executable,'-m','pact','replay',str(path),'--record',str(recording)],
                                      cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,code,result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'],status)
            record['expected_revision_sha256']='0'*64;recording.write_text(json.dumps(record))
            result=subprocess.run([sys.executable,'-m','pact','replay',str(path),'--record',str(recording)],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stderr)['code'],'REVISION_MISMATCH')


