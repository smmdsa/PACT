import copy
import unittest

from pact.diagnostics import PactError
from pact.module import analyze_module


def tiny():
    return {
        'format': 'pact.module/0.1.0', 'constants': {'amount': 7},
        'cells': [{'id': 'counter', 'values': [3], 'mutable': True}],
        'functions': [{
            'id': 'step', 'params': [], 'locals': [], 'result': 'unit', 'writes': ['counter'],
            'entry': 's', 'nodes': [
                {'id': 'z', 'op': 'i32.const', 'value': 0},
                {'id': 'v', 'op': 'state.load', 'cell': 'counter', 'args': ['z']},
                {'id': 'a', 'op': 'const.load', 'name': 'amount'},
                {'id': 'sum', 'op': 'i32.add_wrap', 'args': ['v', 'a']},
                {'id': 's', 'op': 'state.store', 'cell': 'counter', 'args': ['z', 'sum']}
            ]}],
        'exports': ['step'], 'assets': {'palettes': [], 'tiles': []}, 'presentation': {}, 'tests': []
    }


class ModuleTests(unittest.TestCase):
    def reject(self, doc, code):
        with self.assertRaises(PactError) as error:
            analyze_module(doc)
        self.assertEqual(error.exception.diagnostic['code'], code)

    def test_stateful_module_has_checked_layout(self):
        plan = analyze_module(tiny())
        self.assertIsInstance(plan, dict)
        self.assertEqual(plan['layout']['counter'], {'offset': 0, 'count': 1, 'mutable': True})
        self.assertEqual(plan['function_types']['step'], {'params': 0, 'result': 'unit'})

    def test_write_outside_declared_responsibility(self):
        doc = tiny()
        doc['functions'][0]['writes'] = []
        self.reject(doc, 'WRITE_MISMATCH')

    def test_immutable_store_is_rejected(self):
        doc = tiny()
        doc['cells'][0]['mutable'] = False
        self.reject(doc, 'STATE_IMMUTABLE')

    def test_recursive_call_is_rejected(self):
        doc = tiny()
        doc['functions'][0]['nodes'].append({'id': 'recur', 'op': 'call', 'target': 'step', 'args': []})
        doc['functions'][0]['entry'] = 'recur'
        self.reject(doc, 'CALL_RECURSION')

    def test_effect_node_cannot_have_two_execution_edges(self):
        doc=tiny();fn=doc['functions'][0]
        fn['nodes'].append({'id':'twice','op':'flow.sequence','args':['s','s']})
        fn['entry']='twice'
        self.reject(doc,'EFFECT_SHARED')

    def test_unknown_operation_is_rejected(self):
        doc = tiny()
        doc['functions'][0]['nodes'][-1]['op'] = 'platformer.update'
        self.reject(doc, 'OP_UNKNOWN')

    def test_bad_tile_dimensions_are_rejected(self):
        doc = tiny()
        doc['assets'] = {'palettes': [{'id': 'p', 'colors': {'Ink': '#000000'}}],
                         'tiles': [{'id': 't', 'palette': 'p', 'symbols': {'.': None}, 'pixels': ['........']}]}
        self.reject(doc, 'ASSET_INVALID')

    def test_bad_array_reference_is_rejected(self):
        doc = tiny()
        doc['functions'][0]['nodes'][-1]['cell'] = 'missing'
        self.reject(doc, 'STATE_MISSING')


if __name__ == '__main__':
    unittest.main()
