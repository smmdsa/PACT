import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_module import tiny

ROOT = Path(__file__).resolve().parents[1]


class PatchCliTests(unittest.TestCase):
    def setup_files(self, directory):
        root = Path(directory)
        doc = tiny()
        doc['tests'] = [{'id': 'step.test', 'function': 'step', 'set': {}, 'expect': {'counter': [10]}}]
        source = root/'source.json'
        source.write_text(json.dumps(doc), encoding='utf-8')
        from pact.module import migrate_module
        from pact.revision import revision
        expected = revision(migrate_module(doc))
        patch = {'format':'pact.patch/0.1.0','expected_revision_sha256':expected,'operations':[
            {'op':'set_constant','name':'amount','value':8},
            {'op':'replace_test','id':'step.test','test':{
                'id':'step.test','function':'step','set':{},'expect':{'counter':[11]}}}]}
        patch_path = root/'patch.json'
        patch_path.write_text(json.dumps(patch),encoding='utf-8')
        return source, patch_path, root/'candidate.pact', doc, patch

    def run_cli(self, *args):
        return subprocess.run([sys.executable,'-m','pact',*map(str,args)],cwd=ROOT,capture_output=True,text=True)

    def test_dry_run_runs_declared_tests_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, patch, output, _, _ = self.setup_files(tmp)
            before = source.read_bytes()
            result = self.run_cli('patch',source,'--patch',patch,'--dry-run','-o',output)
            self.assertEqual(result.returncode,0,result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt['status'],'validated')
            self.assertEqual(receipt['evidence'],[{'id':'step.test','status':'tested'}])
            self.assertEqual(receipt['changes'][0]['value'],8)
            self.assertNotEqual(receipt['expected_revision_sha256'],receipt['result_revision_sha256'])
            self.assertEqual(source.read_bytes(),before)
            self.assertFalse(output.exists())

    def test_valid_candidate_is_new_source_and_cannot_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, patch, output, _, _ = self.setup_files(tmp)
            before = source.read_bytes()
            result = self.run_cli('patch',source,'--patch',patch,'-o',output)
            self.assertEqual(result.returncode,0,result.stderr)
            from pact.graph import load_document
            candidate = load_document(output)
            self.assertEqual(candidate['constants']['amount'],8)
            candidate_bytes = output.read_bytes()
            result = self.run_cli('patch',source,'--patch',patch,'-o',output)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stderr)['code'],'OUTPUT_EXISTS')
            self.assertEqual(output.read_bytes(),candidate_bytes)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(list(Path(tmp).glob('.pact-*')),[])

    def test_bad_evidence_stale_revision_and_inplace_preserve_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, patch_path, output, _, patch = self.setup_files(tmp)
            before = source.read_bytes()
            variants = [dict(patch,operations=patch['operations'][:1]),
                        dict(patch,expected_revision_sha256='0'*64)]
            for bad, code in zip(variants, ['TEST_FAILED', 'PATCH_STALE']):
                patch_path.write_text(json.dumps(bad),encoding='utf-8')
                result = self.run_cli('patch',source,'--patch',patch_path,'-o',output)
                self.assertEqual(result.returncode,1,result.stdout)
                self.assertEqual(json.loads(result.stderr)['status'],'rejected')
                self.assertEqual(json.loads(result.stderr)['code'],code)
                self.assertFalse(output.exists())
                self.assertEqual(source.read_bytes(),before)
            patch_path.write_text(json.dumps(patch),encoding='utf-8')
            result = self.run_cli('patch',source,'--patch',patch_path,'-o',source)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stderr)['code'],'PATCH_IN_PLACE')
            self.assertEqual(source.read_bytes(),before)

    def test_duplicate_patch_keys_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, patch, output, _, _ = self.setup_files(tmp)
            patch.write_text('{"format":"pact.patch/0.1.0","format":"other"}',encoding='utf-8')
            result = self.run_cli('patch',source,'--patch',patch,'-o',output)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stderr)['code'],'JSON_DUPLICATE_KEY')
            self.assertFalse(output.exists())

    def test_json_candidate_roundtrip_and_incompatible_suffix_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, patch, output, _, _ = self.setup_files(tmp)
            result = self.run_cli('patch',source,'--patch',patch,'--to','json','-o',output)
            self.assertEqual(result.returncode,1,result.stdout)
            self.assertEqual(json.loads(result.stderr)['code'],'PATCH_OUTPUT_FORMAT')
            self.assertFalse(output.exists())
            output = Path(tmp)/'candidate.json'
            result = self.run_cli('patch',source,'--patch',patch,'--to','json','-o',output)
            self.assertEqual(result.returncode,0,result.stderr)
            result = self.run_cli('symbols',output)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['format'],'pact.symbols/0.1.0')

    def test_dry_run_checks_serialized_output_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, patch_path, output, doc, patch = self.setup_files(tmp)
            for index in range(5):
                nodes = [{'id':'n'+'x'*58+str(n),'op':'i32.const','value':0} for n in range(500)]
                level = [node['id'] for node in nodes]
                while len(level) > 1:
                    next_level = []
                    for start in range(0,len(level),2):
                        if start+1 == len(level):
                            next_level.append(level[start])
                        else:
                            name = 'n'+'x'*58+str(len(nodes))
                            nodes.append({'id':name,'op':'i32.add_wrap','args':level[start:start+2]})
                            next_level.append(name)
                    level = next_level
                doc['functions'].append({'id':f'extra{index}','params':[],'locals':[],
                    'result':'i32','writes':[],'entry':level[0],'nodes':nodes})
            source.write_text(json.dumps(doc,separators=(',',':')),encoding='utf-8')
            from pact.revision import revision
            from pact.module import migrate_module
            patch['expected_revision_sha256'] = revision(migrate_module(doc))
            patch_path.write_text(json.dumps(patch),encoding='utf-8')
            before = source.read_bytes()
            self.assertLess(len(before),1024*1024)
            self.assertGreater(len(json.dumps(doc,indent=2).encode()),1024*1024)
            result = self.run_cli('patch',source,'--patch',patch_path,'--to','json','--dry-run')
            self.assertEqual(result.returncode,1,result.stdout)
            self.assertEqual(json.loads(result.stderr)['code'],'SOURCE_LIMIT')
            self.assertEqual(source.read_bytes(),before)
            self.assertFalse(output.exists())
