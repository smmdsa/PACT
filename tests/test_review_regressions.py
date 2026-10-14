import copy
import json
import re
import unittest
from pact.diagnostics import PactError
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.browser import game_html
from tests.test_module import tiny
from tools.make_game import game_document


class ReviewRegressions(unittest.TestCase):
    def reject(self,document,code):
        with self.assertRaises(PactError) as caught:analyze_module(document)
        self.assertEqual(caught.exception.diagnostic['code'],code)

    def test_unhashable_export_is_structured_rejection(self):
        doc=tiny();doc['exports']=[{}];self.reject(doc,'EXPORT_INVALID')

    def test_nonstring_cell_id_is_structured_rejection(self):
        doc=tiny();doc['cells'].append({'id':1,'values':[0],'mutable':True});self.reject(doc,'ID_INVALID')

    def test_surrogate_in_metadata_is_structured_rejection(self):
        doc=tiny();doc['presentation']={'title':'\ud800'};self.reject(doc,'UTF8_INVALID')

    def test_missing_presentation_cell_is_rejected(self):
        doc=game_document();doc['presentation']['map']['cell']='does.not.exist';self.reject(doc,'PRESENTATION_INVALID')

    def test_wrong_map_extent_is_rejected(self):
        doc=game_document();doc['presentation']['map']['columns']=999999;self.reject(doc,'PRESENTATION_INVALID')

    def test_input_cells_must_be_mutable(self):
        doc=game_document()
        next(cell for cell in doc['cells'] if cell['id']=='input.left')['mutable']=False
        self.reject(doc,'PRESENTATION_INVALID')

    def test_memory_export_is_reserved(self):
        doc=tiny();doc['functions'][0]['id']='memory';doc['exports']=['memory'];self.reject(doc,'EXPORT_INVALID')

    def test_cross_function_expression_depth_is_bounded(self):
        doc=tiny();doc['functions']=[];doc['exports']=['f0']
        for i in range(20):
            nodes=[{'id':'n0','op':'call','target':f'f{i+1}','args':[]}] if i<19 else [{'id':'n0','op':'i32.const','value':0}]
            for j in range(1,71):nodes.append({'id':f'n{j}','op':'i32.eqz','args':[f'n{j-1}']})
            doc['functions'].append({'id':f'f{i}','params':[],'locals':[],'result':'i32','writes':[],'nodes':nodes,'entry':'n70'})
        self.reject(doc,'EVALUATION_DEPTH')

    def test_compiler_expansion_has_aggregate_budget(self):
        doc=tiny();doc['functions']=[];doc['exports']=['f0']
        for i in range(2):
            nodes=[{'id':'n0','op':'i32.const','value':1}]
            for j in range(1,20):nodes.append({'id':f'n{j}','op':'i32.add_wrap','args':[f'n{j-1}',f'n{j-1}']})
            doc['functions'].append({'id':f'f{i}','params':[],'locals':[],'result':'i32','writes':[],'nodes':nodes,'entry':'n19'})
        self.reject(doc,'COMPILER_BUDGET')

    def test_html_placeholder_inside_data_is_preserved(self):
        doc=game_document();doc['presentation']['title']='__RUNTIME__'
        html=game_html(doc,b'abc',{'format':'test','title':'__SOURCE__'}).decode()
        source=re.search(r'<script id="pact-source" type="application/json">(.*?)</script>',html,re.S).group(1)
        self.assertEqual(json.loads(source)['presentation']['title'],'__RUNTIME__')
        self.assertIn('"title":"__SOURCE__"',html)
