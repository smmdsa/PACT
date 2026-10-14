import { createHash } from "node:crypto";

export const MAX_OUTPUT = 16384;
const MAX_NODES = 256;
const ID = /^[A-Za-z][A-Za-z0-9_.:\-]{0,63}$/;
const HASH = /^[a-f0-9]{64}$/;
const OP = { end: 0x0b, call: 0x10, i32Const: 0x41 };
const SECTION = { type: 1, import: 2, function: 3, memory: 5, export: 7, code: 10, data: 11 };

export function reject(code, message) {
  throw Object.assign(new Error(message), { code });
}

function requireValue(condition, message) {
  if (!condition) reject("MANIFEST_INVALID", message);
}

function record(value, fields) {
  requireValue(value !== null && typeof value === "object" && !Array.isArray(value), "Expected a record.");
  const keys = Object.keys(value).sort();
  requireValue(JSON.stringify(keys) === JSON.stringify([...fields].sort()), "Unexpected record fields.");
}

export function textBytes(value) {
  requireValue(typeof value === "string", "Expected Utf8 text.");
  for (let index = 0; index < value.length; index++) {
    const unit = value.charCodeAt(index);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      requireValue(index + 1 < value.length, "Unpaired Unicode surrogate.");
      const next = value.charCodeAt(++index);
      requireValue(next >= 0xdc00 && next <= 0xdfff, "Unpaired Unicode surrogate.");
    } else {
      requireValue(unit < 0xdc00 || unit > 0xdfff, "Unpaired Unicode surrogate.");
    }
  }
  const bytes = Buffer.from(value, "utf8");
  requireValue(bytes.length <= MAX_OUTPUT, "Text exceeds the kernel budget.");
  return bytes;
}

export function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function integer(value, signed = false) {
  const bytes = [];
  do {
    const byte = value & 0x7f;
    value = Math.floor(value / 128);
    const done = signed ? (value === 0 && !(byte & 0x40)) : value === 0;
    bytes.push(byte | (done ? 0 : 0x80));
    if (done) break;
  } while (true);
  return Buffer.from(bytes);
}

function vector(items) {
  return Buffer.concat([integer(items.length), ...items]);
}

function encodedName(value) {
  const bytes = Buffer.from(value);
  return Buffer.concat([integer(bytes.length), bytes]);
}

function section(id, payload) {
  return Buffer.concat([Buffer.from([id]), integer(payload.length), payload]);
}

function constant(value) {
  return Buffer.concat([Buffer.from([OP.i32Const]), integer(value, true)]);
}

export function permittedBytecode(emissions) {
  const payloads = emissions.map(textBytes);
  const type = vector([Buffer.from([0x60, 2, 0x7f, 0x7f, 0]), Buffer.from([0x60, 0, 0])]);
  const imports = vector([Buffer.concat([encodedName("pact"), encodedName("emit_utf8"), Buffer.from([0, 0])])]);
  const exports = vector([
    Buffer.concat([encodedName("memory"), Buffer.from([2, 0])]),
    Buffer.concat([encodedName("main"), Buffer.from([0, 1])]),
  ]);
  const instructions = [], segments = [];
  let offset = 0;
  for (const payload of payloads) {
    instructions.push(constant(offset), constant(payload.length), Buffer.from([OP.call, 0]));
    segments.push(Buffer.concat([Buffer.from([0]), constant(offset), Buffer.from([OP.end]), integer(payload.length), payload]));
    offset += payload.length;
  }
  const body = Buffer.concat([Buffer.from([0]), ...instructions, Buffer.from([OP.end])]);
  return Buffer.concat([
    Buffer.from([0, 0x61, 0x73, 0x6d, 1, 0, 0, 0]),
    section(SECTION.type, type), section(SECTION.import, imports),
    section(SECTION.function, vector([Buffer.from([1])])),
    section(SECTION.memory, vector([Buffer.from([1, 1, 1])])),
    section(SECTION.export, exports), section(SECTION.code, vector([Buffer.concat([integer(body.length), body])])),
    section(SECTION.data, vector(segments)),
  ]);
}

export function validateArtifact(manifest, binary, outputBudget) {
  record(manifest, ["format", "plan", "wasm_sha256"]);
  requireValue(manifest.format === "pact.artifact/0.0.1", "Unsupported artifact format.");
  requireValue(typeof manifest.wasm_sha256 === "string" && HASH.test(manifest.wasm_sha256), "Invalid artifact hash.");
  const plan = manifest.plan;
  record(plan, ["format", "responsibility", "source_sha256", "capabilities", "emissions", "types", "evidence"]);
  requireValue(plan.format === "pact.plan/0.0.1", "Unsupported plan format.");
  requireValue(typeof plan.responsibility === "string" && ID.test(plan.responsibility), "Invalid responsibility ID.");
  requireValue(typeof plan.source_sha256 === "string" && HASH.test(plan.source_sha256), "Invalid source hash.");
  requireValue(JSON.stringify(plan.capabilities) === '["stdout"]', "Unsupported capability declaration.");
  requireValue(Array.isArray(plan.emissions) && plan.emissions.length >= 1 && plan.emissions.length <= MAX_NODES,
    "Invalid emission count.");
  const total = plan.emissions.map(textBytes).reduce((sum, bytes) => sum + bytes.length, 0);
  if (total > MAX_OUTPUT || total > outputBudget) reject("OUTPUT_LIMIT", "Output exceeds the host budget.");
  requireValue(plan.types !== null && typeof plan.types === "object" && !Array.isArray(plan.types), "Invalid type table.");
  const entries = Object.entries(plan.types);
  requireValue(entries.length >= 1 && entries.length <= MAX_NODES, "Invalid type table size.");
  for (const [id, type] of entries) requireValue(ID.test(id) && ["Utf8", "Unit"].includes(type), "Invalid inferred type.");
  requireValue(Array.isArray(plan.evidence) && plan.evidence.length >= 1 && plan.evidence.length <= MAX_NODES,
    "Contract evidence is required.");
  const ids = new Set();
  for (const item of plan.evidence) {
    record(item, ["id", "op", "status"]);
    requireValue(typeof item.id === "string" && ID.test(item.id) && !ids.has(item.id), "Invalid evidence ID.");
    ids.add(item.id);
    requireValue(item.op === "stdout.exact" && item.status === "evaluated", "Unsupported evidence.");
  }
  if (sha256(binary) !== manifest.wasm_sha256) reject("ARTIFACT_HASH", "Bytecode differs from the recorded hash.");
  if (!binary.equals(permittedBytecode(plan.emissions))) reject("ARTIFACT_PROFILE", "Bytecode is outside the permitted profile.");
  return plan;
}
