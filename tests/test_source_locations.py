import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.revision import revision
from tests.test_module import tiny

ROOT = Path(__file__).resolve().parents[1]


class SourceLocationTests(unittest.TestCase):
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
            self.assertEqual(output.returncode,1)
            self.assertEqual(json.loads(output.stderr)['code'],'SOURCE_MAP_UNSUPPORTED')
