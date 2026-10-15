"""Host-side grading tests use synthetic records; never run resource attacks here."""
import copy
import unittest
from tools.check_agent_isolation import probe_passed


class ProbeResultTests(unittest.TestCase):
    def fixture(self,name):
        return {'started':True,'cleanup_verified':True,'state':{'OOMKilled':False,'Running':False},
                'timed_out':False,'output_limited':False,'captured_bytes':100,'returncode':0,
                'observation':{'probe':name,'stage':'finished','denied':True,
                               'interpreted_control':True,'loopback_control':True,'interfaces':['lo']}}

    def test_positive_controls_and_cleanup_are_required(self):
        for name in ('filesystem','network','file_size','temporary_space','processes','cpu'):
            original=self.fixture(name)
            self.assertTrue(probe_passed(name,original))
            for key in ('started','cleanup_verified'):
                record=copy.deepcopy(original);record[key]=False
                self.assertFalse(probe_passed(name,record))
            record=copy.deepcopy(original);record['observation']['denied']=False
            self.assertFalse(probe_passed(name,record))
        record=self.fixture('network');record['observation']['loopback_control']=False
        self.assertFalse(probe_passed('network',record))
        record=self.fixture('filesystem');record['observation']['interpreted_control']=False
        self.assertFalse(probe_passed('filesystem',record))

    def test_memory_kill_is_not_inferred_from_a_generic_crash(self):
        record=self.fixture('memory');record['returncode']=137
        self.assertFalse(probe_passed('memory',record))
        record['state']['OOMKilled']=True
        self.assertTrue(probe_passed('memory',record))
        record['timed_out']=True
        self.assertFalse(probe_passed('memory',record))

    def test_output_capture_limit_and_wall_timeout_are_distinct(self):
        record=self.fixture('output');record['output_limited']=True
        self.assertTrue(probe_passed('output',record))
        record['captured_bytes']=1048577
        self.assertFalse(probe_passed('output',record))
        record=self.fixture('wall_time')
        self.assertFalse(probe_passed('wall_time',record))
        record['timed_out']=True
        self.assertTrue(probe_passed('wall_time',record))

    def test_cleanup_failure_retains_completed_observations_and_logs(self):
        import base64
        import json
        from pathlib import Path
        from unittest.mock import patch
        import tools.check_agent_isolation as probe
        from tests.test_agent_sandbox import AgentSandboxTests
        config=AgentSandboxTests().configuration()
        stdout=b'{"probe":"file_size","stage":"started"}\n{"probe":"file_size","stage":"finished","denied":true}\n'
        raw={'stdout':stdout,'stderr':b'diagnostic','returncode':0,'timed_out':False,'output_limited':False}
        with patch.object(probe,'control',side_effect=[b'created',json.dumps([config]).encode(),json.dumps([{'State':{'Running':False}}]).encode()]),patch.object(probe,'run_bounded',return_value=raw),patch.object(probe,'cleanup_container',side_effect=ValueError('removal denied')):
            result=probe.run_probe('file_size','sha256:'+'a'*64,Path('/host/sentinel'))
        self.assertFalse(result['pass']);self.assertFalse(result['cleanup_verified'])
        self.assertEqual(result['cleanup_error'],'removal denied')
        self.assertEqual(base64.b64decode(result['log']['stdout_base64']),stdout)
        self.assertEqual(result['state'],{'Running':False})
        self.assertTrue(result['observation']['denied'])

    def test_cleanup_failure_probe_restores_the_real_backend_and_removes_container(self):
        import json
        import os
        from unittest.mock import patch
        import tools.check_agent_isolation as probe
        from tests.test_agent_sandbox import AgentSandboxTests
        config=AgentSandboxTests().configuration();state=[{'State':{'Running':True}}]
        responses=[b'created',json.dumps([config]).encode(),b'started',json.dumps(state).encode(),json.dumps(state).encode()]
        with patch.dict(os.environ,{'DOCKER_HOST':'original-test-endpoint'}):
            with patch.object(probe,'control',side_effect=responses),patch.object(probe,'cleanup_container',side_effect=[ValueError('Cannot connect'),None]):
                result=probe.cleanup_failure_probe('sha256:'+'a'*64)
            self.assertEqual(os.environ['DOCKER_HOST'],'original-test-endpoint')
        self.assertTrue(result['pass']);self.assertTrue(result['cleanup_verified'])
        self.assertEqual(result['failed_removal_error'],'Cannot connect')
