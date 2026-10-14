import fs from 'node:fs';
try {
  const binary=fs.readFileSync(process.argv[2]);
  const doc=JSON.parse(fs.readFileSync(process.argv[3]));
  if(!WebAssembly.validate(binary))throw new Error('Invalid generated WebAssembly');
  const evidence=[];
  for(const test of doc.tests){
    const {instance}=await WebAssembly.instantiate(binary,{});
    const memory=new DataView(instance.exports.memory.buffer);
    for(const [id,values] of Object.entries(test.set)){
      const cell=doc.layout[id];values.forEach((value,i)=>memory.setInt32(cell.offset+i*4,value,true));
    }
    const result=instance.exports[test.function](...(test.args||[]));
    if('result' in test && result!==test.result)throw new Error(`${test.id}: result ${result}, expected ${test.result}`);
    for(const [id,values] of Object.entries(test.expect)){
      const cell=doc.layout[id];
      values.forEach((value,i)=>{const actual=memory.getInt32(cell.offset+i*4,true);if(actual!==value)throw new Error(`${test.id}: ${id}[${i}] = ${actual}, expected ${value}`)});
    }
    evidence.push({id:test.id,status:'tested'});
  }
  console.log(JSON.stringify({status:'passed',evidence}));
} catch(error){console.error(JSON.stringify({status:'rejected',code:'TEST_FAILED',message:error.message}));process.exitCode=1;}
