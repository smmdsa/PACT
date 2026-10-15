"""Authored trusted fixtures for the in-container declaration runner."""
import importlib
import contextlib
import io
import unittest
from tests.test_module import tiny


class SandboxDeclarationTests(unittest.TestCase):
    def fixture(self):
        document=tiny()
        document['tests']=[{'id':'step.adds.seven','function':'step','set':{},'expect':{'counter':[10]}}]
        return document

    def execute(self,document):
        runner=importlib.import_module('benchmarks.sandbox.pact_tests')
        return runner.execute_declared_tests(document)

    def test_actual_wasm_executes_the_declared_expectation(self):
        report=self.execute(self.fixture())
        self.assertEqual(report,{'engine':'wasm','status':'passed','declared':1,'executed':1,'pass':True,'reason':None})

    def test_wrong_expectation_fails_even_when_source_is_valid(self):
        document=self.fixture();document['tests'][0]['expect']['counter']=[999]
        diagnostic=io.StringIO()
        with contextlib.redirect_stderr(diagnostic):report=self.execute(document)
        self.assertIn('expected 999',diagnostic.getvalue())
        self.assertIs(report['pass'],False)
        self.assertEqual(report['reason'],'TEST_FAILED')
        self.assertIsNone(report['executed'])

    def test_empty_legacy_declarations_are_not_a_pass(self):
        document=tiny();document['tests']=[]
        self.assertEqual(self.execute(document),{'engine':'wasm','status':'missing','declared':0,'executed':0,
                                               'pass':False,'reason':'NO_DECLARED_TESTS'})
