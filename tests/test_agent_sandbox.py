import importlib
import unittest
from unittest.mock import patch
import json
from pathlib import Path
import tempfile


class AgentSandboxTests(unittest.TestCase):
    def test_c_runtime_metadata_is_required_and_bounded(self):
        observed={'execution_status':'completed','initial_counter':[1,2],'cases':[],'reset_case':None}
        runtime={'engine':'gcc','gcc':'12.2.0'}
        parsed,versions=self.module().parse_observations(json.dumps({**observed,'runtime':runtime}).encode(),'c')
        self.assertEqual(parsed,observed);self.assertEqual(versions,runtime)
        for value in (None,{},dict(runtime,gcc='x'*101),dict(runtime,engine='other')):
            with self.assertRaises(ValueError):
                self.module().parse_observations(json.dumps({**observed,'runtime':value}).encode(),'c')

    def test_c_backend_missing_never_compiles_or_executes_on_host(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.c';candidate.write_bytes(b'#error must not compile on host')
            with patch.object(module.sys,'platform','linux'),patch.object(module.subprocess,'run',side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError,'no local execution fallback'):
                    module.run_candidate(candidate,'sha256:'+'a'*64,language='c')

    def test_javascript_observations_require_bounded_runtime_metadata(self):
        observed={'execution_status':'completed','initial_counter':[1,2],'cases':[],'reset_case':None}
        runtime={'engine':'node','node':'v24.0.0','v8':'13.6.0'}
        parsed,versions=self.module().parse_observations(json.dumps({**observed,'runtime':runtime}).encode(),'javascript')
        self.assertEqual(parsed,observed);self.assertEqual(versions,runtime)
        for value in (None,{},dict(runtime,node='x'*101),dict(runtime,engine='other')):
            with self.assertRaises(ValueError):
                self.module().parse_observations(json.dumps({**observed,'runtime':value}).encode(),'javascript')
        with self.assertRaises(ValueError):
            self.module().parse_observations(json.dumps(observed).encode(),'javascript')

    def module(self):
        try:return importlib.import_module('benchmarks.agent_sandbox')
        except ImportError:self.fail('Isolated PACT adapter is missing')

    def test_create_requires_explicit_resource_and_isolation_flags(self):
        command=self.module().create_command('pact-test','sha256:'+'a'*64)
        for flag,value in [('--network','none'),('--read-only',None),('--cap-drop','ALL'),
                           ('--user','65534:65534'),('--pids-limit','32'),('--memory','128m'),
                           ('--security-opt','no-new-privileges'),('--pull','never')]:
            self.assertIn(flag,command)
            if value:self.assertEqual(command[command.index(flag)+1],value)
        self.assertNotIn('--mount',command);self.assertNotIn('-v',command)

    def test_mutable_image_names_reject(self):
        for image in ('python:latest','sha256:'+'a'*64+'\n','--privileged'):
            with self.assertRaises(ValueError):self.module().create_command('pact-test',image)

    def configuration(self):
        return {'Image':'sha256:'+'a'*64,'Config':{'User':'65534:65534'},'Mounts':[],
                'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,
                    'Memory':134217728,'MemorySwap':134217728,'NanoCpus':1000000000,'PidsLimit':32,
                    'Binds':None,'VolumesFrom':None,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges']}}

    def test_configuration_verification_rejects_weakened_isolation(self):
        module=self.module();image='sha256:'+'a'*64
        module.verify_configuration(self.configuration(),image)
        for key,value in [('NetworkMode','host'),('ReadonlyRootfs',False),('Privileged',True),
                          ('Memory',0),('PidsLimit',0),('Binds',['/:/host'])]:
            info=self.configuration();info['HostConfig'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):module.verify_configuration(info,image)

    def test_missing_backend_never_falls_back_to_host_execution(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate';candidate.write_bytes(b'not host source')
            with patch.object(module.sys,'platform','linux'),patch.object(module.subprocess,'run',side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError,'no local execution fallback'):
                    module.run_candidate(candidate,'sha256:'+'a'*64)

    def test_python_backend_missing_also_rejects_without_host_execution(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate';candidate.write_bytes(b'raise RuntimeError("must not run on host")')
            with patch.object(module.sys,'platform','linux'),patch.object(module.subprocess,'run',side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError,'no local execution fallback'):
                    module.run_candidate(candidate,'sha256:'+'a'*64,language='python')

    def test_javascript_backend_missing_never_runs_candidate_on_host(self):
        module=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.mjs';candidate.write_bytes(b'throw new Error("must not run on host")')
            with patch.object(module.sys,'platform','linux'),patch.object(module.subprocess,'run',side_effect=FileNotFoundError):
                with self.assertRaisesRegex(ValueError,'no local execution fallback'):
                    module.run_candidate(candidate,'sha256:'+'a'*64,language='javascript')
