import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def guarded_document():
    return {'format':'pact.module/0.4.0','constants':{},
        'cells':[{'id':'reserved','values':[0],'mutable':False}],
        'functions':[{'id':'bounded.identity','params':['value'],'locals':[],'result':'i32','writes':[],
            'entry':'result','nodes':[
                {'id':'value','op':'local.get','name':'value'},
                {'id':'zero','op':'i32.const','value':0},
                {'id':'nonnegative','op':'i32.ge_s','args':['value','zero']},
                {'id':'result','op':'flow.guard','args':['nonnegative','value']}]}],
        'exports':['bounded.identity'],'assets':{'palettes':[],'tiles':[]},'presentation':{},
        'tests':[{'id':'zero.allowed','function':'bounded.identity','args':[0],'set':{},'expect':{},'result':0}]}


class CheckedAssertionsCliTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-m','pact',*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    def test_guarded_numeric_export_builds_and_exposes_test_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.json';source.write_text(json.dumps(guarded_document()))
            target=root/'guard.wasm'
            result=self.run_cli('build',source,'-o',target)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['evidence'],[{'id':'zero.allowed','status':'tested'}])
            self.assertTrue(target.exists())

    def test_assertion_trap_prevents_publication_and_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);doc=guarded_document();doc['tests'][0].update(args=[-1],result=-1)
            source=root/'source.json';source.write_text(json.dumps(doc))
            result=self.run_cli('check',source)
            self.assertEqual(result.returncode,0,result.stderr)
            target=root/'guard.wasm';target.write_bytes(b'existing artifact')
            result=self.run_cli('build',source,'-o',target)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stderr)['code'],'TEST_FAILED')
            self.assertEqual(target.read_bytes(),b'existing artifact')
            self.assertFalse(target.with_suffix('.manifest.json').exists())

    def test_forward_migration_to_0_4_is_explicit_and_does_not_add_contracts(self):
        from tests.test_module import tiny
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);doc=tiny();doc['format']='pact.module/0.3.0'
            doc['tests']=[{'id':'step.test','function':'step','set':{},'expect':{'counter':[10]}}]
            source=root/'source.json';source.write_text(json.dumps(doc));target=root/'migrated.json'
            result=self.run_cli('migrate',source,'--to','pact.module/0.4.0','-o',target)
            self.assertEqual(result.returncode,0,result.stderr)
            migrated=json.loads(target.read_text())
            self.assertEqual(dict(migrated,format=doc['format']),doc)
            self.assertEqual(json.loads(result.stdout)['to'],'pact.module/0.4.0')
