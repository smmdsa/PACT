import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.revision import revision
from tests.test_module import tiny

ROOT = Path(__file__).resolve().parents[1]


class SourceLocationTests(unittest.TestCase):
    def test_json_migration_rejection_points_to_original_snapshot(self):
        document=tiny();document['functions'][0]['nodes'][1]['cell']='missing'
        source=json.dumps(document,indent=2).replace('"id": "v"','"id": "\\u0076"').replace('\n','\r\n')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_bytes(source.encode())
            target=Path(tmp)/'candidate.json';target.write_bytes(b'preserved')
            result=subprocess.run([sys.executable,'-m','pact','migrate',str(path),'-o',str(target)],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            diagnostic=json.loads(result.stderr)
            self.assertEqual(diagnostic['code'],'STATE_MISSING')
            position=diagnostic.get('source_location',{})
            self.assertEqual(position.get('function'),'step')
            line=source.split('\n')[position['line']-1]
            self.assertEqual(line[position['column']-1:position['end_column']-1],'"\\u0076"')
            self.assertEqual(target.read_bytes(),b'preserved')

    def test_migration_loader_reads_one_snapshot_for_semantic_rejections(self):
        from pact.graph import load_document
        document=tiny();document['functions'][0]['writes']=[]
        source=json.dumps(document,indent=2)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_text(source)
            opened=[];real_open=Path.open
            def track_open(path,*args,**kwargs):
                opened.append((path,args))
                return real_open(path,*args,**kwargs)
            with patch.object(Path,'open',track_open),self.assertRaises(PactError) as raised:
                load_document(path,migrate_to='pact.module/0.2.0')
            self.assertEqual(opened,[(path,('rb',))])
            diagnostic=raised.exception.diagnostic
            self.assertEqual(diagnostic['source_location']['kind'],'function')
            self.assertEqual(diagnostic['fix']['op'],'set_writes')

    def test_migration_loader_keeps_ambiguous_definitions_as_candidates(self):
        from pact.graph import load_document
        document=tiny();other=copy.deepcopy(document['functions'][0]);other['id']='other'
        document['functions'].append(other)
        document['functions'][0]['nodes'][1]['cell']='missing'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_text(json.dumps(document))
            with self.assertRaises(PactError) as raised:load_document(path,migrate_to='pact.module/0.2.0')
        diagnostic=raised.exception.diagnostic
        self.assertNotIn('source_location',diagnostic)
        self.assertEqual([p['function'] for p in diagnostic['source_candidates']],['step','other'])

    def test_target_migration_evidence_error_retains_fix_without_fabricating_span(self):
        from pact.graph import load_document
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_text(json.dumps(tiny()))
            with self.assertRaises(PactError) as raised:load_document(path,migrate_to='pact.module/0.3.0')
        diagnostic=raised.exception.diagnostic
        self.assertEqual(diagnostic['code'],'EXPORT_EVIDENCE_MISSING')
        self.assertEqual(diagnostic['fix'],{'op':'add_export_tests','functions':['step']})
        self.assertNotIn('source_location',diagnostic)
        self.assertNotIn('source_candidates',diagnostic)

    def test_explicit_migration_loader_preserves_bytes_and_source(self):
        from pact.graph import load_document
        from pact.module import migrate_module
        document=tiny();expected=migrate_module(document)
        with tempfile.TemporaryDirectory() as tmp:
            for name,source in [('source.json',json.dumps(document)),('source.pact',dumps(document))]:
                with self.subTest(name=name):
                    path=Path(tmp)/name;original=source.encode();path.write_bytes(original)
                    migrated=load_document(path,migrate_to='pact.module/0.2.0')
                    self.assertEqual(migrated,expected)
                    self.assertEqual(path.read_bytes(),original)
                    self.assertEqual(compile_module(analyze_module(migrated)),compile_module(analyze_module(document)))


    def test_json_cli_semantic_rejection_uses_original_escaped_crlf_span(self):
        source=json.dumps(tiny(),indent=2).replace('"cell": "counter"','"cell": "missing"')
        source=source.replace('"id": "v"','"id": "\\u0076"').replace('\n','\r\n')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json';path.write_bytes(source.encode())
            for command in ('check','symbols','convert'):
                args=[sys.executable,'-m','pact',command,str(path)]
                if command=='convert':args+=['--to','compact','-o',str(Path(tmp)/'out.pact')]
                output=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(output.returncode,1)
                diagnostic=json.loads(output.stderr)
                self.assertEqual(diagnostic['code'],'STATE_MISSING')
                position=diagnostic.get('source_location',{})
                self.assertEqual(position.get('function'),'step')
                line=source.split('\n')[position['line']-1]
                self.assertEqual(line[position['column']-1:position['end_column']-1],'"\\u0076"')

    def test_json_semantic_rejection_lists_ambiguous_candidates(self):
        document=tiny();other=copy.deepcopy(document['functions'][0]);other['id']='other'
        document['functions'].append(other)
        document['functions'][0]['nodes'][1]['cell']='missing'
        with self.assertRaises(PactError) as raised:self.locate(json.dumps(document))
        diagnostic=raised.exception.diagnostic
        self.assertNotIn('source_location',diagnostic)
        self.assertEqual([p['function'] for p in diagnostic.get('source_candidates',[])],['step','other'])

    def test_json_function_rejection_retains_structured_fix(self):
        document=tiny();document['functions'][0]['writes']=[]
        with self.assertRaises(PactError) as raised:self.locate(json.dumps(document))
        diagnostic=raised.exception.diagnostic
        self.assertEqual(diagnostic['source_location']['kind'],'function')
        self.assertEqual(diagnostic['source_location']['id'],'step')
        self.assertEqual(diagnostic['fix']['op'],'set_writes')

    def test_json_contract_collision_omits_definition_location(self):
        document=json.loads((ROOT/'examples/hello.pact.json').read_text())
        document['contracts'][0]['id']=document['nodes'][0]['id']
        document['contracts'][0]['value']='wrong output'
        with self.assertRaises(PactError) as raised:self.locate(json.dumps(document))
        diagnostic=raised.exception.diagnostic
        self.assertEqual(diagnostic['code'],'CONTRACT_FAILED')
        self.assertNotIn('source_location',diagnostic)
        self.assertNotIn('source_candidates',diagnostic)

    def test_json_malformed_definition_containers_preserve_rejections(self):
        from pact.graph import load_document
        for nodes in (None, {}, [None], [{'id':[]} ]):
            document=tiny();document['functions'][0]['nodes']=nodes
            with self.subTest(nodes=nodes),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'source.json';path.write_text(json.dumps(document))
                with self.assertRaises(PactError) as raised:load_document(path,validate_source=True)
                self.assertNotIn('source_location',raised.exception.diagnostic)


    def locate(self, source, **selection):
        try:
            module = importlib.import_module('pact.source_locations')
        except ImportError:
            self.fail('Source location queries are missing')
        return module.locate_source(source, **selection)

    def test_qualified_selection_preserves_semantics_and_uses_character_columns(self):
        document = tiny()
        second = copy.deepcopy(document['functions'][0]); second['id'] = 'other'
        document['functions'].append(second)
        source = '# 雪 comment\n' + dumps(document)
        source = source.replace('z = i32.const 0', '\t  z = i32.const 0')
        before = compile_module(analyze_module(document))
        result = self.locate(source, function_id='other', node_id='z')
        line = next(i for i, value in enumerate(source.split('\n'), 1) if value == 'fn other') + 5
        self.assertEqual(result['positions'], [{'kind':'node','function':'other','id':'z',
                                              'line':line,'column':4,'end_column':5}])
        self.assertEqual(result['source_sha256'], hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(result['semantic_revision_sha256'], revision(document))
        self.assertTrue(result['context_only']); self.assertFalse(result['buildable'])
        self.assertEqual(compile_module(analyze_module(loads(source))), before)

    def test_inline_constants_are_located_at_their_exact_tokens(self):
        document = tiny(); document['functions'][0]['nodes'][0]['value'] = -2147483648
        # A single-use constant immediately before its consumer.
        nodes = document['functions'][0]['nodes']; nodes[1]['args'] = ['q']
        nodes.insert(1, {'id':'q','op':'i32.const','value':0})
        source = dumps(document, inline=True)
        position = self.locate(source, function_id='step', node_id='q')['positions'][0]
        line = source.split('\n')[position['line']-1]
        self.assertEqual(line[position['column']-1:position['end_column']-1], 'q=0')
        self.assertEqual(position['kind'], 'inline_constant')

    def test_unique_semantic_errors_have_locations_and_ambiguous_ids_have_candidates(self):
        source = dumps(tiny()).replace('v = get counter z', 'v = get missing z')
        with self.assertRaises(PactError) as raised: loads(source)
        diagnostic = raised.exception.diagnostic
        self.assertEqual(diagnostic['code'], 'STATE_MISSING')
        self.assertEqual(diagnostic.get('source_location',{}).get('line'), 11)
        document = tiny(); other=copy.deepcopy(document['functions'][0]);other['id']='other'
        document['functions'].append(other)
        source=dumps(document).replace('v = get counter z', 'v = get missing z',1)
        with self.assertRaises(PactError) as raised: loads(source)
        diagnostic=raised.exception.diagnostic
        self.assertNotIn('source_location',diagnostic)
        self.assertEqual([p['function'] for p in diagnostic.get('source_candidates',[])], ['step','other'])

    def test_syntax_rejection_has_physical_line_and_no_fabricated_semantic_location(self):
        source='# lead\npact 0.4\nformat "pact.module/0.1.0"\nbroken = unknown\n'
        with self.assertRaises(PactError) as raised: loads(source)
        self.assertEqual(raised.exception.diagnostic.get('source_location'), {'line':4,'column':1})
        source=dumps(tiny()).replace('writes ["counter"]','writes []')
        with self.assertRaises(PactError) as raised: loads(source)
        self.assertEqual(raised.exception.diagnostic['source_location']['kind'],'function')
        self.assertEqual(raised.exception.diagnostic['fix']['op'],'set_writes')

    def test_graph_string_lookalikes_are_not_inline_nodes_and_missing_selection_rejects(self):
        document=json.loads((ROOT/'examples/hello.pact.json').read_text())
        document['nodes'][0]['value']='fake=8 # 雪\u2028still one line'
        document['contracts'][0]['value']=document['nodes'][0]['value']+document['nodes'][1]['value']
        source=dumps(document,literals=True)
        result=self.locate(source)
        self.assertEqual(len([p for p in result['positions'] if p['kind']=='node']),len(document['nodes']))
        self.assertFalse(any(p['kind']=='inline_constant' for p in result['positions']))
        for selection in ({'function_id':'missing'}, {'node_id':'missing'}, {'function_id':'step','node_id':'missing'}):
            with self.subTest(selection=selection), self.assertRaises(PactError):
                self.locate(dumps(tiny()),**selection)

    def test_contract_namespace_collisions_never_point_to_a_node(self):
        document=json.loads((ROOT/'examples/hello.pact.json').read_text())
        document['contracts'][0]['id']=document['nodes'][0]['id']
        document['contracts'][0]['value']='wrong output'
        valid=dumps(json.loads((ROOT/'examples/hello.pact.json').read_text()))
        source='\n'.join('contracts '+json.dumps(document['contracts']) if line.startswith('contracts ') else line for line in valid.split('\n'))
        with self.assertRaises(PactError) as raised: loads(source)
        self.assertEqual(raised.exception.diagnostic['code'],'CONTRACT_FAILED')
        self.assertNotIn('source_location',raised.exception.diagnostic)
        self.assertNotIn('source_candidates',raised.exception.diagnostic)

    def test_migration_rejection_and_bad_header_use_actual_locations(self):
        source=dumps(tiny()).replace('v = get counter z','v = get missing z')
        with self.assertRaises(PactError) as raised: loads(source,migrate_legacy=True)
        self.assertEqual(raised.exception.diagnostic['source_location']['line'],11)
        with self.assertRaises(PactError) as raised: loads('# lead\n\n# more\npact 9.9\n')
        self.assertEqual(raised.exception.diagnostic['source_location']['line'],4)

    def test_cli_path_and_snapshot_hash_are_bound_to_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.pact'; data=dumps(tiny()).replace('\n','\r\n').encode();path.write_bytes(data)
            output=subprocess.run([sys.executable,'-m','pact','locate',str(path),'--function','step','--node','v'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(output.returncode,0,output.stderr)
            result=json.loads(output.stdout)
            self.assertEqual(result['source_sha256'],hashlib.sha256(data).hexdigest())
            self.assertEqual(result['source_path'],str(path))
            path.write_text(json.dumps(tiny()))
            output=subprocess.run([sys.executable,'-m','pact','locate',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(output.returncode,0,output.stderr)
            self.assertEqual(len(json.loads(output.stdout)['positions']),6)

    def test_json_qualified_ids_use_exact_escaped_tokens_and_character_columns(self):
        document=tiny(); other=copy.deepcopy(document['functions'][0]);other['id']='other'
        document['functions'].append(other)
        source=json.dumps(document,ensure_ascii=False,indent=2)
        source=source.replace('"id": "z"','"\\u0069d": "\\u007a"')
        result=self.locate(source,function_id='other',node_id='z')
        position=result['positions'][0]
        line=source.split('\n')[position['line']-1]
        self.assertEqual(line[position['column']-1:position['end_column']-1],'"\\u007a"')
        self.assertEqual(position['function'],'other')
        self.assertEqual(result['source_sha256'],hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(result['semantic_revision_sha256'],revision(json.loads(source)))
        self.assertEqual(compile_module(analyze_module(json.loads(source))),compile_module(analyze_module(document)))

    def test_minified_json_indexes_definitions_only_in_physical_order(self):
        document=tiny(); other=copy.deepcopy(document['functions'][0]);other['id']='other'
        document['functions'].append(other)
        # Function ID follows nodes; unrelated metadata must not create definitions.
        fn=document['functions'][0];fn['id']=fn.pop('id')
        document['tests']=[{'id':'z','function':'step','set':{},'expect':{'counter':[10]}}]
        source=json.dumps(document,ensure_ascii=False,separators=(',',':'))
        result=self.locate(source,node_id='z')
        self.assertTrue(result['selection_ambiguous'])
        self.assertEqual([p['function'] for p in result['positions']],['step','other'])
        for position in result['positions']:
            self.assertEqual(position['line'],1)
            self.assertEqual(source[position['column']-1:position['end_column']-1],'"z"')
        positions=self.locate(source)['positions']
        self.assertEqual(len(positions),12)
        self.assertEqual(positions,sorted(positions,key=lambda p:(p['line'],p['column'])))

    def test_json_graph_excludes_contract_and_reference_ids(self):
        document=json.loads((ROOT/'examples/hello.pact.json').read_text())
        document['contracts'][0]['id']=document['nodes'][0]['id']
        document['nodes'][0]['value']='雪\u2028"id": "v0"'
        document['contracts'][0]['value']=document['nodes'][0]['value']+document['nodes'][1]['value']
        source=json.dumps(document,ensure_ascii=False,separators=(',',':'))
        result=self.locate(source,node_id=document['nodes'][0]['id'])
        self.assertEqual(len(result['positions']),1)
        self.assertIsNone(result['positions'][0]['function'])
        self.assertFalse(result['selection_ambiguous'])
        position=self.locate(source,node_id='v1')['positions'][0]
        self.assertEqual(position['line'],1)
        self.assertEqual(source[position['column']-1:position['end_column']-1],'"v1"')
        for selection in ({'function_id':'missing'},{'node_id':'missing'}):
            with self.subTest(selection=selection),self.assertRaises(PactError):
                self.locate(source,**selection)

    def test_json_rejects_invalid_programs_and_duplicate_keys(self):
        source=json.dumps(tiny()).replace('"cell": "counter"','"cell": "missing"')
        with self.assertRaises(PactError) as raised:self.locate(source)
        self.assertEqual(raised.exception.diagnostic['code'],'STATE_MISSING')
        source=json.dumps(tiny()).replace('"id": "z"','"id": "z", "\\u0069d": "z"')
        with self.assertRaises(PactError) as raised:self.locate(source)
        self.assertEqual(raised.exception.diagnostic['code'],'JSON_DUPLICATE_KEY')
        for source in ('{','[]','null'):
            with self.subTest(source=source),self.assertRaises(PactError):self.locate(source)

    def test_json_crlf_cli_preserves_snapshot_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.json'
            data=('\t'+json.dumps(tiny(),indent=2)).replace('\n','\r\n').encode()
            path.write_bytes(data)
            output=subprocess.run([sys.executable,'-m','pact','locate',str(path),'--function','step','--node','v'],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(output.returncode,0,output.stderr)
            result=json.loads(output.stdout)
            self.assertEqual(result['source_sha256'],hashlib.sha256(data).hexdigest())
            position=result['positions'][0];line=data.decode().split('\n')[position['line']-1]
            self.assertEqual(line[position['column']-1:position['end_column']-1],'"v"')
