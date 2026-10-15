import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pact.diagnostics import PactError
from pact.module import analyze_module
from pact.compact import dumps, loads
from pact.module import FORMATS, UNIT_FORMAT, migrate_module
from pact.module_build import build_module
from pact.module_wasm import compile_module
from pact.inspection import inspect_function, symbols
from pact.revision import revision
from tests.test_module import tiny

UNITS = 'pact.module/0.6.0'


def signature(params=None, result='unit', locals_=None, literals=None):
    return {'params': params or {}, 'locals': locals_ or {}, 'literals': literals or {}, 'result': result}


def unit_counter():
    doc = tiny();doc['format'] = UNITS
    doc['tests'] = [{'id': 'step', 'function': 'step', 'set': {}, 'expect': {'counter': [10]}}]
    doc['units'] = {'names': ['pixel', 'tick'], 'cells': {'counter': 'pixel'},
                    'constants': {'amount': 'pixel'}, 'functions': {}}
    return doc


def arithmetic(op='i32.add_wrap', left='pixel', right='pixel', result='pixel'):
    doc = unit_counter()
    doc['functions'] = [{'id': 'sum', 'params': ['x', 'y'], 'locals': [], 'result': 'i32', 'writes': [],
                         'entry': 'calculate', 'nodes': [
                             {'id': 'x', 'op': 'local.get', 'name': 'x'},
                             {'id': 'y', 'op': 'local.get', 'name': 'y'},
                             {'id': 'calculate', 'op': op, 'args': ['x', 'y']}]}]
    doc['exports'] = ['sum']
    doc['tests'] = [{'id': 'sum', 'function': 'sum', 'args': [2, 3], 'set': {}, 'expect': {}, 'result': 5}]
    doc['units']['functions'] = {'sum': signature({'x': left, 'y': right}, result)}
    return doc


class UnitInferenceTests(unittest.TestCase):
    def reject(self, doc, code='UNIT_MISMATCH'):
        with self.assertRaises(PactError) as raised:
            analyze_module(doc)
        self.assertEqual(raised.exception.diagnostic['code'], code)
        return raised.exception.diagnostic

    def test_state_and_constants_have_nominal_units(self):
        plan = analyze_module(unit_counter())
        self.assertEqual(plan['unit_contracts']['cells'], {'counter': 'pixel'})
        self.assertEqual(plan['unit_contracts']['functions']['step']['result'], 'unit')
        doc = unit_counter();doc['units']['constants']['amount'] = 'tick'
        diagnostic = self.reject(doc)
        self.assertEqual((diagnostic['function'], diagnostic['node']), ('step', 'sum'))

    def test_add_sub_and_remainder_require_identical_units(self):
        for op in ('i32.add_wrap', 'i32.sub_wrap', 'i32.rem_s'):
            analyze_module(arithmetic(op))
            self.reject(arithmetic(op, right='tick'))
            self.reject(arithmetic(op, right='i32'))

    def test_scaling_ratio_and_unsupported_products(self):
        for left, right, result in [('pixel', 'i32', 'pixel'), ('i32', 'pixel', 'pixel'), ('i32', 'i32', 'i32')]:
            analyze_module(arithmetic('i32.mul_wrap', left, right, result))
        self.reject(arithmetic('i32.mul_wrap'))
        self.reject(arithmetic('i32.mul_wrap', right='tick'))
        analyze_module(arithmetic('i32.div_s', result='i32'))
        analyze_module(arithmetic('i32.div_s', right='i32'))
        self.reject(arithmetic('i32.div_s', left='i32', result='i32'))
        self.reject(arithmetic('i32.div_s', right='tick'))

    def test_comparisons_and_bitwise_contracts(self):
        for op in ('i32.eq', 'i32.ne', 'i32.lt_s', 'i32.gt_s', 'i32.le_s', 'i32.ge_s'):
            analyze_module(arithmetic(op, result='i32'))
            self.reject(arithmetic(op, right='tick', result='i32'))
        for op in ('i32.and', 'i32.or'):
            analyze_module(arithmetic(op, 'i32', 'i32', 'i32'))
            self.reject(arithmetic(op, result='i32'))

    def test_branch_guard_predicate_and_result_units(self):
        doc = arithmetic();fn = doc['functions'][0]
        fn['params'].append('predicate')
        fn['nodes'].append({'id': 'p', 'op': 'local.get', 'name': 'predicate'})
        fn['nodes'][-2].update(op='flow.if', args=['p', 'x', 'y'])
        doc['tests'][0]['args'].append(1)
        analyze_module(doc)
        doc['units']['functions']['sum']['params']['y'] = 'tick'
        self.reject(doc)
        doc['units']['functions']['sum']['params']['y'] = 'pixel'
        doc['units']['functions']['sum']['params']['predicate'] = 'pixel'
        self.reject(doc)
        doc = arithmetic();doc['units']['functions']['sum']['result'] = 'tick'
        self.reject(doc)
        doc = arithmetic();fn = doc['functions'][0]
        fn['nodes'][-1].update(op='flow.guard')
        self.reject(doc)

    def test_unitful_indices_and_repeat_counters_reject(self):
        doc = unit_counter()
        doc['units']['functions']['step'] = signature(literals={'z': 'pixel'})
        self.reject(doc)
        doc = unit_counter();fn = doc['functions'][0]
        fn.update(locals=['index'], entry='repeat', nodes=[
            {'id': 'reset', 'op': 'state.reset', 'cells': ['counter']},
            {'id': 'repeat', 'op': 'flow.repeat', 'counter': 'index', 'count': 2, 'args': ['reset']}])
        doc['units']['functions']['step'] = signature(locals_={'index': 'pixel'})
        self.reject(doc)

    def test_helpers_enforce_argument_and_result_contracts(self):
        doc = arithmetic();helper = copy.deepcopy(doc['functions'][0]);helper['id'] = 'helper'
        fn = doc['functions'][0];fn['nodes'][-1].update(op='call', target='helper')
        doc['functions'].append(helper)
        doc['units']['functions']['helper'] = signature({'x': 'pixel', 'y': 'pixel'}, 'pixel')
        analyze_module(doc)
        doc['units']['functions']['sum']['params']['x'] = 'tick'
        self.reject(doc)

    def test_locals_and_stores_cannot_erase_units(self):
        doc = unit_counter();fn = doc['functions'][0]
        fn.update(params=['value'], locals=['tmp'], writes=[], entry='save', nodes=[
            {'id': 'value', 'op': 'local.get', 'name': 'value'},
            {'id': 'save', 'op': 'local.set', 'name': 'tmp', 'args': ['value']}])
        doc['tests'][0].update(args=[3], expect={'counter': [3]})
        doc['units']['functions']['step'] = signature({'value': 'tick'}, locals_={'tmp': 'pixel'})
        self.reject(doc)
        doc['units']['functions']['step']['params']['value'] = 'pixel'
        build_module(doc)
        doc = unit_counter();fn = doc['functions'][0]
        fn['nodes'] = [{'id': 'z', 'op': 'i32.const', 'value': 0},
                       {'id': 'value', 'op': 'const.load', 'name': 'amount'},
                       {'id': 's', 'op': 'state.store', 'cell': 'counter', 'args': ['z', 'value']}]
        doc['units']['cells']['counter'] = 'tick'
        self.assertEqual(self.reject(doc)['node'], 's')

    def test_assert_predicates_are_dimensionless_and_eqz_accepts_typed_zero(self):
        doc = arithmetic();fn = doc['functions'][0]
        fn.update(params=['x'], result='unit', entry='assertion')
        fn['nodes'] = [{'id': 'x', 'op': 'local.get', 'name': 'x'},
                       {'id': 'assertion', 'op': 'flow.assert', 'args': ['x']}]
        doc['tests'] = [{'id': 'step', 'function': 'sum', 'args': [1], 'set': {}, 'expect': {'counter': [3]}}]
        doc['units']['functions']['sum'] = signature({'x': 'pixel'})
        self.reject(doc)
        fn['nodes'].insert(1, {'id': 'is-zero', 'op': 'i32.eqz', 'args': ['x']})
        fn['nodes'][-1]['args'] = ['is-zero'];doc['tests'][0]['args'] = [0]
        build_module(doc)


class UnitDeclarationTests(unittest.TestCase):
    def test_malformed_metadata_always_rejects_with_pact_error(self):
        variants = [None, [], {}, {'names': [], 'cells': {}, 'constants': {}, 'functions': {}, 'extra': 1}]
        for value in variants:
            doc = unit_counter();doc['units'] = value
            with self.subTest(value=value), self.assertRaises(PactError):
                analyze_module(doc)

    def test_unknown_bindings_names_and_literal_kinds_reject(self):
        for area, value in [('names', ['pixel', 'pixel']), ('names', ['i32']), ('names', ['unit']),
                             ('names', [None]), ('cells', {'missing': 'pixel'}),
                             ('cells', {'counter': []}), ('constants', {'amount': 'unknown'}),
                             ('functions', {'missing': signature()}),
                             ('functions', {'step': signature(literals={'sum': 'pixel'})}),
                             ('functions', {'step': signature(params={'missing': 'pixel'})}),
                             ('functions', {'step': signature(result='pixel')}),
                             ('functions', {'step': []})]:
            doc = unit_counter();doc['units'][area] = value
            with self.subTest(area=area, value=value), self.assertRaises(PactError):
                analyze_module(doc)

    def test_legacy_schema_rejects_units(self):
        doc = unit_counter();doc['format'] = 'pact.module/0.5.0'
        with self.assertRaises(PactError) as raised:
            analyze_module(doc)
        self.assertEqual(raised.exception.diagnostic['code'], 'SCHEMA_INVALID')


class UnitIntegrationTests(unittest.TestCase):
    def test_cli_check_exposes_units_and_explicit_migration_is_compatible(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'source.pact';target = Path(directory)/'migrated.pact'
            doc = unit_counter();source.write_text(dumps(doc))
            result = subprocess.run([sys.executable, '-m', 'pact', 'check', str(source)],
                                     cwd=root, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['unit_contracts']['cells'], {'counter': 'pixel'})
            doc.pop('units');doc['format'] = 'pact.module/0.5.0';source.write_text(dumps(doc))
            result = subprocess.run([sys.executable, '-m', 'pact', 'migrate', str(source), '--to', UNITS,
                                     '-o', str(target)], cwd=root, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(loads(target.read_text()), dict(doc, format=UNITS))

    def test_manifest_and_selected_context_include_contracts(self):
        doc = unit_counter();_, manifest = build_module(doc)
        self.assertEqual(manifest['unit_contracts'], analyze_module(doc)['unit_contracts'])
        context = inspect_function(doc, 'step')
        self.assertEqual(context['unit_contracts']['constants'], {'amount': 'pixel'})
        self.assertEqual(context['cells']['read'][0]['unit'], 'pixel')
        discovered = symbols(doc)
        self.assertEqual(discovered['unit_contracts']['functions']['step']['result'], 'unit')
        self.assertNotIn('literals', discovered['unit_contracts']['functions']['step'])

    def test_helper_literals_stay_omitted_from_selected_context(self):
        doc = arithmetic();helper = copy.deepcopy(doc['functions'][0]);helper['id'] = 'helper'
        helper['nodes'][0] = {'id': 'x', 'op': 'i32.const', 'value': 2}
        helper['params'] = ['y']
        doc['functions'][0]['nodes'] = [n for n in doc['functions'][0]['nodes'] if n['id'] != 'x']
        doc['functions'][0]['nodes'][-1].update(op='call', target='helper', args=['y'])
        doc['functions'].append(helper)
        doc['units']['functions']['helper'] = signature({'y': 'pixel'}, 'pixel', literals={'x': 'pixel'})
        context = inspect_function(doc, 'sum')
        self.assertNotIn('literals', context['unit_contracts']['functions']['helper'])
        self.assertIn('dependency_literal_unit_bindings', context['omitted'])

    def test_representations_migration_and_annotations_preserve_runtime_bytes(self):
        self.assertEqual(FORMATS[-1], UNIT_FORMAT)
        doc = unit_counter();binary = compile_module(analyze_module(doc))
        for options in ({}, {'compressed': True}, {'inline': True}, {'literals': True}):
            self.assertEqual(loads(dumps(doc, **options)), doc)
        legacy = copy.deepcopy(doc);legacy.pop('units');legacy['format'] = 'pact.module/0.5.0'
        migrated = migrate_module(legacy, UNITS)
        self.assertEqual(compile_module(analyze_module(legacy)), binary)
        self.assertEqual(compile_module(analyze_module(migrated)), binary)
        self.assertNotEqual(revision(legacy), revision(doc))
        self.assertEqual(migrated, dict(legacy, format=UNITS))
        self.assertEqual(migrate_module(tiny())['format'], 'pact.module/0.2.0')

    def test_explicit_literal_and_zero_initialized_local_contracts_execute(self):
        doc = arithmetic();fn = doc['functions'][0]
        fn['params'] = ['y'];fn['nodes'][0] = {'id': 'x', 'op': 'i32.const', 'value': 2}
        doc['tests'][0]['args'] = [3]
        doc['units']['functions']['sum'] = signature({'y': 'pixel'}, 'pixel', literals={'x': 'pixel'})
        build_module(doc)
        doc['units']['functions']['sum']['literals']['x'] = 'tick'
        with self.assertRaises(PactError) as raised:
            analyze_module(doc)
        self.assertEqual(raised.exception.diagnostic['code'], 'UNIT_MISMATCH')
        doc = arithmetic();fn = doc['functions'][0]
        fn.update(params=[], locals=['tmp'], entry='read', nodes=[{'id': 'read', 'op': 'local.get', 'name': 'tmp'}])
        doc['units']['functions']['sum'] = signature(result='pixel', locals_={'tmp': 'pixel'})
        doc['tests'][0].update(args=[], result=0)
        build_module(doc)

    def test_reset_keeps_typed_initial_state(self):
        doc = unit_counter();fn = doc['functions'][0]
        fn.update(entry='reset', nodes=[{'id': 'reset', 'op': 'state.reset', 'cells': ['counter']}])
        doc['tests'][0].update(set={'counter': [21]}, expect={'counter': [3]})
        build_module(doc)

    def test_published_unit_example_builds_with_contracts(self):
        from pact.graph import load_document
        root = Path(__file__).resolve().parents[1]
        _, manifest = build_module(load_document(root/'examples/counter.units.pact'))
        self.assertEqual(manifest['unit_contracts']['cells']['counter'], 'pixel')
        self.assertTrue(all(row['reference'] == row['wasm'] == 'tested' for row in manifest['evidence']))

    def test_expected_traps_inherit_dual_engine_acceptance(self):
        from tests.test_expected_traps import negative
        doc = negative();doc['format'] = UNITS
        doc['units'] = unit_counter()['units']
        _, manifest = build_module(doc)
        self.assertEqual(manifest['evidence'][-1]['reference'], 'tested')
        self.assertEqual(manifest['evidence'][-1]['wasm'], 'tested')

    def test_cli_patch_rejects_unitful_product_without_publishing(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory);source = directory/'source.pact';output = directory/'candidate.pact'
            doc = unit_counter();source.write_text(dumps(doc))
            replacement = copy.deepcopy(doc['functions'][0]['nodes'][3]);replacement['op'] = 'i32.mul_wrap'
            patch = {'format': 'pact.patch/0.1.0', 'expected_revision_sha256': revision(doc),
                     'operations': [{'op': 'replace_node', 'function': 'step', 'id': 'sum', 'node': replacement}]}
            change = directory/'change.json';change.write_text(json.dumps(patch))
            result = subprocess.run([sys.executable, '-m', 'pact', 'patch', str(source), '--patch', str(change),
                                     '-o', str(output)], cwd=root, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)['code'], 'UNIT_MISMATCH')
            self.assertFalse(output.exists())
            self.assertEqual(loads(source.read_text()), doc)
