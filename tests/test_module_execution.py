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


if __name__ == '__main__': unittest.main()
