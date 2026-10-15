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
        parsed,versions,embedded=self.module().parse_observations(json.dumps({**observed,'runtime':runtime}).encode(),'c')
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
        parsed,versions,embedded=self.module().parse_observations(json.dumps({**observed,'runtime':runtime}).encode(),'javascript')
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

    def test_pact_observations_require_separate_embedded_test_evidence(self):
        observed={'execution_status':'completed','initial_counter':[1,2],'cases':[],'reset_case':None}
        evidence={'engine':'wasm','status':'passed','declared':1,'executed':1,'pass':True,'reason':None}
        parsed,runtime,tests=self.module().parse_observations(json.dumps({**observed,'embedded_tests':evidence}).encode(),'pact')
        self.assertEqual(parsed,observed);self.assertIsNone(runtime);self.assertEqual(tests,evidence)
        for bad in (None,{},dict(evidence,declared=0),dict(evidence,executed=0),dict(evidence,**{'pass':1}),dict(evidence,status='not_applicable')):
            with self.assertRaises(ValueError):
                self.module().parse_observations(json.dumps({**observed,'embedded_tests':bad}).encode(),'pact')

    def test_worker_evidence_cannot_be_attached_to_another_language(self):
        observed={'execution_status':'completed','initial_counter':[1,2],'cases':[],'reset_case':None,'embedded_tests':{}}
        with self.assertRaises(ValueError):self.module().parse_observations(json.dumps(observed).encode(),'python')

    def test_cli_success_requires_pact_test_execution(self):
        module=self.module()
        report={'grade':{'behavior_pass':True},'policy':{'policy_pass':True},'trace':{'language':'pact'},
                'embedded_tests':{'pass':None}}
        self.assertFalse(module.checks_passed(report))
        report['embedded_tests']['pass']=False;self.assertFalse(module.checks_passed(report))
        report['embedded_tests']['pass']=True;self.assertTrue(module.checks_passed(report))
        report['policy']['policy_pass']=False;self.assertFalse(module.checks_passed(report))
        report['policy']['policy_pass']=True;report['trace']['language']='python'
        report['embedded_tests']['pass']=None;self.assertTrue(module.checks_passed(report))

    def test_reference_checkpoint_survives_a_partial_final_report(self):
        observed={'execution_status':'completed','initial_counter':[1,2],'cases':[],'reset_case':None}
        checkpoint=json.dumps({'format':'pact.reference-checkpoint/0.1','observations':observed}).encode()+b'\n'
        self.assertEqual(self.module().parse_checkpoint(checkpoint+b'{"embedded'),observed)
        for data in (b'',checkpoint.rstrip(),b'noise\n'+checkpoint,checkpoint.replace(b'completed',b'error')):
            with self.assertRaises(ValueError):self.module().parse_checkpoint(data)

    def test_final_report_must_match_its_reference_checkpoint(self):
        observed={'execution_status':'completed','initial_counter':[1,2],'cases':[],'reset_case':None}
        checkpoint=json.dumps({'format':'pact.reference-checkpoint/0.1','observations':observed}).encode()+b'\n'
        evidence={'engine':'wasm','status':'passed','declared':1,'executed':1,'pass':True,'reason':None}
        final=json.dumps({**observed,'embedded_tests':evidence}).encode()
        parsed,_,_=self.module().parse_observations(checkpoint+final,'pact')
        self.assertEqual(parsed,observed)
        changed=json.dumps({**observed,'initial_counter':[9,9],'embedded_tests':evidence}).encode()
        with self.assertRaises(ValueError):self.module().parse_observations(checkpoint+changed,'pact')

    def test_unknown_policy_rejects_before_docker_or_source_access(self):
        module=self.module()
        with patch.object(module,'control') as control:
            with self.assertRaisesRegex(ValueError,'source-policy profile'):
                module.run_candidate('missing','sha256:'+'a'*64,policy_profile='unknown')
            control.assert_not_called()

    def test_cli_forwards_the_explicit_policy_profile(self):
        import contextlib
        import io
        module=self.module()
        report={'grade':{'behavior_pass':True},'policy':{'policy_pass':True},'trace':{'language':'python'},
                'embedded_tests':{'pass':None}}
        with patch.object(module,'run_candidate',return_value=report) as run,contextlib.redirect_stdout(io.StringIO()):
            result=module.main(['candidate.py','--image','sha256:'+'a'*64,'--language','python',
                                '--policy-profile','counter-four-forms/0.2'])
        self.assertEqual(result,0)
        self.assertEqual(run.call_args.kwargs['policy_profile'],'counter-four-forms/0.2')
