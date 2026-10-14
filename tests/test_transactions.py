"""Pure revision-checked transactions, without filesystem or runtime authority."""
import copy
import hashlib
import importlib
import importlib.util
import json
import unittest

from pact.diagnostics import PactError
from pact.inspection import symbols
from pact.module import analyze_module
from pact.module_wasm import compile_module


def fixture():
    return {'format': 'pact.module/0.1.0', 'constants': {'amount': 7},
            'cells': [{'id': 'counter', 'values': [0], 'mutable': True}],
            'functions': [{'id': 'read', 'params': [], 'locals': [], 'result': 'i32',
                           'writes': [], 'entry': 'value',
                           'nodes': [{'id': 'value', 'op': 'const.load', 'name': 'amount'}]}],
            'exports': ['read'], 'assets': {'palettes': [], 'tiles': []}, 'presentation': {},
            'tests': [{'id': 'read.test', 'function': 'read', 'set': {}, 'expect': {}, 'result': 7}]}


class TransactionTests(unittest.TestCase):
    def setUp(self):
        for name in ('pact.transactions', 'pact.revision'):
            self.assertIsNotNone(importlib.util.find_spec(name), f'{name} API is missing')
        self.apply = importlib.import_module('pact.transactions').apply_patch
        self.revision = importlib.import_module('pact.revision').revision
        self.doc = fixture()

    def patch(self, *operations):
        return {'format': 'pact.patch/0.1.0',
                'expected_revision_sha256': self.revision(self.doc), 'operations': list(operations)}

    def reject(self, patch, code=None, document=None):
        doc = self.doc if document is None else document
        before, before_patch = copy.deepcopy(doc), copy.deepcopy(patch)
        with self.assertRaises(PactError) as error:
            self.apply(doc, patch)
        if code:
            self.assertEqual(error.exception.diagnostic['code'], code)
        self.assertEqual(doc, before)
        self.assertEqual(patch, before_patch)

    def test_shared_revision_matches_existing_inspection_canonicalization(self):
        expected = hashlib.sha256(json.dumps(self.doc, sort_keys=True, separators=(',', ':'),
                                            ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(self.revision(self.doc), expected)
        self.assertEqual(symbols(self.doc)['semantic_revision_sha256'], expected)
        reordered = json.loads(json.dumps(self.doc, sort_keys=True))
        self.assertEqual(self.revision(reordered), expected)

    def test_revision_preserves_array_order_and_hidden_values(self):
        changed = copy.deepcopy(self.doc)
        changed['cells'][0]['values'][0] = 1
        self.assertNotEqual(self.revision(changed), self.revision(self.doc))
        changed = copy.deepcopy(self.doc)
        changed['cells'].append({'id': 'other', 'values': [0], 'mutable': True})
        before = self.revision(changed)
        changed['cells'].reverse()
        self.assertNotEqual(self.revision(changed), before)

    def test_valid_three_operation_candidate_compiles_and_inputs_are_detached(self):
        node = {'id': 'value', 'op': 'i32.const', 'value': 9}
        test = {**self.doc['tests'][0], 'result': 9}
        patch = self.patch({'op': 'replace_node', 'function': 'read', 'id': 'value', 'node': node},
                           {'op': 'set_constant', 'name': 'amount', 'value': 10},
                           {'op': 'replace_test', 'id': 'read.test', 'test': test})
        original, original_patch = copy.deepcopy(self.doc), copy.deepcopy(patch)
        candidate = self.apply(self.doc, patch)
        self.assertEqual(candidate['functions'][0]['nodes'], [node])
        self.assertEqual(candidate['constants']['amount'], 10)
        self.assertEqual(candidate['tests'], [test])
        self.assertTrue(compile_module(analyze_module(candidate)).startswith(b'\x00asm'))
        self.assertNotEqual(self.revision(candidate), self.revision(self.doc))
        candidate['functions'][0]['nodes'][0]['value'] = 22
        candidate['cells'][0]['values'][0] = 3
        candidate['tests'][0]['result'] = 22
        self.assertEqual(self.doc, original)
        self.assertEqual(patch, original_patch)

    def test_pure_validation_does_not_execute_declared_tests(self):
        patch = self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8})
        candidate = self.apply(self.doc, patch)
        self.assertEqual(candidate['constants']['amount'], 8)
        self.assertEqual(candidate['tests'][0]['result'], 7)

    def test_stale_revision_rejected(self):
        patch = self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8})
        patch['expected_revision_sha256'] = '0' * 64
        self.reject(patch, 'PATCH_STALE')

    def test_revision_schema_is_exact_lowercase_sha256(self):
        for digest in (None, [], '', 'a' * 63, 'A' * 64, 'g' * 64, 1):
            with self.subTest(digest=digest):
                patch = self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8})
                patch['expected_revision_sha256'] = digest
                self.reject(patch, 'PATCH_INVALID')

    def test_closed_patch_schema_and_version(self):
        base = self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8})
        for patch in (None, [], {}, {**base, 'extra': 1},
                      {**base, 'format': 'pact.patch/9'},
                      {key: value for key, value in base.items() if key != 'operations'}):
            with self.subTest(patch=patch):
                self.reject(patch)

    def test_operations_are_bounded_list(self):
        for ops in (None, {}, [], [None] * 257):
            with self.subTest(ops=type(ops).__name__):
                patch = self.patch()
                patch['operations'] = ops
                self.reject(patch, 'PATCH_INVALID')

    def test_256_distinct_operations_are_accepted(self):
        self.doc['constants'] = {f'c{i}': i for i in range(256)}
        self.doc['functions'][0]['nodes'][0]['name'] = 'c0'
        patch = self.patch(*[{'op': 'set_constant', 'name': f'c{i}', 'value': i + 1}
                             for i in range(256)])
        self.assertEqual(self.apply(self.doc, patch)['constants']['c255'], 256)

    def test_closed_operation_schema_and_unknown_operation(self):
        valid = {'op': 'set_constant', 'name': 'amount', 'value': 8}
        for op in (None, [], {}, {**valid, 'extra': True},
                   {'op': 'set_constant', 'name': 'amount'},
                   {**valid, 'op': 'delete_constant'}):
            with self.subTest(op=op):
                self.reject(self.patch(op))

    def test_missing_targets_and_invalid_target_identifiers(self):
        for op in ({'op': 'set_constant', 'name': 'missing', 'value': 1},
                   {'op': 'replace_node', 'function': 'missing', 'id': 'value', 'node': {}},
                   {'op': 'replace_node', 'function': 'read', 'id': 'missing', 'node': {}},
                   {'op': 'replace_test', 'id': 'missing', 'test': {}},
                   {'op': 'set_constant', 'name': [], 'value': 1},
                   {'op': 'replace_node', 'function': [], 'id': 'value', 'node': {}},
                   {'op': 'replace_test', 'id': [], 'test': {}}):
            with self.subTest(op=op):
                self.reject(self.patch(op))

    def test_replacement_ids_must_stay_stable(self):
        for op in ({'op': 'replace_node', 'function': 'read', 'id': 'value',
                    'node': {'id': 'renamed', 'op': 'i32.const', 'value': 1}},
                   {'op': 'replace_test', 'id': 'read.test',
                    'test': {**self.doc['tests'][0], 'id': 'renamed'}}):
            with self.subTest(op=op):
                self.reject(self.patch(op), 'PATCH_ID_CHANGED')

    def test_duplicate_targets_rejected_even_when_identical(self):
        for op in ({'op': 'set_constant', 'name': 'amount', 'value': 8},
                   {'op': 'replace_node', 'function': 'read', 'id': 'value',
                    'node': {'id': 'value', 'op': 'i32.const', 'value': 7}},
                   {'op': 'replace_test', 'id': 'read.test', 'test': self.doc['tests'][0]}):
            with self.subTest(op=op['op']):
                self.reject(self.patch(op, copy.deepcopy(op)), 'PATCH_TARGET_DUPLICATE')

    def test_same_node_id_in_different_functions_is_not_duplicate(self):
        fn = copy.deepcopy(self.doc['functions'][0])
        fn['id'] = 'other'
        self.doc['functions'].append(fn)
        patch = self.patch(*[{'op': 'replace_node', 'function': fn, 'id': 'value',
                             'node': {'id': 'value', 'op': 'i32.const', 'value': 9}}
                            for fn in ('read', 'other')])
        self.assertEqual([fn['nodes'][0]['value'] for fn in self.apply(self.doc, patch)['functions']], [9, 9])

    def test_invalid_candidate_rejected_after_valid_earlier_operation(self):
        patch = self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8},
                           {'op': 'replace_node', 'function': 'read', 'id': 'value',
                            'node': {'id': 'value', 'op': 'call', 'target': 'read', 'args': []}})
        self.reject(patch, 'CALL_RECURSION')

    def test_full_candidate_validation_rejects_bad_nodes_constants_and_tests(self):
        for op in ({'op': 'set_constant', 'name': 'amount', 'value': True},
                   {'op': 'set_constant', 'name': 'amount', 'value': 2**31},
                   {'op': 'replace_node', 'function': 'read', 'id': 'value',
                    'node': {'id': 'value', 'op': 'i32.const', 'value': 1, 'extra': 1}},
                   {'op': 'replace_node', 'function': 'read', 'id': 'value',
                    'node': {'id': 'value', 'op': 'i32.eqz', 'args': ['missing']}},
                   {'op': 'replace_test', 'id': 'read.test',
                    'test': {**self.doc['tests'][0], 'function': 'missing'}},
                   {'op': 'replace_test', 'id': 'read.test',
                    'test': {**self.doc['tests'][0], 'result': True}}):
            with self.subTest(op=op):
                self.reject(self.patch(op))

    def test_full_original_validation_prevents_repairing_invalid_input(self):
        self.doc['constants']['amount'] = True
        self.reject(self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8}), 'INTEGER_INVALID')

    def test_graphs_are_not_supported(self):
        self.reject(self.patch({'op': 'set_constant', 'name': 'amount', 'value': 8}),
                    document={'format': 'pact.graph/0.0.1'})
