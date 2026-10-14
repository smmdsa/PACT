// Runs only compiler-produced numeric modules requested by pact.replay.
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
try {
  const binary = fs.readFileSync(process.argv[2]);
  const request = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const {instance} = await WebAssembly.instantiate(binary, {});
  const memory = new DataView(instance.exports.memory.buffer);
  const state = () => Object.fromEntries(Object.keys(request.layout).sort().map(id => {
    const cell = request.layout[id];
    return [id, Array.from({length: cell.count}, (_, i) => memory.getInt32(cell.offset + i * 4, true))];
  }));
  const initial = state();
  const events = [];
  let status = 'completed';
  for (const [index, call] of request.calls.entries()) {
    const event = {index, function: call.function, args: call.args};
    try {
      event.result = instance.exports[call.function](...call.args) ?? null;
    } catch (error) {
      if (!(error instanceof WebAssembly.RuntimeError)) throw error;
      event.diagnostic = {status: 'rejected', code: 'WASM_TRAP', message: 'Compiled WebAssembly trapped.'};
      status = 'trapped';
    }
    event.state_sha256 = hash(JSON.stringify(state()));
    events.push(event);
    if (status !== 'completed') break;
  }
  const final = state();
  process.stdout.write(JSON.stringify({format: 'pact.replay-report/0.1.0', engine: 'wasm', status,
    semantic_revision_sha256: request.revision, initial_state_sha256: hash(JSON.stringify(initial)),
    events, final_state: final, final_state_sha256: hash(JSON.stringify(final)),
    requested_calls: request.calls.length, wasm_sha256: hash(binary),
    node_version: process.version, v8_version: process.versions.v8}) + '\n');
} catch (error) {
  process.stderr.write(JSON.stringify({status: 'rejected', code: 'REPLAY_RUNTIME', message: error.message}) + '\n');
  process.exitCode = 1;
}
