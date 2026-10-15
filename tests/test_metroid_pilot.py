import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class MetroidPilotTests(unittest.TestCase):
    def module(self):return importlib.import_module('tools.check_metroid_pilot')

    def test_image_and_isolation_flags_are_explicit(self):
        command=self.module().create_command('test','sha256:'+'a'*64)
        for flag,value in [('--memory','768m'),('--pids-limit','128'),('--network','none'),
                           ('--user','65534:65534'),('--entrypoint','node')]:
            self.assertEqual(command[command.index(flag)+1],value)
        self.assertIn('--read-only',command)
        self.assertIn('/tmp:size=64m,nosuid,nodev,noexec',command)
        self.assertNotIn('-v',command)
        with self.assertRaises(ValueError):self.module().create_command('test','image:latest')

    def test_unavailable_docker_never_executes_html_on_host(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as directory:
            candidate=Path(directory)/'candidate.html';candidate.write_bytes(b'<script>throw Error("must not run")</script>')
            with patch.object(module.sys,'platform','linux'),patch.object(module,'control',side_effect=ValueError('Docker missing')):
                with self.assertRaisesRegex(ValueError,'Docker missing'):
                    module.run_candidate(candidate,'sha256:'+'a'*64)

    def test_weakened_browser_resource_configuration_rejects(self):
        info={'Image':'sha256:'+'a'*64,'Config':{'User':'65534:65534'},'Mounts':[],
              'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'Memory':805306368,
                'MemorySwap':805306368,'NanoCpus':1000000000,'PidsLimit':128,'CapDrop':['ALL'],
                'SecurityOpt':['no-new-privileges'],'Binds':None,'VolumesFrom':None}}
        self.module().verify_configuration(info,info['Image'])
        info['HostConfig']['Memory']=0
        with self.assertRaises(ValueError):self.module().verify_configuration(info,info['Image'])

    def test_worker_json_requires_boolean_checks_and_bounded_payload(self):
        module=self.module()
        output={'format':'pact.metroid-browser-observations/0.1','checks':[{'id':'bootstrap','pass':False,'detail':'missing API'}],
                'runtime':{'chromium':'test','playwright':'test'},'screenshots':[],'page_errors':[]}
        self.assertFalse(module.parse_output(json.dumps(output).encode())['checks'][0]['pass'])
        output['checks'][0]['pass']='true'
        with self.assertRaises(ValueError):module.parse_output(json.dumps(output).encode())
        output['checks'][0]['pass']=True;output['page_errors']=['x'*513]
        with self.assertRaises(ValueError):module.parse_output(json.dumps(output).encode())

    def test_worker_cannot_choose_screenshot_paths(self):
        output={'format':'pact.metroid-browser-observations/0.1','checks':[{'id':'boot','pass':True,'detail':'ok'}],
                'runtime':{'chromium':'test','playwright':'test'},'screenshots':[{'id':'../escape','png_base64':'AA=='}],'page_errors':[]}
        with self.assertRaises(ValueError):self.module().parse_output(json.dumps(output).encode())
