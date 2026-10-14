from enum import IntEnum

from .schema import MAX_TEXT_BYTES, PLAN_FORMAT, require, utf8


class Section(IntEnum):
    TYPE = 1
    IMPORT = 2
    FUNCTION = 3
    MEMORY = 5
    EXPORT = 7
    CODE = 10
    DATA = 11


class Instruction(IntEnum):
    END = 0x0B
    CALL = 0x10
    I32_CONST = 0x41


I32 = 0x7F
FUNCTION_TYPE = 0x60
FUNCTION_EXPORT = 0
MEMORY_EXPORT = 2
MEMORY_PAGE_BYTES = 65536
WASM_HEADER = b"\x00asm\x01\x00\x00\x00"


def unsigned(value):
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        result.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(result)


def signed(value):
    result = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        done = (value == 0 and not byte & 0x40) or (value == -1 and byte & 0x40)
        result.append(byte | (0 if done else 0x80))
        if done:
            return bytes(result)


def vector(items):
    return unsigned(len(items)) + b"".join(items)


def name(value):
    data = value.encode("utf-8")
    return unsigned(len(data)) + data


def section(kind, payload):
    return bytes([kind]) + unsigned(len(payload)) + payload


def compile_plan(plan):
    require(isinstance(plan, dict) and plan.get("format") == PLAN_FORMAT,
            "PLAN_INVALID", "Expected a PACT execution plan.")
    emissions = plan.get("emissions")
    require(isinstance(emissions, list) and 1 <= len(emissions) <= 256,
            "PLAN_INVALID", "Expected bounded emissions.")
    payloads = [utf8(text) for text in emissions]
    require(sum(map(len, payloads)) <= MAX_TEXT_BYTES, "OUTPUT_LIMIT", "Output exceeds the budget.")
    types = vector([
        bytes([FUNCTION_TYPE]) + vector([bytes([I32]), bytes([I32])]) + vector([]),
        bytes([FUNCTION_TYPE]) + vector([]) + vector([]),
    ])
    imports = vector([name("pact") + name("emit_utf8") + bytes([FUNCTION_EXPORT]) + unsigned(0)])
    functions = vector([unsigned(1)])
    memory = vector([b"\x01" + unsigned(1) + unsigned(1)])
    exports = vector([
        name("memory") + bytes([MEMORY_EXPORT]) + unsigned(0),
        name("main") + bytes([FUNCTION_EXPORT]) + unsigned(1),
    ])
    instructions = bytearray()
    segments, offset = [], 0
    for payload in payloads:
        instructions.extend(bytes([Instruction.I32_CONST]) + signed(offset))
        instructions.extend(bytes([Instruction.I32_CONST]) + signed(len(payload)))
        instructions.extend(bytes([Instruction.CALL]) + unsigned(0))
        segments.append(b"\x00" + bytes([Instruction.I32_CONST]) + signed(offset)
                        + bytes([Instruction.END]) + unsigned(len(payload)) + payload)
        offset += len(payload)
    body = unsigned(0) + bytes(instructions) + bytes([Instruction.END])
    code = vector([unsigned(len(body)) + body])
    return WASM_HEADER + b"".join([
        section(Section.TYPE, types), section(Section.IMPORT, imports),
        section(Section.FUNCTION, functions), section(Section.MEMORY, memory),
        section(Section.EXPORT, exports), section(Section.CODE, code),
        section(Section.DATA, vector(segments)),
    ])
