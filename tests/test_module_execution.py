from pact.module import migrate_module
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.reference import Machine
from tests.test_graph import ROOT
from tests.test_module import tiny
from tools.make_game import game_document


def execute(document, calls):
    plan = analyze_module(document)
    binary = compile_module(plan)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root/'module.wasm').write_bytes(binary)
        (root/'request.json').write_text(json.dumps({'calls': calls, 'layout': plan['layout']}))
        script = """import fs from 'node:fs';
const q=JSON.parse(fs.readFileSync(process.argv[2]));
const {instance}=await WebAssembly.instantiate(fs.readFileSync(process.argv[1]),{});
const memory=new DataView(instance.exports.memory.buffer);
const results=q.calls.map(c=>{
  for(const [key,values] of Object.entries(c.set||{})) { const cell=q.layout[key]; values.forEach((v,i)=>memory.setInt32(cell.offset+i*4,v,true)); }
  return instance.exports[c.fn](...(c.args||[]))??null;
});
const state=Object.fromEntries(Object.entries(q.layout).map(([id,c])=>[id,Array.from({length:c.count},(_,i)=>memory.getInt32(c.offset+i*4,true))]));
console.log(JSON.stringify({results,state}));"""
        output = subprocess.run(['node','--input-type=module','-e',script,str(root/'module.wasm'),str(root/'request.json')],capture_output=True,timeout=15)
        return output, plan


class NumericExecutionTests(unittest.TestCase):
    def test_mutable_expression_reads_current_state(self):
        doc = tiny()
        ref = Machine(doc)
        ref.call('step'); ref.call('step')
        self.assertEqual(ref.state['counter'], [17])
        output, _ = execute(doc, [{'fn':'step'}, {'fn':'step'}])
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(json.loads(output.stdout)['state']['counter'], [17])

    def test_runtime_bounds_reject_invalid_index(self):
        doc = tiny()
        doc['functions'][0]['nodes'][0]['value'] = 1
        output, _ = execute(doc, [{'fn':'step'}])
        self.assertNotEqual(output.returncode, 0)
        self.assertIn(b'unreachable', output.stderr)

    def test_wrap_semantics_are_explicit(self):
        doc = tiny()
        doc['cells'][0]['values'] = [2147483647]
        doc['constants']['amount'] = 1
        output, _ = execute(doc, [{'fn':'step'}])
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(json.loads(output.stdout)['state']['counter'], [-2147483648])

    def test_bounded_repeat_cannot_be_extended_by_counter_write(self):
        doc = tiny()
        fn = doc['functions'][0]
        fn['locals'] = ['i']
        fn['nodes'].extend([
            {'id':'minus','op':'i32.const','value':-1},
            {'id':'alter','op':'local.set','name':'i','args':['minus']},
            {'id':'body','op':'flow.sequence','args':['s','alter']},
            {'id':'loop','op':'flow.repeat','count':3,'counter':'i','args':['body']}])
        fn['entry']='loop'
        output, _ = execute(doc, [{'fn':'step'}])
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertEqual(json.loads(output.stdout)['state']['counter'], [24])

    def test_state_reset_runtime_and_wasm_equivalence_on_game(self):
        baseline_doc = game_document()
        reset_doc = migrate_module(game_document())
        mutable_cells = [cell['id'] for cell in reset_doc['cells'] if cell['mutable']]
        init_fn = next(fn for fn in reset_doc['functions'] if fn['id'] == 'game.init')
        self.assertEqual(len(init_fn['nodes']), 373)
        init_fn['nodes'] = [{'id': 'n0000', 'op': 'state.reset', 'cells': mutable_cells}]
        init_fn['entry'] = 'n0000'

        baseline_wasm = compile_module(analyze_module(baseline_doc))
        reset_wasm = compile_module(analyze_module(reset_doc))
        self.assertEqual(len(baseline_wasm) - len(reset_wasm), 3097)

        calls = [
            {'set': {'player.x': [99999], 'enemy.alive': [0, 0, 0, 0, 0, 0], 'game.gems': [5]}, 'fn': 'game.init'},
            {'set': {'input.start': [1]}, 'fn': 'game.tick'},
            {'set': {'input.start': [0], 'input.right': [1], 'input.jump': [1]}, 'fn': 'game.tick'},
        ]
        for _ in range(25):
            calls.append({'fn': 'game.tick'})
        calls.append({'fn': 'game.init'})
        calls.append({'set': {'input.start': [1]}, 'fn': 'game.tick'})

        vm_base = Machine(baseline_doc)
        vm_reset = Machine(reset_doc)
        for call in calls:
            for key, values in call.get('set', {}).items():
                vm_base.state[key] = list(values)
                vm_reset.state[key] = list(values)
            vm_base.call(call['fn'])
            vm_reset.call(call['fn'])
        self.assertEqual(vm_reset.state, vm_base.state)

        wasm_result, _ = execute(reset_doc, calls)
        self.assertEqual(wasm_result.returncode, 0, wasm_result.stderr)
        self.assertEqual(json.loads(wasm_result.stdout)['state'], vm_base.state)


if __name__ == '__main__': unittest.main()
