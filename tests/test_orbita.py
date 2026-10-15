"""Behavioral checks for the authored PACT interface kernel."""
import json
from pathlib import Path
import random
import unittest

from pact.diagnostics import PactError
from pact.graph import load_document
from pact.module_build import build_module
from pact.reference import Machine
from tests.test_module_execution import execute

ROOT=Path(__file__).resolve().parents[1]


class OrbitaTests(unittest.TestCase):
    def setUp(self):
        source=ROOT/'examples/orbita.pact'
        self.assertTrue(source.exists(),'The PACT interaction kernel has not been implemented')
        self.doc=load_document(source)
        self.vm=Machine(self.doc)

    def test_focus_and_lens_are_independent_of_investments(self):
        self.vm.call('orbit.select',5);self.vm.call('orbit.lens',2)
        self.assertEqual(self.vm.state['selected'],[5])
        self.assertEqual(self.vm.state['lens'],[2])
        self.assertEqual(self.vm.state['levels'],[0]*6)

    def test_budget_and_per_idea_limits(self):
        for index in (0,1):
            self.vm.call('orbit.select',index)
            for _ in range(3):self.vm.call('orbit.adjust',1)
        self.vm.call('orbit.select',2);self.vm.call('orbit.adjust',1)
        self.assertEqual(self.vm.state['levels'],[3,3,0,0,0,0])
        self.assertEqual(self.vm.state['spent'],[6])
        self.vm.call('orbit.select',0);self.vm.call('orbit.adjust',1)
        self.assertEqual(self.vm.state['levels'][0],3)
        self.vm.call('orbit.adjust',-1)
        self.assertEqual(self.vm.state['spent'],[5])

    def test_cannot_remove_from_an_empty_idea(self):
        self.vm.call('orbit.adjust',-1)
        self.assertEqual(self.vm.state['spent'],[0])
        self.assertEqual(self.vm.state['cursor'],[0])

    def test_undo_redo_and_forked_future(self):
        self.vm.call('orbit.adjust',1)
        self.vm.call('orbit.select',2);self.vm.call('orbit.adjust',1)
        self.vm.call('orbit.undo')
        self.assertEqual(self.vm.state['levels'],[1,0,0,0,0,0])
        self.vm.call('orbit.redo')
        self.assertEqual(self.vm.state['levels'],[1,0,1,0,0,0])
        self.vm.call('orbit.undo');self.vm.call('orbit.select',4);self.vm.call('orbit.adjust',1)
        self.vm.call('orbit.redo')
        self.assertEqual(self.vm.state['levels'],[1,0,0,0,1,0])
        self.assertEqual(self.vm.state['length'],[3])

    def test_history_keeps_latest_32_states(self):
        for i in range(80):self.vm.call('orbit.adjust',1 if i%2==0 else -1)
        self.assertEqual(self.vm.state['cursor'],[31])
        self.assertEqual(self.vm.state['length'],[32])
        self.vm.call('orbit.undo')
        self.assertEqual(self.vm.state['levels'],[1,0,0,0,0,0])
        self.vm.call('orbit.redo')
        self.assertEqual(self.vm.state['levels'],[0]*6)

    def test_reset_clears_history_and_focus(self):
        self.vm.call('orbit.adjust',1);self.vm.call('orbit.select',4);self.vm.call('orbit.lens',2)
        self.vm.call('orbit.reset')
        self.assertEqual(self.vm.state,Machine(self.doc).state)

    def test_invalid_parameters_trap_before_writes(self):
        for fn,values in [('orbit.select',[-1,6]),('orbit.lens',[-1,3]),('orbit.adjust',[-2,0,2])]:
            for value in values:
                before=json.dumps(self.vm.state)
                with self.assertRaises(PactError):self.vm.call(fn,value)
                self.assertEqual(json.dumps(self.vm.state),before)

    def test_compiled_wasm_matches_reference_across_decisions(self):
        rng=random.Random(17)
        calls=[{'fn':'orbit.undo'},{'fn':'orbit.redo'}]
        for i in range(100):
            calls.extend([{'fn':'orbit.select','args':[rng.randrange(6)]},
                          {'fn':'orbit.lens','args':[rng.randrange(3)]},
                          {'fn':'orbit.adjust','args':[rng.choice([-1,1])]}])
            if i%4==0:calls.append({'fn':'orbit.undo'})
            if i%9==0:calls.append({'fn':'orbit.redo'})
        for call in calls:
            self.vm.call(call['fn'],*call.get('args',[]))
            self.assertEqual(sum(self.vm.state['levels']),self.vm.state['spent'][0])
            self.assertTrue(0<=self.vm.state['spent'][0]<=6)
        actual,_=execute(self.doc,calls)
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual(json.loads(actual.stdout)['state'],self.vm.state)

    def test_every_export_has_executed_build_evidence(self):
        _,manifest=build_module(self.doc)
        self.assertEqual(set(manifest['declared_export_tests']),set(self.doc['exports']))
        self.assertTrue(all(row['status']=='tested' for row in manifest['evidence']))
