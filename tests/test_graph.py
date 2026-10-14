import copy
import json
import tempfile
import unittest
from pathlib import Path

from pact.diagnostics import PactError
from pact.graph import analyze, load_document

ROOT = Path(__file__).resolve().parents[1]


def hello():
    return json.loads((ROOT / "examples/hello.pact.json").read_text())


def text_program(text):
    doc = hello()
    doc["nodes"] = [{"id": "v0", "op": "utf8.literal", "value": text},
                    {"id": "e0", "op": "stdout.emit", "args": ["v0"]}]
    doc["contracts"][0]["value"] = text
    return doc


class GraphTests(unittest.TestCase):
    def reject(self, doc, code):
        with self.assertRaises(PactError) as caught:
            analyze(doc)
        self.assertEqual(caught.exception.diagnostic["code"], code)

    def test_hello_has_exact_output_and_evaluated_contract(self):
        result = analyze(hello())
        self.assertIsInstance(result, dict)
        self.assertEqual(result["emissions"], ["hola mundo, from an alien language\n"])
        self.assertEqual(result["capabilities"], ["stdout"])
        self.assertEqual(result["types"], {"e0": "Unit", "v0": "Utf8", "v1": "Utf8", "v2": "Utf8"})
        self.assertEqual(result["evidence"], [{"id": "c0", "status": "evaluated", "op": "stdout.exact"}])

    def test_declaration_order_does_not_change_plan(self):
        doc = hello()
        other = copy.deepcopy(doc)
        other["nodes"].reverse()
        self.assertIsInstance(analyze(doc), dict)
        self.assertEqual(analyze(doc), analyze(other))

    def test_unresolved_reference(self):
        doc = hello()
        doc["nodes"][-1]["args"] = ["missing"]
        self.reject(doc, "REFERENCE_MISSING")

    def test_cycle(self):
        doc = hello()
        doc["nodes"][2]["args"] = ["v2"]
        self.reject(doc, "GRAPH_CYCLE")

    def test_duplicate_id(self):
        doc = hello()
        doc["nodes"].append(copy.deepcopy(doc["nodes"][0]))
        self.reject(doc, "ID_DUPLICATE")

    def test_dead_node_is_rejected(self):
        doc = hello()
        doc["nodes"].append({"id": "dead", "op": "utf8.literal", "value": "unused"})
        self.reject(doc, "NODE_UNREACHABLE")

    def test_undeclared_effect(self):
        doc = hello()
        doc["effects"] = []
        self.reject(doc, "EFFECT_MISMATCH")

    def test_unknown_capability(self):
        doc = hello()
        doc["effects"] = ["network"]
        self.reject(doc, "CAPABILITY_UNKNOWN")

    def test_type_mismatch(self):
        doc = hello()
        doc["nodes"][2]["args"] = ["e0"]
        doc["nodes"][-1]["args"] = ["v0"]
        doc["entry"] = "v2"
        self.reject(doc, "TYPE_MISMATCH")

    def test_unknown_field_is_not_silently_ignored(self):
        doc = hello()
        doc["nodes"][0]["values"] = "typo"
        self.reject(doc, "SCHEMA_INVALID")

    def test_unknown_operation(self):
        doc = hello()
        doc["nodes"][0]["op"] = "filesystem.read"
        self.reject(doc, "OP_UNKNOWN")

    def test_malformed_node(self):
        doc = hello()
        doc["nodes"][0] = None
        self.reject(doc, "SCHEMA_INVALID")

    def test_contract_mismatch(self):
        doc = hello()
        doc["contracts"][0]["value"] = "different intent"
        self.reject(doc, "CONTRACT_FAILED")

    def test_contract_required(self):
        doc = hello()
        doc["contracts"] = []
        self.reject(doc, "CONTRACT_REQUIRED")

    def test_unicode_and_empty_text(self):
        for text in ("", "Hola 👽 — ñ\n"):
            with self.subTest(text=text):
                result = analyze(text_program(text))
                self.assertIsInstance(result, dict)
                self.assertEqual(result["emissions"], [text])

    def test_limit_is_measured_in_utf8_bytes(self):
        self.reject(text_program("👽" * 4097), "TEXT_LIMIT")

    def test_surrogate_is_rejected(self):
        self.reject(text_program("\ud800"), "UTF8_INVALID")

    def test_shared_pure_node_is_allowed(self):
        doc = text_program("aa")
        doc["nodes"][0]["value"] = "a"
        doc["nodes"].insert(1, {"id": "v1", "op": "utf8.concat", "args": ["v0", "v0"]})
        doc["nodes"][-1]["args"] = ["v1"]
        result = analyze(doc)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["emissions"], ["aa"])

    def test_shared_effect_is_rejected(self):
        doc = text_program("hellohello")
        doc["nodes"][0]["value"] = "hello"
        doc["nodes"].append({"id": "e1", "op": "effect.sequence", "args": ["e0", "e0"]})
        doc["entry"] = "e1"
        self.reject(doc, "EFFECT_SHARED")

    def test_sequence_order_is_explicit(self):
        doc = text_program("ba")
        doc["nodes"][0]["value"] = "a"
        doc["nodes"].extend([
            {"id": "v1", "op": "utf8.literal", "value": "b"},
            {"id": "e1", "op": "stdout.emit", "args": ["v1"]},
            {"id": "e2", "op": "effect.sequence", "args": ["e1", "e0"]}])
        doc["entry"] = "e2"
        result = analyze(doc)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["emissions"], ["b", "a"])

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"entry":"e0","entry":"e1"}')
            with self.assertRaises(PactError) as caught:
                load_document(path)
            self.assertEqual(caught.exception.diagnostic["code"], "JSON_DUPLICATE_KEY")

    def test_source_limit_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large.json"
            path.write_bytes(b" " * (1024 * 1024 + 1))
            with self.assertRaises(PactError) as caught:
                load_document(path)
            self.assertEqual(caught.exception.diagnostic["code"], "SOURCE_LIMIT")


if __name__ == "__main__":
    unittest.main()
