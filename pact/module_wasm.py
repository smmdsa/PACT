import hashlib

from .module import BINARY
from .revision import revision
from .wasm import WASM_HEADER, section, vector, unsigned, signed, name

MAX_TRAP_POSITIONS = 16384


def compile_module(plan):
    return _compile(plan, False)[0]


def compile_module_with_traps(plan):
    return _compile(plan, True)


def _compile(plan, collect):
    doc = plan['document']
    initial_cells = {cell['id']: cell['values'] for cell in doc['cells']}
    functions = sorted(doc['functions'], key=lambda fn: fn['id'])
    fn_index = {fn['id']: i for i, fn in enumerate(functions)}
    fn_defs = {fn['id']: fn for fn in functions}
    signatures, type_ids = [], []
    for fn in functions:
        signature = (len(fn['params']), fn['result'])
        if signature not in signatures: signatures.append(signature)
        type_ids.append(signatures.index(signature))
    types = vector([b'\x60' + vector([b'\x7f'] * count) + vector([b'\x7f'] if result == 'i32' else [])
                    for count, result in signatures])
    bodies, positions = [], []
    complete = True
    body_cursor = len(unsigned(len(functions)))
    for fn in functions:
        graph = {node['id']: node for node in fn['nodes']}
        slots = {key: i for i, key in enumerate(fn['params'] + fn['locals'])}
        extra, local_positions = [], []
        code = bytearray()
        def temp():
            result = len(slots) + len(extra)
            extra.append(result)
            return result
        def const(value): return b'\x41' + signed(value)
        def get(index): return b'\x20' + unsigned(index)
        def put(index): return b'\x21' + unsigned(index)
        def trap(key, kind):
            nonlocal complete
            if collect:
                if len(positions) + len(local_positions) < MAX_TRAP_POSITIONS:
                    local_positions.append({'function_index':fn_index[fn['id']], 'function':fn['id'],
                                            'node':key, 'kind':kind, 'offset':len(code)})
                else:
                    complete = False
        def result_type(key):
            op = graph[key]['op']
            if op == 'call': return fn_defs[graph[key]['target']]['result']
            if op in ('flow.if', 'flow.guard'): return result_type(graph[key]['args'][1])
            return 'unit' if op in ('local.set','state.store','state.reset','flow.sequence','flow.repeat','flow.assert') else 'i32'
        def address(key, node):
            field = plan['layout'][node['cell']]
            scratch = temp()
            emit(node['args'][0]); code.extend(put(scratch))
            code.extend(get(scratch) + const(0) + b'\x48' + get(scratch) + const(field['count']) + b'\x4e\x72')
            code.extend(b'\x04\x40'); trap(key, 'bounds'); code.extend(b'\x00\x0b')
            code.extend(get(scratch) + const(4) + b'\x6c' + const(field['offset']) + b'\x6a')
        def emit(key):
            node = graph[key]
            op, args = node['op'], node.get('args', [])
            if op == 'i32.const': code.extend(const(node['value']))
            elif op == 'const.load': code.extend(const(doc['constants'][node['name']]))
            elif op == 'local.get': code.extend(get(slots[node['name']]))
            elif op == 'local.set':
                emit(args[0]); code.extend(put(slots[node['name']]))
            elif op in BINARY:
                emit(args[0]); emit(args[1])
                if op in ('i32.div_s','i32.rem_s'): trap(key, 'arithmetic')
                code.append(BINARY[op])
            elif op == 'i32.eqz': emit(args[0]); code.extend(b'\x45')
            elif op == 'state.load': address(key, node); code.extend(b'\x28\x02\x00')
            elif op == 'state.store':
                address(key, node); emit(args[1]); code.extend(b'\x36\x02\x00')
            elif op == 'state.reset':
                for cell_id in node['cells']:
                    for idx, val in enumerate(initial_cells[cell_id]):
                        code.extend(const(plan['layout'][cell_id]['offset'] + idx * 4) + const(val) + b'\x36\x02\x00')
            elif op == 'flow.sequence':
                for ref in args: emit(ref)
            elif op in ('flow.assert', 'flow.guard'):
                emit(args[0]); code.extend(b'\x45\x04\x40'); trap(key, 'assertion'); code.extend(b'\x00\x0b')
                if op == 'flow.guard': emit(args[1])
            elif op == 'flow.if':
                kind = b'\x7f' if result_type(key) == 'i32' else b'\x40'
                emit(args[0]); code.extend(b'\x04' + kind); emit(args[1]); code.extend(b'\x05'); emit(args[2]); code.extend(b'\x0b')
            elif op == 'call':
                for ref in args: emit(ref)
                code.extend(b'\x10' + unsigned(fn_index[node['target']]))
            elif op == 'flow.repeat':
                counter = temp()
                code.extend(const(0) + put(counter) + b'\x02\x40\x03\x40')
                code.extend(get(counter) + const(node['count']) + b'\x4e\x0d\x01')
                code.extend(get(counter) + put(slots[node['counter']]))
                emit(args[0])
                code.extend(get(counter) + const(1) + b'\x6a' + put(counter) + b'\x0c\x00\x0b\x0b')
            else: raise AssertionError(op)
        emit(fn['entry']); code.extend(b'\x0b')
        local_count = len(fn['locals']) + len(extra)
        locals_blob = vector([unsigned(local_count) + b'\x7f']) if local_count else vector([])
        body = locals_blob + code
        size = unsigned(len(body))
        for position in local_positions:
            position['offset'] += body_cursor + len(size) + len(locals_blob)
        positions.extend(local_positions)
        bodies.append(size + body)
        body_cursor += len(size) + len(body)
    exports = [name('memory') + b'\x02\x00']
    exports.extend(name(key) + b'\x00' + unsigned(fn_index[key]) for key in doc['exports'])
    data = b'\x00\x41\x00\x0b' + unsigned(len(plan['initial_data'])) + plan['initial_data']
    prefix = WASM_HEADER + b''.join([
        section(1, types), section(3, vector([unsigned(index) for index in type_ids])),
        section(5, vector([b'\x01\x02\x02'])), section(7, vector(exports))])
    code_payload = vector(bodies)
    code_start = len(prefix) + 1 + len(unsigned(len(code_payload)))
    binary = prefix + section(10, code_payload) + section(11, vector([data]))
    if not collect: return binary, None
    for position in positions: position['offset'] += code_start
    return binary, {'format':'pact.wasm-traps/0.1.0', 'wasm_sha256':hashlib.sha256(binary).hexdigest(),
                    'semantic_revision_sha256':revision(doc), 'complete':complete,
                    'coordinates':'zero-based absolute Wasm byte offsets', 'positions':positions}
