import hashlib
import json
from pathlib import Path

from .diagnostics import PactError
from .schema import MAX_SOURCE_BYTES, MAX_TEXT_BYTES, PLAN_FORMAT, require, utf8, validate


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON_DUPLICATE_KEY", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_document(path, migrate_legacy=False, validate_source=False):
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
        require(len(data) <= MAX_SOURCE_BYTES, "SOURCE_LIMIT", "Source exceeds 1 MiB.")
        text = data.decode("utf-8")
        if Path(path).suffix == '.pact' or text.lstrip().startswith('pact '):
            from .compact import loads
            return loads(text, migrate_legacy=migrate_legacy)
        document = json.loads(text, object_pairs_hook=_unique_pairs)
        if validate_source:
            from .source_locations import validate_json_source
            validate_json_source(text, document)
        from .module import FORMATS, migrate_module
        if migrate_legacy and isinstance(document, dict) and document.get('format') == FORMATS[0]:
            return migrate_module(document)
        return document
    except PactError:
        raise
    except (OSError, ValueError, RecursionError) as error:
        raise PactError("SOURCE_INVALID", str(error)) from None


def canonical_source(document):
    normalized = dict(document)
    normalized["nodes"] = sorted(document["nodes"], key=lambda node: node["id"])
    normalized["contracts"] = sorted(document["contracts"], key=lambda contract: contract["id"])
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def analyze(document):
    nodes = validate(document)
    types, values, visiting = {}, {}, set()

    def infer(name):
        require(name not in visiting, "GRAPH_CYCLE", "Graph contains a cycle.", name)
        if name in types:
            return types[name]
        visiting.add(name)
        node = nodes[name]
        op = node["op"]
        args = node.get("args", [])
        argument_types = [infer(ref) for ref in args]
        if op == "utf8.literal":
            result_type, value = "Utf8", node["value"]
        elif op == "utf8.concat":
            require(all(kind == "Utf8" for kind in argument_types),
                    "TYPE_MISMATCH", "utf8.concat requires Utf8 arguments.", name)
            size = sum(len(values[ref].encode("utf-8")) for ref in args)
            require(size <= MAX_TEXT_BYTES, "TEXT_LIMIT", "Concatenation exceeds the text budget.", name)
            result_type, value = "Utf8", "".join(values[ref] for ref in args)
        else:
            expected = "Utf8" if op == "stdout.emit" else "Unit"
            require(all(kind == expected for kind in argument_types),
                    "TYPE_MISMATCH", f"{op} requires {expected} arguments.", name)
            result_type, value = "Unit", None
        visiting.remove(name)
        types[name], values[name] = result_type, value
        return result_type

    require(infer(document["entry"]) == "Unit", "ENTRY_TYPE", "Entry must return Unit.", document["entry"])
    dead = sorted(set(nodes) - set(types))
    require(not dead, "NODE_UNREACHABLE", f"Nodes are unreachable: {dead}")
    inferred_effects = ["stdout"] if any(node["op"] == "stdout.emit" for node in nodes.values()) else []
    require(document["effects"] == inferred_effects, "EFFECT_MISMATCH", "Declared and inferred effects differ.")
    emissions, executed = [], set()
    total = 0

    def execute(name):
        nonlocal total
        require(name not in executed, "EFFECT_SHARED", "An effect node cannot execute twice.", name)
        executed.add(name)
        node = nodes[name]
        if node["op"] == "stdout.emit":
            text = values[node["args"][0]]
            total += len(utf8(text, name))
            require(total <= MAX_TEXT_BYTES, "OUTPUT_LIMIT", "Total output exceeds the budget.", name)
            emissions.append(text)
        else:
            for ref in node["args"]:
                execute(ref)

    execute(document["entry"])
    output = "".join(emissions)
    evidence = []
    for contract in sorted(document["contracts"], key=lambda item: item["id"]):
        require(contract["value"] == output, "CONTRACT_FAILED", "Computed stdout differs from the contract.", contract["id"])
        evidence.append({"id": contract["id"], "status": "evaluated", "op": "stdout.exact"})
    return {
        "format": PLAN_FORMAT,
        "responsibility": document["responsibility"],
        "source_sha256": hashlib.sha256(canonical_source(document)).hexdigest(),
        "capabilities": inferred_effects,
        "emissions": emissions,
        "types": dict(sorted(types.items())),
        "evidence": evidence,
    }
