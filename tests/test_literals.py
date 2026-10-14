import copy
import json
from pathlib import Path
import unittest

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.graph import analyze
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.revision import revision
from pact.wasm import compile_plan
from tests.test_module import tiny

ROOT = Path(__file__).resolve().parents[1]


class LiteralTests(unittest.TestCase):
    def literal_source(self, document, compressed=False):
        try:
            return dumps(document, compressed=compressed, literals=True)
        except TypeError:
            self.fail('Literal frontend is not implemented')

    def test_examples_preserve_ir_revision_wasm_and_input(self):
        for name in ('hello', 'alien-harvest'):
            document = json.loads((ROOT / f'examples/{name}.pact.json').read_text())
            original = copy.deepcopy(document)
            for compressed in (False, True):
                with self.subTest(name=name, compressed=compressed):
                    source = self.literal_source(document, compressed)
                    self.assertTrue(source.startswith('pact 0.4\n'))
                    self.assertNotIn(' = i32.const ', source)
                    self.assertNotIn(' = utf8.literal ', source)
                    restored = loads(source)
                    self.assertEqual(restored, original)
                    self.assertEqual(document, original)
                    self.assertEqual(revision(restored), revision(original))
                    compiler, validator = ((compile_module, analyze_module) if 'functions' in document
                                           else (compile_plan, analyze))
                    self.assertEqual(compiler(validator(restored)), compiler(validator(original)))
                    self.assertLess(len(source.encode()), len(dumps(document, compressed=compressed).encode()))
                    if compressed and name == 'alien-harvest':
                        self.assertIn('\ncells.packed ', source)
                        self.assertIn('\nassets.shared ', source)
            self.assertEqual(dumps(document), (ROOT / f'examples/{name}.pact').read_text())

    def test_signed_integer_boundaries_and_stable_colon_ids(self):
        for value in (-2147483648, -42, 0, 2147483647):
            document = tiny()
            document['functions'][0]['nodes'][0].update(id='number:0', value=value)
            for node in document['functions'][0]['nodes']:
                if 'args' in node:
                    node['args'] = ['number:0' if ref == 'z' else ref for ref in node['args']]
            source = self.literal_source(document)
            self.assertIn(f'number:0 = {value}\n', source)
            self.assertEqual(loads(source), document)

    def test_quoted_unicode_strings_comments_and_escaped_newlines(self):
        for value in ('', 'a = b # c "quoted"\n雪\\end', 'before\u2028middle\u2029after\u0085', '😀'):
            document = json.loads((ROOT / 'examples/hello.pact.json').read_text())
            document['nodes'][0].update(id='text:0', value=value)
            document['nodes'][2]['args'][0] = 'text:0'
            document['contracts'][0]['value'] = value + document['nodes'][1]['value']
            source = self.literal_source(document)
            self.assertEqual(loads('# rationale\n' + source + '# trailing\n'), document)
        source = self.literal_source(document)
        encoded = json.dumps('😀', ensure_ascii=False)
        self.assertEqual(loads(source.replace(encoded, '"\\ud83d\\ude00"')), document)
        with self.assertRaises(PactError) as error:
            loads(source.replace(encoded, '"\\ud800"'))
        self.assertEqual(error.exception.diagnostic['code'], 'UTF8_INVALID')

    def test_older_headers_reject_bare_literals(self):
        for document in (tiny(), json.loads((ROOT / 'examples/hello.pact.json').read_text())):
            source = self.literal_source(document)
            for header in ('pact 0.2', 'pact 0.3'):
                with self.subTest(header=header), self.assertRaises(PactError):
                    loads(source.replace('pact 0.4', header, 1))

    def test_legacy_operations_still_valid_under_literal_header(self):
        for document in (tiny(), json.loads((ROOT / 'examples/hello.pact.json').read_text())):
            source = dumps(document).replace('pact 0.2', 'pact 0.4', 1)
            self.assertEqual(loads(source), document)

    def test_invalid_values_extra_operands_and_implicit_arguments_reject(self):
        source = self.literal_source(tiny())
        for value in ('true', 'false', 'null', '1.0', '1e0', 'NaN', 'Infinity', '[]', '[1]',
                      '{}', '{"a":1}', '2147483648', '-2147483649', '0 extra',
                      '"text" extra', '+1', '01', '-01'):
            with self.subTest(value=value), self.assertRaises(PactError):
                loads(source.replace('z = 0\n', f'z = {value}\n', 1))
        for expression in ('sum = add.wrap v 7', 'sum = add.wrap v "text"'):
            with self.subTest(expression=expression), self.assertRaises(PactError):
                loads(source.replace('sum = add.wrap v a', expression))

    def test_lowered_nodes_still_obey_original_profile_and_graph_rules(self):
        source = self.literal_source(tiny())
        with self.assertRaises(PactError) as error:
            loads(source.replace('z = 0\n', 'z = "numeric modules reject text"\n'))
        self.assertEqual(error.exception.diagnostic['code'], 'OP_UNKNOWN')
        with self.assertRaises(PactError):
            loads(source.replace('sum = add.wrap v a', 'sum = add.wrap sum a'))
        with self.assertRaises(PactError):
            loads(source.replace('z = 0\n', 'z = 0\nz = 0\n'))

    def test_combined_inline_and_bare_literals_preserve_order_and_identity(self):
        document = json.loads((ROOT / 'examples/alien-harvest.pact.json').read_text())
        source = dumps(document, inline=True, literals=True)
        self.assertIn('n0000=0', source)
        self.assertNotIn(' = i32.const ', source)
        self.assertEqual(loads(source), document)
        self.assertEqual(revision(loads(source)), revision(document))
        self.assertEqual(compile_module(analyze_module(loads(source))), compile_module(analyze_module(document)))
        tiny_source = dumps(tiny(), literals=True)
        with self.assertRaises(PactError):
            loads(tiny_source.replace('sum = add.wrap v a', 'sum = add.wrap v z=1'))

    def test_existing_revision_checked_patch_accepts_literal_source(self):
        from pact.transactions import apply_patch
        document = json.loads((ROOT / 'examples/alien-harvest.pact.json').read_text())
        patch = json.loads((ROOT / 'examples/patches/jump.patch.json').read_text())
        original = copy.deepcopy(document)
        restored = loads(self.literal_source(document, compressed=True))
        candidate = apply_patch(restored, patch)
        expected = apply_patch(document, patch)
        self.assertEqual(candidate, expected)
        self.assertEqual(document, original)
        self.assertEqual(restored, original)
        self.assertEqual(loads(self.literal_source(candidate, compressed=True)), expected)
        self.assertEqual(compile_module(analyze_module(candidate)), compile_module(analyze_module(expected)))


if __name__ == '__main__':
    unittest.main()
