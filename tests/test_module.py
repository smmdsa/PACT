import copy
import unittest

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.inspection import inspect_function, symbols
from pact.module import analyze_module
from tools.make_game import game_document


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

    def test_state_reset_validation_inspection_and_structured_fixes(self):
        document = game_document()
        mutable_cells = [cell['id'] for cell in document['cells'] if cell['mutable']]
        init_fn = next(fn for fn in document['functions'] if fn['id'] == 'game.init')
        init_fn['nodes'] = [{'id': 'n0000', 'op': 'state.reset', 'cells': mutable_cells}]
        init_fn['entry'] = 'n0000'
        plan = analyze_module(document)
        self.assertEqual(plan['work']['game.init'], sum(len(cell['values']) for cell in document['cells'] if cell['mutable']))
        for kwargs in ({}, {'compressed': True}, {'inline': True}):
            text = dumps(document, **kwargs)
            self.assertIn('n0000 = reset [', text)
            self.assertEqual(loads(text), document)
        sym = symbols(document)
        init_sym = next(item for item in sym['functions'] if item['id'] == 'game.init')
        self.assertEqual(init_sym['write_cells'], sorted(mutable_cells))
        inspected = inspect_function(document, 'game.init')
        self.assertEqual([c['id'] for c in inspected['cells']['write']], sorted(mutable_cells))

        bad_writes = copy.deepcopy(document)
        bad_init = next(fn for fn in bad_writes['functions'] if fn['id'] == 'game.init')
        bad_init['writes'] = ['input.left']
        with self.assertRaises(PactError) as ctx:
            analyze_module(bad_writes)
        self.assertEqual(ctx.exception.diagnostic['code'], 'WRITE_MISMATCH')
        self.assertEqual(ctx.exception.diagnostic['fix'], {
            'op': 'set_writes',
            'function': 'game.init',
            'declared_writes': ['input.left'],
            'expected_writes': sorted(mutable_cells),
        })

        bad_unreach = copy.deepcopy(document)
        bad_unreach_init = next(fn for fn in bad_unreach['functions'] if fn['id'] == 'game.init')
        bad_unreach_init['nodes'].append({'id': 'dead0', 'op': 'i32.const', 'value': 42})
        with self.assertRaises(PactError) as ctx:
            analyze_module(bad_unreach)
        self.assertEqual(ctx.exception.diagnostic['code'], 'NODE_UNREACHABLE')
        self.assertEqual(ctx.exception.diagnostic['fix'], {
            'op': 'remove_unreachable',
            'function': 'game.init',
            'unreachable_nodes': ['dead0'],
        })

        for bad_cells, expected_code in [
            (['level.tiles'], 'STATE_IMMUTABLE'),
            (['missing.cell'], 'STATE_MISSING'),
            (['input.left', 'input.left'], 'ID_DUPLICATE'),
            ([], 'ARGUMENT_LIMIT'),
        ]:
            candidate = copy.deepcopy(document)
            fn = next(item for item in candidate['functions'] if item['id'] == 'game.init')
            fn['nodes'] = [{'id': 'n0000', 'op': 'state.reset', 'cells': bad_cells}]
            fn['writes'] = sorted(set(bad_cells))
            with self.subTest(bad_cells=bad_cells), self.assertRaises(PactError) as ctx:
                analyze_module(candidate)
            self.assertEqual(ctx.exception.diagnostic['code'], expected_code)


if __name__ == '__main__':
    unittest.main()
