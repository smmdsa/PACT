import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.module import FORMAT, FORMATS, TESTED_FORMAT, analyze_module, migrate_module
from pact.module_build import build_module
from pact.module_wasm import compile_module
from pact.reference import Machine
from tests.test_module import tiny

CHECKED = 'pact.module/0.4.0'


def checked(op='flow.guard', numeric=False):
    doc = tiny()
    doc['format'] = CHECKED
    fn = doc['functions'][0]
    fn['params'] = ['predicate']
    fn['nodes'].append({'id': 'p', 'op': 'local.get', 'name': 'predicate'})
    if numeric:
        fn.update(result='i32', writes=[])
        fn['nodes'] = [node for node in fn['nodes'] if node['id'] != 's']
    body = 'sum' if numeric else 's'
    args = ['p', body] if op == 'flow.guard' else ['p']
    fn['nodes'].append({'id': 'check', 'op': op, 'args': args})
    fn['entry'] = 'check'
    if op == 'flow.assert':
        fn['nodes'].append({'id': 'sequence', 'op': 'flow.sequence', 'args': ['check', 's']})
        fn['entry'] = 'sequence'
    doc['tests'] = [{'id': 'success', 'function': 'step', 'args': [1], 'set': {},
                     'expect': {} if numeric else {'counter': [10]},
                     **({'result': 10} if numeric else {})}]
    return doc


def wasm_calls(doc, predicates):
    plan = analyze_module(doc)
    script = """import fs from 'node:fs';
const q=JSON.parse(fs.readFileSync(process.argv[2]));
const {instance}=await WebAssembly.instantiate(fs.readFileSync(process.argv[1]),{});
const view=new DataView(instance.exports.memory.buffer);
const state=()=>Object.fromEntries(Object.entries(q.layout).map(([id,c])=>
  [id,Array.from({length:c.count},(_,i)=>view.getInt32(c.offset+i*4,true))]));
const calls=q.predicates.map(p=>{
  try {return {result:instance.exports.step(p)??null,state:state()};}
  catch(e) {return {trap:e instanceof WebAssembly.RuntimeError,state:state()};}
});
console.log(JSON.stringify(calls));"""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'module.wasm').write_bytes(compile_module(plan))
        (root / 'calls.json').write_text(json.dumps({'layout': plan['layout'], 'predicates': predicates}))
        result = subprocess.run(['node', '--input-type=module', '-e', script,
                                 str(root / 'module.wasm'), str(root / 'calls.json')],
                                capture_output=True, timeout=15)
    if result.returncode:
        raise AssertionError(result.stderr.decode())
    return json.loads(result.stdout)


class CheckedAssertionsTests(unittest.TestCase):
    def reject(self, doc, code, operation=analyze_module):
        with self.assertRaises(PactError) as error:
            operation(doc)
        self.assertEqual(error.exception.diagnostic['code'], code)
        return error.exception.diagnostic

    def test_format_defaults_and_coverage(self):
        from pact.module import CHECKED_FORMAT
        self.assertEqual(CHECKED_FORMAT, CHECKED)
        self.assertEqual(FORMAT, 'pact.module/0.2.0')
        self.assertEqual(TESTED_FORMAT, 'pact.module/0.3.0')
        self.assertEqual(FORMATS[3], CHECKED)
        self.assertEqual(analyze_module(checked())['declared_export_tests'], {'step': ['success']})
        doc = checked()
        doc['tests'] = []
        self.reject(doc, 'EXPORT_EVIDENCE_MISSING')

    def test_operations_are_version_gated(self):
        for version in FORMATS[:3]:
            for op in ('flow.assert', 'flow.guard'):
                with self.subTest(version=version, op=op):
                    doc = checked(op)
                    doc['format'] = version
                    self.reject(doc, 'OP_UNKNOWN')
        doc = checked()
        fn = doc['functions'][0]
        fn.update(params=[], entry='reset', nodes=[{'id': 'reset', 'op': 'state.reset', 'cells': ['counter']}])
        doc['tests'][0].update(args=[], expect={'counter': [3]})
        self.assertEqual(Machine(doc).call('step'), None)

    def test_typed_arity(self):
        for op, invalid in [('flow.assert', []), ('flow.assert', ['p', 'p']),
                            ('flow.guard', ['p']), ('flow.guard', ['p', 's', 'p'])]:
            with self.subTest(op=op, args=invalid):
                doc = checked(op)
                next(n for n in doc['functions'][0]['nodes'] if n['id'] == 'check')['args'] = invalid
                self.reject(doc, 'ARITY_INVALID')
        for op in ('flow.assert', 'flow.guard'):
            doc = checked(op)
            next(n for n in doc['functions'][0]['nodes'] if n['id'] == 'check')['args'][0] = 's'
            self.reject(doc, 'TYPE_MISMATCH')

    def test_nonzero_and_zero_reference_and_wasm(self):
        for op, numeric in [('flow.assert', False), ('flow.guard', False), ('flow.guard', True)]:
            with self.subTest(op=op, numeric=numeric):
                doc = checked(op, numeric)
                vm = Machine(doc)
                predicates = [1, -1, -(2**31), 2147483647, 0]
                expected = []
                for predicate in predicates:
                    if predicate:
                        expected.append({'result': vm.call('step', predicate), 'state': copy.deepcopy(vm.state)})
                    else:
                        diagnostic = self.reject(doc, 'ASSERTION_FAILED', lambda _: vm.call('step', predicate))
                        self.assertEqual(diagnostic['function'], 'step')
                        self.assertEqual(diagnostic['node'], 'check')
                        expected.append({'trap': True, 'state': copy.deepcopy(vm.state)})
                self.assertEqual(wasm_calls(doc, predicates), expected)

    def test_guard_executes_body_once_and_postcondition_preserves_writes(self):
        doc = checked()
        self.assertEqual(wasm_calls(doc, [0, 1, 0]), [
            {'trap': True, 'state': {'counter': [3]}},
            {'result': None, 'state': {'counter': [10]}},
            {'trap': True, 'state': {'counter': [10]}}])
        post = checked('flow.assert')
        next(n for n in post['functions'][0]['nodes'] if n['id'] == 'sequence')['args'] = ['s', 'check']
        vm = Machine(post)
        self.reject(post, 'ASSERTION_FAILED', lambda _: vm.call('step', 0))
        self.assertEqual(vm.state, {'counter': [10]})
        self.assertEqual(wasm_calls(post, [0]), [{'trap': True, 'state': vm.state}])

    def test_false_guard_skips_a_trapping_body(self):
        doc = checked(numeric=True)
        fn = doc['functions'][0]
        fn['nodes'] = [{'id': 'p', 'op': 'local.get', 'name': 'predicate'},
                       {'id': 'zero', 'op': 'i32.const', 'value': 0},
                       {'id': 'divide', 'op': 'i32.div_s', 'args': ['p', 'zero']},
                       {'id': 'check', 'op': 'flow.guard', 'args': ['p', 'divide']}]
        vm = Machine(doc)
        self.reject(doc, 'ASSERTION_FAILED', lambda _: vm.call('step', 0))
        with self.assertRaises(ArithmeticError):
            vm.call('step', 1)
        self.assertEqual(wasm_calls(doc, [0, 1]), [{'trap': True, 'state': {'counter': [3]}}] * 2)

    def test_predicate_trap_precedes_writes_and_shared_reads_are_not_snapshots(self):
        doc = checked()
        fn = doc['functions'][0]
        next(n for n in fn['nodes'] if n['id'] == 'check')['args'][0] = 'v'
        fn['nodes'] = [n for n in fn['nodes'] if n['id'] != 'p']
        next(n for n in fn['nodes'] if n['id'] == 'z')['value'] = 1
        vm = Machine(doc)
        with self.assertRaises(IndexError):
            vm.call('step', 1)
        self.assertEqual(vm.state, {'counter': [3]})
        self.assertEqual(wasm_calls(doc, [1]), [{'trap': True, 'state': vm.state}])

        doc = checked()
        fn = doc['functions'][0]
        fn['nodes'] = [n for n in fn['nodes'] if n['id'] != 'p']
        fn['nodes'].extend([
            {'id': 'post', 'op': 'flow.assert', 'args': ['v']},
            {'id': 'sequence', 'op': 'flow.sequence', 'args': ['check', 'post']}])
        fn['entry'] = 'sequence'
        next(n for n in fn['nodes'] if n['id'] == 'check')['args'][0] = 'v'
        doc['constants']['amount'] = -3
        vm = Machine(doc)
        self.reject(doc, 'ASSERTION_FAILED', lambda _: vm.call('step', 1))
        self.assertEqual(vm.state, {'counter': [0]})
        self.assertEqual(wasm_calls(doc, [1]), [{'trap': True, 'state': vm.state}])

    def test_guard_transitive_call_effects_and_nested_result_type(self):
        doc = checked()
        fn = doc['functions'][0]
        helper = copy.deepcopy(tiny()['functions'][0])
        helper['id'] = 'helper'
        doc['functions'].append(helper)
        fn['nodes'] = [{'id': 'p', 'op': 'local.get', 'name': 'predicate'},
                       {'id': 'invoke', 'op': 'call', 'target': 'helper', 'args': []},
                       {'id': 'check', 'op': 'flow.guard', 'args': ['p', 'invoke']}]
        self.assertEqual(wasm_calls(doc, [0, 1]), [
            {'trap': True, 'state': {'counter': [3]}},
            {'result': None, 'state': {'counter': [10]}}])
        fn['nodes'].extend([
            {'id': 'skip', 'op': 'flow.sequence', 'args': []},
            {'id': 'branch', 'op': 'flow.if', 'args': ['p', 'check', 'skip']}])
        fn['entry'] = 'branch'
        self.assertEqual(wasm_calls(doc, [0, 1]), [
            {'result': None, 'state': {'counter': [3]}},
            {'result': None, 'state': {'counter': [10]}}])
        fn['writes'] = []
        self.reject(doc, 'WRITE_MISMATCH')

        doc = checked(numeric=True)
        fn = doc['functions'][0]
        fn['nodes'].append({'id': 'branch', 'op': 'flow.if', 'args': ['p', 'check', 'a']})
        fn['entry'] = 'branch'
        self.assertEqual(wasm_calls(doc, [0, 1]), [
            {'result': 7, 'state': {'counter': [3]}},
            {'result': 10, 'state': {'counter': [3]}}])

    def test_effect_inference_and_single_use_edges(self):
        doc = checked()
        doc['functions'][0]['writes'] = []
        self.reject(doc, 'WRITE_MISMATCH')
        doc = checked()
        doc['functions'][0]['result'] = 'i32'
        self.reject(doc, 'TYPE_MISMATCH')
        for op in ('flow.assert', 'flow.guard'):
            doc = checked(op)
            fn = doc['functions'][0]
            entry = fn['entry']
            fn['nodes'].append({'id': 'twice', 'op': 'flow.sequence', 'args': [entry, entry]})
            fn['entry'] = 'twice'
            self.reject(doc, 'EFFECT_SHARED')

    def test_conservative_work_budget_includes_guard_body(self):
        doc = checked()
        fn = doc['functions'][0]
        fn['locals'] = ['i', 'j']
        fn['nodes'].extend([
            {'id': 'assertion', 'op': 'flow.assert', 'args': ['p']},
            {'id': 'body', 'op': 'flow.sequence', 'args': ['assertion', 's']},
            {'id': 'inner', 'op': 'flow.repeat', 'count': 256, 'counter': 'i', 'args': ['body']},
            {'id': 'outer', 'op': 'flow.repeat', 'count': 256, 'counter': 'j', 'args': ['inner']}])
        next(n for n in fn['nodes'] if n['id'] == 'check')['args'][1] = 'outer'
        self.reject(doc, 'COMPILER_BUDGET')

    def test_roundtrips_aliases_and_forward_migration_binary(self):
        for op in ('flow.assert', 'flow.guard'):
            source = checked(op)
            binary = compile_module(analyze_module(source))
            for options in ({}, {'compressed': True}, {'literals': True}, {'inline': True}):
                text = dumps(source, **options)
                self.assertIn(' = ' + op.split('.')[1] + ' ', text)
                restored = loads(text)
                self.assertEqual(restored, source)
                self.assertEqual(compile_module(analyze_module(restored)), binary)
        for version in FORMATS[:3]:
            source = tiny()
            source['format'] = version
            source['tests'] = [{'id': 'success', 'function': 'step', 'set': {}, 'expect': {'counter': [10]}}]
            before = copy.deepcopy(source)
            migrated = migrate_module(source, CHECKED)
            self.assertEqual(source, before)
            self.assertEqual(compile_module(analyze_module(source)), compile_module(analyze_module(migrated)))
        self.assertEqual(migrate_module(tiny())['format'], FORMAT)

    def test_build_success_and_unexpected_trap_failure(self):
        for numeric in (False, True):
            doc = checked(numeric=numeric)
            binary, manifest = build_module(doc)
            self.assertTrue(binary.startswith(b'\0asm'))
            self.assertEqual(len(manifest['evidence']), 1)
            self.assertEqual(manifest['declared_export_tests'], {'step': ['success']})
            doc['tests'][0]['args'] = [0]
            self.reject(doc, 'TEST_FAILED', build_module)
