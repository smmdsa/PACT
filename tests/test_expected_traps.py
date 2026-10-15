import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.module import FORMAT, FORMATS, analyze_module, migrate_module
from pact.module_wasm import compile_module, compile_module_with_traps
from pact.module_build import build_module
from pact.reference import Machine
from tests.test_checked_assertions import checked

TRAPS = 'pact.module/0.5.0'


def negative(op='flow.guard'):
    doc = checked(op)
    doc['format'] = TRAPS
    doc['tests'].append({'id': 'reject-zero', 'function': 'step', 'args': [0],
                         'set': {}, 'expect': {'counter': [3]},
                         'trap': {'code': 'ASSERTION_FAILED', 'function': 'step', 'node': 'check'}})
    return doc


class TrapSchemaTests(unittest.TestCase):
    def reject(self, doc, code):
        with self.assertRaises(PactError) as raised:
            analyze_module(doc)
        self.assertEqual(raised.exception.diagnostic['code'], code)

    def test_version_inherits_checks_and_export_cases(self):
        self.assertEqual(FORMATS[-1], TRAPS)
        self.assertEqual(FORMAT, 'pact.module/0.2.0')
        self.assertEqual(analyze_module(negative())['declared_export_tests'],
                         {'step': ['reject-zero', 'success']})
        doc = negative();doc['tests'] = []
        self.reject(doc, 'EXPORT_EVIDENCE_MISSING')

    def test_legacy_schema_still_rejects_trap_metadata(self):
        doc = negative();doc['format'] = 'pact.module/0.4.0'
        self.reject(doc, 'SCHEMA_INVALID')

    def test_trap_can_be_the_only_assertion_but_cannot_have_result(self):
        doc = negative();doc['tests'][-1]['expect'] = {}
        analyze_module(doc)
        doc['tests'][-1]['result'] = 0
        self.reject(doc, 'TEST_INVALID')

    def test_trap_record_is_closed_and_qualified(self):
        for trap, code in [(None, 'SCHEMA_INVALID'), ([], 'SCHEMA_INVALID'),
                           ({}, 'SCHEMA_INVALID'),
                           ({'code': 'ANY', 'function': 'step', 'node': 'check'}, 'TEST_INVALID'),
                           ({'code': [], 'function': 'step', 'node': 'check'}, 'TEST_INVALID'),
                           ({'code': 'ASSERTION_FAILED', 'function': [], 'node': 'check'}, 'TEST_INVALID'),
                           ({'code': 'ASSERTION_FAILED', 'function': 'absent', 'node': 'check'}, 'TEST_INVALID'),
                           ({'code': 'ASSERTION_FAILED', 'function': 'step', 'node': []}, 'TEST_INVALID'),
                           ({'code': 'ASSERTION_FAILED', 'function': 'step', 'node': 'absent'}, 'TEST_INVALID'),
                           ({'code': 'STATE_BOUNDS', 'function': 'step', 'node': 'check'}, 'TEST_INVALID')]:
            with self.subTest(trap=trap):
                doc = negative();doc['tests'][-1]['trap'] = trap
                self.reject(doc, code)

    def test_all_source_representations_preserve_trap_declarations(self):
        doc = negative()
        for options in ({}, {'compressed': True}, {'literals': True}, {'inline': True}):
            self.assertEqual(loads(dumps(doc, **options)), doc)

    def test_forward_migration_preserves_binary_and_source(self):
        doc = checked();before = copy.deepcopy(doc)
        migrated = migrate_module(doc, TRAPS)
        self.assertEqual(doc, before)
        self.assertEqual(migrated['format'], TRAPS)
        self.assertEqual(compile_module(analyze_module(doc)), compile_module(analyze_module(migrated)))
        self.reject({**negative(), 'format': 'pact.module/0.3.0'}, 'OP_UNKNOWN')


class TrapExecutionTests(unittest.TestCase):
    def reject(self, doc, message=None):
        with self.assertRaises(PactError) as raised:
            build_module(doc)
        self.assertEqual(raised.exception.diagnostic['code'], 'TEST_FAILED')
        if message:
            self.assertIn(message, str(raised.exception))

    def test_guard_and_assert_mixed_positive_negative_cases(self):
        for op in ('flow.guard', 'flow.assert'):
            _, manifest = build_module(negative(op))
            self.assertEqual(len(manifest['evidence']), 2)
            for row in manifest['evidence']:
                self.assertEqual(row['reference'], 'tested')
                self.assertEqual(row['wasm'], 'tested')
            row = manifest['evidence'][-1]
            self.assertEqual(row['trap'], negative()['tests'][-1]['trap'])
            self.assertIsInstance(row['wasm_location']['offset'], int)

    def test_wrong_or_unreached_trap_and_unexpected_trap_reject(self):
        doc = negative();doc['tests'][-1]['args'] = [1]
        self.reject(doc)
        doc = negative();doc['functions'][0]['nodes'].append(
            {'id': 'unused', 'op': 'flow.assert', 'args': ['p']})
        doc['functions'][0]['nodes'].append({'id': 'both', 'op': 'flow.sequence', 'args': ['check', 'unused']})
        doc['functions'][0]['entry'] = 'both'
        doc['tests'][-1]['trap']['node'] = 'unused'
        self.reject(doc)
        doc = negative();del doc['tests'][-1]['trap']
        self.reject(doc)

    def test_post_trap_writes_and_fresh_case_instances(self):
        doc = negative('flow.assert')
        next(n for n in doc['functions'][0]['nodes'] if n['id'] == 'sequence')['args'] = ['s', 'check']
        doc['tests'][-1]['expect'] = {'counter': [10]}
        _, manifest = build_module(doc)
        self.assertEqual(len(manifest['evidence']), 2)
        doc['tests'][-1]['expect'] = {'counter': [3]}
        self.reject(doc)
        doc = negative();doc['tests'][-1].update(set={'counter': [18]}, expect={'counter': [18]})
        build_module(doc)

    def test_exact_internal_helper_attribution(self):
        doc = negative()
        helper = copy.deepcopy(doc['functions'][0]);helper['id'] = 'helper'
        caller = doc['functions'][0]
        caller['nodes'] = [{'id': 'p', 'op': 'local.get', 'name': 'predicate'},
                           {'id': 'invoke', 'op': 'call', 'target': 'helper', 'args': ['p']}]
        caller['entry'] = 'invoke'
        doc['functions'].append(helper)
        doc['tests'][-1]['trap']['function'] = 'helper'
        _, manifest = build_module(doc)
        self.assertEqual(manifest['evidence'][-1]['trap']['function'], 'helper')

    def test_bounds_division_remainder_and_overflow_sites(self):
        for op, a, b in [('state.load', 1, 0), ('state.load', -1, 0), ('state.store', 1, 0), ('i32.div_s', 1, 0),
                          ('i32.rem_s', 1, 0), ('i32.div_s', -2147483648, -1)]:
            with self.subTest(op=op, a=a, b=b):
                doc = negative();fn = doc['functions'][0]
                fn.update(params=[], result='unit' if op == 'state.store' else 'i32',
                          writes=['counter'] if op == 'state.store' else [], entry='fault')
                fn['nodes'] = [{'id': 'a', 'op': 'i32.const', 'value': a},
                               {'id': 'b', 'op': 'i32.const', 'value': b},
                               {'id': 'fault', 'op': op, **({'cell': 'counter', 'args': ['a']}
                                if op == 'state.load' else {'cell': 'counter', 'args': ['a', 'b']}
                                if op == 'state.store' else {'args': ['a', 'b']})}]
                if op == 'state.load':
                    fn['nodes'] = [node for node in fn['nodes'] if node['id'] != 'b']
                doc['tests'] = [{'id': 'fault', 'function': 'step', 'set': {}, 'expect': {},
                                 'trap': {'code': 'STATE_BOUNDS' if op.startswith('state.') else 'ARITHMETIC_TRAP',
                                          'function': 'step', 'node': 'fault'}}]
                _, manifest = build_module(doc)
                self.assertEqual(manifest['evidence'][0]['trap'], doc['tests'][0]['trap'])

    def test_numeric_positive_result_is_still_checked(self):
        doc = checked(numeric=True);doc['format'] = TRAPS
        _, manifest = build_module(doc)
        self.assertEqual(manifest['evidence'][0]['reference'], 'tested')
        doc['tests'][0]['result'] = 999
        self.reject(doc)

    def test_numeric_guard_trap_has_no_result_and_prefix_state_is_preserved(self):
        doc = checked(numeric=True);doc['format'] = TRAPS
        doc['cells'][0]['values'] = [3, 8]
        doc['tests'].append({'id': 'numeric-trap', 'function': 'step', 'args': [0],
                             'set': {'counter': [21]}, 'expect': {'counter': [21, 8]},
                             'trap': {'code': 'ASSERTION_FAILED', 'function': 'step', 'node': 'check'}})
        build_module(doc)

    def test_reference_budget_is_shared_and_cannot_satisfy_a_trap(self):
        doc = negative()
        machine = Machine(doc, evaluation_limit=1000, runtime_diagnostics=True)
        machine.call('step', 1)
        with patch('pact.module_tests.REFERENCE_TEST_BUDGET', machine.evaluations):
            with self.assertRaises(PactError) as raised:
                build_module(doc)
        self.assertEqual(raised.exception.diagnostic['code'], 'TEST_REFERENCE_LIMIT')


def node_cases(doc, map_change=None, stackless=False):
    plan = analyze_module(doc)
    binary, trap_map = compile_module_with_traps(plan)
    if map_change:
        map_change(trap_map)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        (directory/'module.wasm').write_bytes(binary)
        (directory/'cases.json').write_text(json.dumps({'tests': doc['tests'], 'layout': plan['layout'],
                                                      'trap_map': trap_map, 'reference_tested': True}))
        runner = root/'tools/check_module.mjs'
        command = ['node', str(runner), str(directory/'module.wasm'), str(directory/'cases.json')]
        if stackless:
            command = ['node', '--input-type=module', '-e',
                       "Error.prepareStackTrace=()=>'';process.argv.splice(1,0,'runner');await import(process.argv[4]);",
                       str(directory/'module.wasm'), str(directory/'cases.json'), runner.as_uri()]
        return subprocess.run(command, capture_output=True, timeout=15)


class WasmTrapAcceptanceTests(unittest.TestCase):
    def test_actual_engine_trap_requires_matching_hash_and_exact_site(self):
        self.assertEqual(node_cases(negative()).returncode, 0)
        mutations = [lambda m: m.update(wasm_sha256='0'*64),
                     lambda m: m.update(positions=[], complete=False),
                     lambda m: [p.update(node='other') for p in m['positions']],
                     lambda m: [p.update(kind='bounds') for p in m['positions']],
                     lambda m: [p.update(function='other') for p in m['positions']]]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = node_cases(negative(), mutation)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(result.stderr)['code'], 'TEST_FAILED')

    def test_missing_engine_stack_coordinates_rejects_expected_trap(self):
        result = node_cases(negative(), stackless=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no exact Wasm coordinates', json.loads(result.stderr)['message'])


class TrapCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'pact', *map(str, args)],
                              cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=20)

    def test_published_example_executes_all_three_cases(self):
        from pact.graph import load_document
        root = Path(__file__).resolve().parents[1]
        doc = load_document(root/'examples/counter.traps.pact')
        _, manifest = build_module(doc)
        self.assertEqual([row['id'] for row in manifest['evidence']],
                         ['success', 'reject-zero', 'writes-retained'])
        self.assertTrue(all(row['reference'] == row['wasm'] == 'tested' for row in manifest['evidence']))

    def test_build_patch_and_forward_migration(self):
        from pact.revision import revision
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);source = root/'source.json';output = root/'module.wasm'
            doc = negative();source.write_text(json.dumps(doc))
            result = self.run_cli('build', source, '-o', output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['evidence'][-1]['trap'], doc['tests'][-1]['trap'])
            original = output.read_bytes()
            doc['tests'][-1]['expect'] = {'counter': [999]}
            source.write_text(json.dumps(doc))
            result = self.run_cli('build', source, '-o', output)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)['code'], 'TEST_FAILED')
            self.assertEqual(output.read_bytes(), original)
            doc = negative();source.write_text(json.dumps(doc))
            replacement = copy.deepcopy(doc['tests'][-1]);replacement['args'] = [1]
            change = root/'change.json'
            change.write_text(json.dumps({'format': 'pact.patch/0.1.0',
                'expected_revision_sha256': revision(doc),
                'operations': [{'op': 'replace_test', 'id': replacement['id'], 'test': replacement}]}))
            target = root/'candidate.json'
            result = self.run_cli('patch', source, '--patch', change, '-o', target)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stderr)['code'], 'TEST_FAILED')
            self.assertFalse(target.exists())
            self.assertEqual(json.loads(source.read_text()), doc)
            legacy = checked();source.write_text(json.dumps(legacy))
            result = self.run_cli('migrate', source, '--to', TRAPS, '-o', target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(dict(json.loads(target.read_text()), format=legacy['format']), legacy)
