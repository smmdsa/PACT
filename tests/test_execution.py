import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pact.graph import analyze
from pact.wasm import compile_plan
from tests.test_graph import ROOT, hello, text_program


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)

    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "pact", *map(str, args)],
                              cwd=ROOT, capture_output=True, timeout=10)

    def build(self, document):
        source, wasm = self.work / "input.json", self.work / "program.wasm"
        source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        result = self.cli("build", source, "-o", wasm)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return source, wasm, wasm.with_suffix(".manifest.json")

    def run_host(self, wasm, *args):
        return subprocess.run(["node", str(ROOT / "host/run.mjs"), str(wasm), *args],
                              capture_output=True, timeout=10)

    def reject(self, result, code):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(json.loads(result.stderr)["code"], code)

    def write_manifest(self, path, value):
        path.write_bytes((json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    def test_manifest_rewrite_preserves_compiler_bytes_and_host_acceptance(self):
        _, wasm, manifest = self.build(text_program("👽é\n"))
        original = manifest.read_bytes()
        self.write_manifest(manifest, json.loads(original))
        self.assertEqual(manifest.read_bytes(), original)
        result = self.run_host(wasm, "--allow", "stdout")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "👽é\n".encode("utf-8"))

    def test_compiler_emits_valid_webassembly(self):
        artifact = compile_plan(analyze(hello()))
        self.assertEqual(artifact[:8], b"\x00asm\x01\x00\x00\x00")
        path = self.work / "module.wasm"
        path.write_bytes(artifact)
        result = subprocess.run(["node", "--input-type=module", "-e",
                                 "import fs from 'node:fs'; console.log(WebAssembly.validate(fs.readFileSync(process.argv[1])))",
                                 str(path)], capture_output=True, timeout=10)
        self.assertEqual(result.stdout.strip(), b"true")

    def test_hello_executes_as_real_wasm(self):
        _, wasm, _ = self.build(hello())
        result = self.run_host(wasm, "--allow", "stdout")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"hola mundo, from an alien language\n")
        self.assertEqual(result.stderr, b"")

    def test_interpreter_and_wasm_agree_on_unicode_and_empty_output(self):
        for text in ("", "hola 👽 — ñ\n", "x" * 200, "👽" * 4096):
            with self.subTest(text_length=len(text)):
                source, wasm, _ = self.build(text_program(text))
                reference = self.cli("interpret", source, "--allow", "stdout")
                actual = self.run_host(wasm, "--allow", "stdout")
                self.assertEqual(reference.returncode, 0, reference.stderr)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                self.assertEqual(actual.stdout, text.encode())
                self.assertEqual(actual.stdout, reference.stdout)

    def test_stdout_is_denied_by_default(self):
        source, wasm, _ = self.build(hello())
        self.reject(self.run_host(wasm), "CAPABILITY_DENIED")
        self.reject(self.cli("interpret", source), "CAPABILITY_DENIED")

    def test_unknown_grant_is_rejected(self):
        _, wasm, _ = self.build(hello())
        self.reject(self.run_host(wasm, "--allow", "network"), "CLI_INVALID")

    def test_output_budget_is_checked_before_any_output(self):
        _, wasm, _ = self.build(text_program("👽"))
        self.reject(self.run_host(wasm, "--allow", "stdout", "--max-output", "3"), "OUTPUT_LIMIT")
        allowed = self.run_host(wasm, "--allow", "stdout", "--max-output", "4")
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(allowed.stdout, "👽".encode())

    def test_bytecode_hash_tampering(self):
        _, wasm, _ = self.build(hello())
        wasm.write_bytes(wasm.read_bytes() + b"\x00\x01\x00")
        self.reject(self.run_host(wasm, "--allow", "stdout"), "ARTIFACT_HASH")

    def test_recomputed_hash_does_not_bypass_profile(self):
        _, wasm, manifest = self.build(hello())
        data = wasm.read_bytes() + b"\x00\x01\x00"
        wasm.write_bytes(data)
        record = json.loads(manifest.read_text())
        record["wasm_sha256"] = hashlib.sha256(data).hexdigest()
        self.write_manifest(manifest, record)
        self.reject(self.run_host(wasm, "--allow", "stdout"), "ARTIFACT_PROFILE")

    def test_valid_infinite_loop_module_is_rejected_before_execution(self):
        _, wasm, manifest = self.build(hello())
        looping = bytes.fromhex("0061736d0100000001040160000003020100070801046d61696e00000a0901070003400c000b0b")
        result = subprocess.run(["node", "--input-type=module", "-e",
                                 "console.log(WebAssembly.validate(Buffer.from(process.argv[1], 'hex')))", looping.hex()],
                                capture_output=True, timeout=10)
        self.assertEqual(result.stdout.strip(), b"true")
        wasm.write_bytes(looping)
        record = json.loads(manifest.read_text())
        record["wasm_sha256"] = hashlib.sha256(looping).hexdigest()
        self.write_manifest(manifest, record)
        self.reject(self.run_host(wasm, "--allow", "stdout"), "ARTIFACT_PROFILE")

    def test_manifest_output_tampering(self):
        _, wasm, manifest = self.build(hello())
        record = json.loads(manifest.read_text())
        record["plan"]["emissions"] = ["different output"]
        self.write_manifest(manifest, record)
        self.reject(self.run_host(wasm, "--allow", "stdout"), "ARTIFACT_PROFILE")

    def test_manifest_capability_escalation(self):
        _, wasm, manifest = self.build(hello())
        record = json.loads(manifest.read_text())
        record["plan"]["capabilities"] = ["network"]
        self.write_manifest(manifest, record)
        self.reject(self.run_host(wasm, "--allow", "stdout"), "MANIFEST_INVALID")

    def test_manifest_identifiers_and_hashes_cannot_end_with_newline(self):
        for field in ("responsibility", "source_sha256"):
            with self.subTest(field=field):
                _, wasm, manifest = self.build(hello())
                record = json.loads(manifest.read_text())
                record["plan"][field] += "\n"
                self.write_manifest(manifest, record)
                self.reject(self.run_host(wasm, "--allow", "stdout"), "MANIFEST_INVALID")

    def test_sequence_executes_in_order_with_nonzero_multibyte_offset(self):
        first, second = "👽" * 50, "\x00é\n"
        doc = text_program(first + second)
        doc["nodes"][0]["value"] = first
        doc["nodes"].extend([
            {"id": "v1", "op": "utf8.literal", "value": second},
            {"id": "e1", "op": "stdout.emit", "args": ["v1"]},
            {"id": "e2", "op": "effect.sequence", "args": ["e0", "e1"]}])
        doc["entry"] = "e2"
        source, wasm, _ = self.build(doc)
        actual = self.run_host(wasm, "--allow", "stdout")
        expected = self.cli("interpret", source, "--allow", "stdout")
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertEqual(actual.stdout, (first + second).encode())
        self.assertEqual(actual.stdout, expected.stdout)

    def test_missing_manifest(self):
        _, wasm, manifest = self.build(hello())
        manifest.unlink()
        self.reject(self.run_host(wasm, "--allow", "stdout"), "ARTIFACT_READ")

    def test_failed_contract_does_not_produce_artifact(self):
        doc = hello()
        doc["contracts"][0]["value"] = "not the intended output"
        source, target = self.work / "bad.json", self.work / "bad.wasm"
        source.write_text(json.dumps(doc))
        self.reject(self.cli("build", source, "-o", target), "CONTRACT_FAILED")
        self.assertFalse(target.exists())
        self.assertFalse(target.with_suffix(".manifest.json").exists())

    def test_reordered_graph_produces_identical_bytecode(self):
        doc = hello()
        _, wasm, manifest = self.build(doc)
        binary, record = wasm.read_bytes(), manifest.read_bytes()
        doc["nodes"].reverse()
        _, wasm, manifest = self.build(doc)
        self.assertEqual(wasm.read_bytes(), binary)
        self.assertEqual(manifest.read_bytes(), record)


if __name__ == "__main__":
    unittest.main()
