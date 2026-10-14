import fs from 'node:fs';

const layout = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')).layout.counter;
const {instance} = await WebAssembly.instantiate(fs.readFileSync(process.argv[2]), {});
const memory = new DataView(instance.exports.memory.buffer);
for (const line of fs.readFileSync(0, 'utf8').trim().split('\n')) {
    const args = line.split(' ').map(Number);
    let status = 'ok';
    try { instance.exports.advance(...args); }
    catch (error) {
        if (!(error instanceof WebAssembly.RuntimeError)) throw error;
        status = 'bounds';
    }
    console.log(status, ...Array.from({length:layout.count}, (_,i) => memory.getInt32(layout.offset + i*4, true)));
}
