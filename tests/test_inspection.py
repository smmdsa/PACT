import copy
import hashlib
import json
import unittest

from pact.diagnostics import PactError
from pact.inspection import inspect_function, symbols


def fixture():
    def wrapper(name, target):
        return {'id': name, 'params': [], 'locals': [], 'result': 'unit',
                'writes': ['counter'], 'entry': 'invoke',
                'nodes': [{'id': 'invoke', 'op': 'call', 'target': target, 'args': []}]}
    reader = {'id': 'reader', 'params': [], 'locals': [], 'result': 'i32', 'writes': [],
              'entry': 'sum', 'nodes': [
                  {'id': 'zero', 'op': 'i32.const', 'value': 0},
                  {'id': 'load', 'op': 'state.load', 'cell': 'mapdata', 'args': ['zero']},
                  {'id': 'amount', 'op': 'const.load', 'name': 'amount'},
                  {'id': 'sum', 'op': 'i32.add_wrap', 'args': ['load', 'amount']}]}
    writer = {'id': 'writer', 'params': [], 'locals': [], 'result': 'unit',
              'writes': ['counter'], 'entry': 'store', 'nodes': [
                  {'id': 'zero', 'op': 'i32.const', 'value': 0},
                  {'id': 'value', 'op': 'call', 'target': 'reader', 'args': []},
                  {'id': 'store', 'op': 'state.store', 'cell': 'counter', 'args': ['zero', 'value']}]}
    other = {'id': 'other', 'params': [], 'locals': [], 'result': 'i32', 'writes': [],
             'entry': 'zero', 'nodes': [{'id': 'zero', 'op': 'i32.const', 'value': 0}]}
    return {'format': 'pact.module/0.1.0', 'constants': {'unused': 2, 'amount': 7},
            'cells': [{'id': 'counter', 'values': [3], 'mutable': True},
                      {'id': 'mapdata', 'values': [12345678] * 64, 'mutable': False},
                      {'id': 'unused', 'values': [87654321], 'mutable': False}],
            'functions': [wrapper('ancestor', 'outer'), wrapper('step', 'writer'), reader,
                          wrapper('outer', 'step'), writer, other],
            'exports': ['ancestor', 'outer', 'step', 'other'],
            'assets': {'palettes': [], 'tiles': []}, 'presentation': {},
            'tests': [{'id': name + '.test', 'function': name, 'set': {},
                       'expect': {'mapdata': [12345678] * 64},
                       **({'result': 0} if name == 'other' else {})}
                      for name in ['step', 'other', 'outer', 'ancestor']]}


class InspectionTests(unittest.TestCase):
    def test_closure_preserves_selected_and_dependency_functions(self):
        doc = fixture()
        result = inspect_function(doc, 'step')
        self.assertEqual(result['format'], 'pact.inspection/0.1.0')
        self.assertTrue(result['context_only'])
        self.assertFalse(result['buildable'])
        self.assertEqual(result['selected_function'], doc['functions'][1])
        self.assertEqual(result['direct_callees'], ['writer'])
        self.assertEqual(result['transitive_callees'], ['reader', 'writer'])
        self.assertEqual(result['direct_callers'], ['outer'])
        self.assertEqual(result['transitive_callers'], ['ancestor', 'outer'])
        self.assertEqual([fn['id'] for fn in result['dependency_functions']], ['reader', 'writer'])
        self.assertNotIn('nodes', result['dependency_functions'][0])
        self.assertEqual(result['constants'], {'amount': 7})
        self.assertEqual(result['cells'], {
            'read': [{'id': 'mapdata', 'type': 'i32', 'count': 64, 'mutable': False}],
            'write': [{'id': 'counter', 'type': 'i32', 'count': 1, 'mutable': True}]})
        self.assertEqual(result['test_summaries'], [{'id': name + '.test', 'function': name}
                                         for name in ['ancestor', 'outer', 'step']])

    def test_no_bulk_cell_values_assets_or_test_state_in_context(self):
        result = inspect_function(fixture(), 'step')
        encoded = json.dumps(result)
        for forbidden in ['12345678', '87654321', '"values"', '"assets":', '"expect"', '"set"']:
            self.assertNotIn(forbidden, encoded)

    def test_revision_uses_canonical_document_and_key_order_is_irrelevant(self):
        doc = fixture()
        reordered = json.loads(json.dumps(doc, sort_keys=True))
        expected = hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(',', ':'),
                                            ensure_ascii=False).encode('utf-8')).hexdigest()
        first = inspect_function(doc, 'step')
        self.assertEqual(first['semantic_revision_sha256'], expected)
        self.assertEqual(first, inspect_function(reordered, 'step'))
        self.assertEqual(json.dumps(first), json.dumps(inspect_function(reordered, 'step')))
        self.assertEqual(first, inspect_function(doc, 'step'))

    def test_revision_changes_for_hidden_semantics_and_ordered_arrays(self):
        doc = fixture()
        before = inspect_function(doc, 'step')['semantic_revision_sha256']
        changed = copy.deepcopy(doc)
        changed['cells'][2]['values'][0] += 1
        self.assertNotEqual(before, inspect_function(changed, 'step')['semantic_revision_sha256'])
        changed = copy.deepcopy(doc)
        changed['functions'].reverse()
        self.assertNotEqual(before, inspect_function(changed, 'step')['semantic_revision_sha256'])

    def test_results_are_detached_from_input(self):
        doc = fixture()
        result = inspect_function(doc, 'step')
        result['selected_function']['writes'].clear()
        result['dependency_functions'][0]['params'].append('changed')
        self.assertEqual(doc, fixture())

    def test_symbols_sorted_functions_and_transitive_footprints(self):
        result = symbols(fixture())
        self.assertEqual(result['format'], 'pact.symbols/0.1.0')
        self.assertTrue(result['context_only'])
        self.assertFalse(result['buildable'])
        self.assertEqual([fn['id'] for fn in result['functions']],
                         ['ancestor', 'other', 'outer', 'reader', 'step', 'writer'])
        step = next(fn for fn in result['functions'] if fn['id'] == 'step')
        self.assertEqual(step['read_cells'], ['mapdata'])
        self.assertEqual(step['write_cells'], ['counter'])
        self.assertEqual(step['constants'], ['amount'])
        self.assertEqual(step['direct_callees'], ['writer'])
        self.assertEqual(step['transitive_callees'], ['reader', 'writer'])
        self.assertTrue(step['exported'])
        self.assertNotIn('12345678', json.dumps(result))

    def test_missing_function_raises_pact_error(self):
        with self.assertRaises(PactError) as error:
            inspect_function(fixture(), 'missing')
        self.assertEqual(error.exception.diagnostic['code'], 'FUNCTION_MISSING')

    def test_text_graph_explicitly_unsupported(self):
        graph = {'format': 'pact.graph/0.0.1'}
        for action in [lambda: symbols(graph), lambda: inspect_function(graph, 'step')]:
            with self.assertRaises(PactError) as error:
                action()
            self.assertEqual(error.exception.diagnostic['code'], 'INSPECTION_UNSUPPORTED')

    def test_full_source_validated_even_when_invalid_function_is_unrelated(self):
        doc = fixture()
        doc['functions'][-1]['nodes'][0]['op'] = 'invented'
        for action in [lambda: symbols(doc), lambda: inspect_function(doc, 'step')]:
            with self.assertRaises(PactError) as error:
                action()
            self.assertEqual(error.exception.diagnostic['code'], 'OP_UNKNOWN')

    def test_malformed_document_raises_pact_error(self):
        for doc in [None, [], {}, {'format': 'invented'}]:
            for action in [lambda: symbols(doc), lambda: inspect_function(doc, 'step')]:
                with self.assertRaises(PactError):
                    action()
