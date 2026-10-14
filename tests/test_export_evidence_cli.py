import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_module import tiny

ROOT=Path(__file__).resolve().parents[1]


class ExportEvidenceCliTests(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'-m','pact',*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    def document(self):
        document=tiny()
        document['tests']=[{'id':'step.baseline','function':'step','set':{},'expect':{'counter':[10]}}]
        return document

    def test_explicit_target_and_legacy_default_preserve_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.json';source.write_text(json.dumps(self.document()))
            target=root/'tested.json'
            result=self.run_cli('migrate',source,'--to','pact.module/0.3.0','-o',target)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['to'],'pact.module/0.3.0')
            migrated=json.loads(target.read_text())
            original=self.document()
            self.assertEqual(dict(migrated,format=original['format']),original)
            legacy=root/'legacy.json'
            result=self.run_cli('migrate',source,'-o',legacy)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(legacy.read_text())['format'],'pact.module/0.2.0')
            result=self.run_cli('migrate',legacy,'--to','pact.module/0.3.0','-o',root/'from-2.pact')
            self.assertEqual(result.returncode,0,result.stderr)

    def test_missing_cases_reject_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.json';source.write_text(json.dumps(tiny()))
            target=root/'candidate.pact'
            result=self.run_cli('migrate',source,'--to','pact.module/0.3.0','-o',target)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stderr)['code'],'EXPORT_EVIDENCE_MISSING')
            self.assertFalse(target.exists())

    def test_present_but_wrong_case_fails_actual_wasm_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);document=self.document();document['format']='pact.module/0.3.0'
            document['tests'][0]['expect']['counter']=[999]
            source=root/'wrong.json';source.write_text(json.dumps(document))
            checked=self.run_cli('check',source)
            self.assertEqual(checked.returncode,0,checked.stderr)
            self.assertEqual(json.loads(checked.stdout)['declared_export_tests'],{'step':['step.baseline']})
            target=root/'wrong.wasm';built=self.run_cli('build',source,'-o',target)
            self.assertEqual(built.returncode,1)
            self.assertEqual(json.loads(built.stderr)['code'],'TEST_FAILED')
            self.assertFalse(target.exists());self.assertFalse(target.with_suffix('.manifest.json').exists())
