import re

from .diagnostics import PactError

GRAPH_FORMAT = "pact.graph/0.0.1"
PLAN_FORMAT = "pact.plan/0.0.1"
MAX_SOURCE_BYTES = 1024 * 1024
MAX_NODES = 256
MAX_ARGUMENTS = 64
MAX_TEXT_BYTES = 16384
OPERATIONS = {"utf8.literal", "utf8.concat", "stdout.emit", "effect.sequence"}
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_.:\-]{0,63}", re.ASCII)


def require(condition, code, message, node=None):
    if not condition:
        raise PactError(code, message, node)


def closed_record(value, fields, node=None):
    require(isinstance(value, dict) and set(value) == fields,
            "SCHEMA_INVALID", f"Expected exactly these fields: {sorted(fields)}", node)


def identifier(value, node=None):
    require(isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None,
            "ID_INVALID", "Expected a 1–64 character ASCII identifier.", node)


def utf8(value, node=None):
    require(isinstance(value, str), "SCHEMA_INVALID", "Expected Utf8 text.", node)
    try:
        data = value.encode("utf-8")
    except UnicodeEncodeError:
        raise PactError("UTF8_INVALID", "Text contains an invalid Unicode surrogate.", node) from None
    require(len(data) <= MAX_TEXT_BYTES, "TEXT_LIMIT",
            f"Text exceeds {MAX_TEXT_BYTES} UTF-8 bytes.", node)
    return data


def validate(document):
    closed_record(document, {"format", "responsibility", "entry", "effects", "nodes", "contracts"})
    require(document["format"] == GRAPH_FORMAT, "FORMAT_UNSUPPORTED", "Unsupported graph format.")
    identifier(document["responsibility"])
    identifier(document["entry"])
    effects = document["effects"]
    require(isinstance(effects, list), "SCHEMA_INVALID", "Effects must be a list.")
    require(all(effect == "stdout" for effect in effects),
            "CAPABILITY_UNKNOWN", "Only stdout exists in this kernel.")
    require(len(effects) <= 1, "SCHEMA_INVALID", "Effects cannot be duplicated.")
    nodes = document["nodes"]
    require(isinstance(nodes, list) and 1 <= len(nodes) <= MAX_NODES,
            "NODE_LIMIT", f"Expected 1–{MAX_NODES} nodes.")
    indexed = {}
    for node in nodes:
        require(isinstance(node, dict), "SCHEMA_INVALID", "A node must be a record.")
        name = node.get("id")
        identifier(name)
        operation = node.get("op")
        require(isinstance(operation, str) and operation in OPERATIONS,
                "OP_UNKNOWN", "Unsupported operation.", name)
        fields = {"id", "op", "value" if operation == "utf8.literal" else "args"}
        closed_record(node, fields, name)
        require(name not in indexed, "ID_DUPLICATE", "Node ID is duplicated.", name)
        if operation == "utf8.literal":
            utf8(node["value"], name)
        else:
            args = node["args"]
            require(isinstance(args, list) and 1 <= len(args) <= MAX_ARGUMENTS,
                    "ARGUMENT_LIMIT", f"Expected 1–{MAX_ARGUMENTS} references.", name)
            for ref in args:
                identifier(ref, name)
            if operation == "stdout.emit":
                require(len(args) == 1, "ARITY_INVALID", "stdout.emit needs one argument.", name)
        indexed[name] = node
    require(document["entry"] in indexed, "REFERENCE_MISSING", "Entry node does not exist.")
    for node in nodes:
        for ref in node.get("args", []):
            require(ref in indexed, "REFERENCE_MISSING", f"Reference {ref} does not exist.", node["id"])
    contracts = document["contracts"]
    require(isinstance(contracts, list), "SCHEMA_INVALID", "Contracts must be a list.")
    require(1 <= len(contracts) <= MAX_NODES, "CONTRACT_REQUIRED", "At least one bounded contract is required.")
    contract_ids = set()
    for contract in contracts:
        closed_record(contract, {"id", "op", "value"})
        identifier(contract["id"])
        require(contract["id"] not in contract_ids, "ID_DUPLICATE", "Contract ID is duplicated.", contract["id"])
        contract_ids.add(contract["id"])
        require(contract["op"] == "stdout.exact", "CONTRACT_UNSUPPORTED", "Only stdout.exact is supported.")
        utf8(contract["value"], contract["id"])
    return indexed
