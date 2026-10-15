import copy
import unittest

from pact.compact import dumps, loads
from pact.diagnostics import PactError
from pact.inspection import inspect_function, symbols
from pact.module import FORMAT, FORMATS, analyze_module, migrate_module
from pact.module_build import build_module
from pact.module_wasm import compile_module
from pact.revision import revision
from tests.test_module import tiny

TESTED = 'pact.module/0.3.0'


def tested():
    doc = tiny()
    doc['format'] = TESTED
    doc['tests'] = [{'id': 'step.test', 'function': 'step', 'set': {},
                     'expect': {'counter': [10]}}]
    return doc


class ExportEvidenceTests(unittest.TestCase):
    def rejection(self, document, code, operation=analyze_module):
        with self.assertRaises(PactError) as error:
            operation(document)
        self.assertEqual(error.exception.diagnostic['code'], code)
        return error.exception.diagnostic

    def test_new_format_is_opt_in_and_retains_historical_default(self):
        from pact.module import TESTED_FORMAT
        self.assertEqual(FORMAT, 'pact.module/0.2.0')
        self.assertEqual(TESTED_FORMAT, TESTED)
        self.assertEqual(FORMATS, ('pact.module/0.1.0', FORMAT, TESTED, 'pact.module/0.4.0', 'pact.module/0.5.0'))
        self.assertEqual(analyze_module(tested())['format'], 'pact.module-plan/0.3.0')

    def test_missing_exports_have_sorted_structured_fix(self):
        doc = tested()
        doc['tests'] = []
        for name in ('zebra', 'alpha'):
            fn = copy.deepcopy(doc['functions'][0])
            fn['id'] = name
            doc['functions'].append(fn)
            doc['exports'].append(name)
        diagnostic = self.rejection(doc, 'EXPORT_EVIDENCE_MISSING')
        self.assertEqual(diagnostic['fix'], {'op': 'add_export_tests',
                                          'functions': ['alpha', 'step', 'zebra']})

    def test_map_orders_exports_and_test_ids_without_mutating_source(self):
        doc = tested()
        fn = copy.deepcopy(doc['functions'][0])
        fn['id'] = 'alpha'
        doc['functions'].append(fn)
        doc['exports'].append('alpha')
        for name, target in [('z.case', 'step'), ('a.case', 'step'), ('alpha.case', 'alpha')]:
            case = copy.deepcopy(doc['tests'][0])
            case.update(id=name, function=target)
            doc['tests'].append(case)
        before = copy.deepcopy(doc)
        evidence = analyze_module(doc)['declared_export_tests']
        self.assertEqual(list(evidence), ['alpha', 'step'])
        self.assertEqual(evidence, {'alpha': ['alpha.case'], 'step': ['a.case', 'step.test', 'z.case']})
        self.assertEqual(doc, before)

    def test_helpers_need_no_direct_case_and_tests_still_require_exports(self):
        doc = tested()
        helper = copy.deepcopy(doc['functions'][0])
        helper['id'] = 'helper'
        doc['functions'].append(helper)
        doc['functions'][0].update(entry='invoke', nodes=[
            {'id': 'invoke', 'op': 'call', 'target': 'helper', 'args': []}])
        self.assertEqual(analyze_module(doc)['declared_export_tests'], {'step': ['step.test']})
        doc['tests'][0]['function'] = 'helper'
        self.rejection(doc, 'TEST_INVALID')

    def test_normal_case_validation_precedes_coverage(self):
        mutations = [
            ('ID_DUPLICATE', lambda d: d['tests'].append(copy.deepcopy(d['tests'][0]))),
            ('TEST_INVALID', lambda d: d['tests'][0].update(function='unknown')),
            ('TEST_INVALID', lambda d: d['tests'][0].update(args=[1])),
            ('TEST_EMPTY', lambda d: d['tests'][0].update(expect={})),
            ('TEST_INVALID', lambda d: d['tests'][0].update(expect={'counter': [1, 2]})),
            ('SCHEMA_INVALID', lambda d: d['tests'][0].update(extra=True)),
        ]
        for code, mutate in mutations:
            with self.subTest(code=code):
                doc = tested()
                uncovered = copy.deepcopy(doc['functions'][0])
                uncovered['id'] = 'uncovered'
                doc['functions'].append(uncovered)
                doc['exports'].append('uncovered')
                mutate(doc)
                self.rejection(doc, code)

    def test_empty_exports_need_no_tests(self):
        doc = tested()
        doc.update(exports=[], tests=[])
        self.assertEqual(analyze_module(doc)['declared_export_tests'], {})

    def test_only_new_format_exposes_maps_in_context_and_build(self):
        expected = {'step': ['step.test']}
        doc = tested()
        for result in (inspect_function(doc, 'step'), symbols(doc), build_module(doc)[1]):
            self.assertEqual(result['declared_export_tests'], expected)
        for version in FORMATS[:2]:
            with self.subTest(version=version):
                legacy = tested()
                legacy.update(format=version, tests=[])
                for result in (analyze_module(legacy), inspect_function(legacy, 'step'),
                               symbols(legacy), build_module(legacy)[1]):
                    self.assertNotIn('declared_export_tests', result)

    def test_declared_coverage_is_not_executed_build_evidence(self):
        doc = tested()
        doc['tests'][0]['expect']['counter'] = [999]
        self.assertEqual(analyze_module(doc)['declared_export_tests'], {'step': ['step.test']})
        self.assertEqual(inspect_function(doc, 'step')['declared_export_tests'], {'step': ['step.test']})
        self.rejection(doc, 'TEST_FAILED', build_module)
        binary, manifest = build_module(tested())
        self.assertTrue(binary.startswith(b'\0asm'))
        self.assertEqual(len(manifest['evidence']), 1)

    def test_forward_migrations_preserve_semantics_binary_and_input(self):
        for source_version, target in [('pact.module/0.1.0', FORMAT),
                                       ('pact.module/0.1.0', TESTED), (FORMAT, TESTED)]:
            with self.subTest(source=source_version, target=target):
                source = tested()
                source['format'] = source_version
                before = copy.deepcopy(source)
                migrated = migrate_module(source, target_format=target)
                self.assertEqual(migrated['format'], target)
                self.assertEqual(source, before)
                self.assertEqual({k: v for k, v in migrated.items() if k != 'format'},
                                 {k: v for k, v in source.items() if k != 'format'})
                self.assertNotEqual(revision(source), revision(migrated))
                self.assertEqual(compile_module(analyze_module(source)), compile_module(analyze_module(migrated)))
                migrated['cells'][0]['values'][0] = 77
                self.assertEqual(source, before)
        self.assertEqual(migrate_module(tiny())['format'], FORMAT)

    def test_invalid_noop_and_downgrade_migrations_reject(self):
        for source_version, target in [(FORMAT, FORMAT), (TESTED, TESTED),
                                       (TESTED, FORMAT), (FORMAT, 'pact.module/0.1.0'),
                                       ('pact.module/0.1.0', 'pact.module/9.0.0')]:
            with self.subTest(source=source_version, target=target):
                doc = tested()
                doc['format'] = source_version
                self.rejection(doc, 'MIGRATION_UNSUPPORTED',
                               lambda d: migrate_module(d, target_format=target))
        doc = tiny()
        before = copy.deepcopy(doc)
        self.rejection(doc, 'EXPORT_EVIDENCE_MISSING',
                       lambda d: migrate_module(d, target_format=TESTED))
        self.assertEqual(doc, before)
        doc['functions'][0]['writes'] = []
        self.rejection(doc, 'WRITE_MISMATCH', lambda d: migrate_module(d, target_format=TESTED))

    def test_representations_preserve_declared_format_revision_and_wasm(self):
        source = tested()
        for options in ({}, {'compressed': True}, {'literals': True}, {'inline': True}):
            with self.subTest(options=options):
                restored = loads(dumps(source, **options))
                self.assertEqual(restored, source)
                self.assertEqual(revision(restored), revision(source))
                self.assertEqual(compile_module(analyze_module(restored)), compile_module(analyze_module(source)))
