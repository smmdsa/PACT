import fs from 'node:fs';
import {createHash} from 'node:crypto';
try {
  const binary=fs.readFileSync(process.argv[2]);
  const doc=JSON.parse(fs.readFileSync(process.argv[3]));
  if(!WebAssembly.validate(binary))throw new Error('Invalid generated WebAssembly');
  const kinds={assertion:'ASSERTION_FAILED',bounds:'STATE_BOUNDS',arithmetic:'ARITHMETIC_TRAP'};
  if(doc.trap_map && doc.trap_map.wasm_sha256!==createHash('sha256').update(binary).digest('hex'))
    throw new Error('Trap map does not match generated WebAssembly');
  const evidence=[];
  for(const test of doc.tests){
    const {instance}=await WebAssembly.instantiate(binary,{});
    const memory=new DataView(instance.exports.memory.buffer);
    for(const [id,values] of Object.entries(test.set)){
      const cell=doc.layout[id];values.forEach((value,i)=>memory.setInt32(cell.offset+i*4,value,true));
    }
    let result, location;
    try {
      result=instance.exports[test.function](...(test.args||[]));
    } catch(error) {
      if(!test.trap || !(error instanceof WebAssembly.RuntimeError))throw error;
      const frame=/wasm-function\[(\d+)\]:(0x[0-9a-f]+)/i.exec(error.stack??'');
      if(!frame)throw new Error(`${test.id}: Expected trap has no exact Wasm coordinates`);
      location={function_index:Number(frame[1]),offset:Number(frame[2])};
      const site=doc.trap_map?.positions.find(p=>p.function_index===location.function_index && p.offset===location.offset);
      if(!site || site.function!==test.trap.function || site.node!==test.trap.node || kinds[site.kind]!==test.trap.code)
        throw new Error(`${test.id}: Wasm trap site differs from expected trap`);
    }
    if(test.trap && !location)throw new Error(`${test.id}: Expected a Wasm trap, call returned normally`);
    if('result' in test && result!==test.result)throw new Error(`${test.id}: result ${result}, expected ${test.result}`);
    for(const [id,values] of Object.entries(test.expect)){
      const cell=doc.layout[id];
      values.forEach((value,i)=>{const actual=memory.getInt32(cell.offset+i*4,true);if(actual!==value)throw new Error(`${test.id}: ${id}[${i}] = ${actual}, expected ${value}`)});
    }
    evidence.push({id:test.id,status:'tested',...(doc.reference_tested?{reference:'tested',wasm:'tested'}:{}),
      ...(test.trap?{trap:test.trap,wasm_location:location}:{})});
  }
  console.log(JSON.stringify({status:'passed',evidence}));
} catch(error){console.error(JSON.stringify({status:'rejected',code:'TEST_FAILED',message:error.message}));process.exitCode=1;}
