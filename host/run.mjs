import fs from "node:fs";
import path from "node:path";
import { MAX_OUTPUT, reject, validateArtifact } from "./profile.mjs";

const MAX_ARTIFACT_BYTES = 1024 * 1024;

function options(argv) {
  if (!argv.length || !argv[0].endsWith(".wasm")) reject("CLI_INVALID", "Expected an artifact.wasm path.");
  const config = { wasm: argv[0], allow: new Set(), budget: MAX_OUTPUT };
  for (let index = 1; index < argv.length; index += 2) {
    const key = argv[index], value = argv[index + 1];
    if (key === "--allow" && value === "stdout") config.allow.add(value);
    else if (key === "--max-output" && typeof value === "string" && /^(0|[1-9][0-9]*)$/.test(value)
             && Number(value) <= MAX_OUTPUT) config.budget = Number(value);
    else reject("CLI_INVALID", "Expected --allow stdout or --max-output 0..16384.");
  }
  return config;
}

function boundedRead(file) {
  let descriptor;
  try {
    descriptor = fs.openSync(file, "r");
    const buffer = Buffer.alloc(MAX_ARTIFACT_BYTES + 1);
    let size = 0;
    while (size < buffer.length) {
      const count = fs.readSync(descriptor, buffer, size, buffer.length - size, null);
      if (!count) break;
      size += count;
    }
    if (size > MAX_ARTIFACT_BYTES) reject("ARTIFACT_LIMIT", "Artifact input exceeds 1 MiB.");
    return buffer.subarray(0, size);
  } catch (error) {
    if (error.code === "ARTIFACT_LIMIT") throw error;
    reject("ARTIFACT_READ", "Cannot read artifact input.");
  } finally {
    if (descriptor !== undefined) fs.closeSync(descriptor);
  }
}

function loadManifest(file) {
  const bytes = boundedRead(file);
  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    const value = JSON.parse(text);
    if (JSON.stringify(value, null, 2) + "\n" !== text) reject("MANIFEST_INVALID", "Manifest is not in compiler JSON form.");
    return value;
  } catch {
    reject("MANIFEST_INVALID", "Manifest must be unambiguous compiler JSON with valid UTF-8.");
  }
}

async function main() {
  const config = options(process.argv.slice(2));
  const manifestPath = path.join(path.dirname(config.wasm), path.basename(config.wasm, ".wasm") + ".manifest.json");
  const binary = boundedRead(config.wasm);
  const plan = validateArtifact(loadManifest(manifestPath), binary, config.budget);
  for (const capability of plan.capabilities) {
    if (!config.allow.has(capability)) reject("CAPABILITY_DENIED", "Host has not granted stdout.");
  }
  let instance, emitted = 0;
  const imports = { pact: { emit_utf8(pointer, length) {
    const memory = new Uint8Array(instance.exports.memory.buffer);
    pointer >>>= 0;
    length >>>= 0;
    if (pointer + length > memory.length) reject("MEMORY_BOUNDS", "Emission is outside guest memory.");
    emitted += length;
    if (emitted > config.budget) reject("OUTPUT_LIMIT", "Runtime output exceeds the budget.");
    const bytes = memory.subarray(pointer, pointer + length);
    new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    process.stdout.write(bytes);
  } } };
  ({ instance } = await WebAssembly.instantiate(binary, imports));
  instance.exports.main();
}

main().catch(error => {
  process.stderr.write(JSON.stringify({ status: "rejected", code: error.code || "HOST_FAILED", message: error.message }) + "\n");
  process.exitCode = 1;
});
