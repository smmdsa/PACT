from .module import BINARY
from .wasm import WASM_HEADER, section, vector, unsigned, signed, name


def compile_module(plan):
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
    bodies = []
    for fn in functions:
        graph = {node['id']: node for node in fn['nodes']}
        slots = {key: i for i, key in enumerate(fn['params'] + fn['locals'])}
        extra = []
        def temp():
            result = len(slots) + len(extra)
            extra.append(result)
            return result
        def const(value): return b'\x41' + signed(value)
        def get(index): return b'\x20' + unsigned(index)
        def put(index): return b'\x21' + unsigned(index)
        def result_type(key):
            op = graph[key]['op']
            if op == 'call': return fn_defs[graph[key]['target']]['result']
            if op == 'flow.if': return result_type(graph[key]['args'][1])
            return 'unit' if op in ('local.set','state.store','state.reset','flow.sequence','flow.repeat') else 'i32'
        def address(node):
            field = plan['layout'][node['cell']]
            scratch = temp()
            check = emit(node['args'][0]) + put(scratch)
            check += get(scratch) + const(0) + b'\x48' + get(scratch) + const(field['count']) + b'\x4e\x72'
            check += b'\x04\x40\x00\x0b'
            return check + get(scratch) + const(4) + b'\x6c' + const(field['offset']) + b'\x6a'
        def emit(key):
            node = graph[key]
            op, args = node['op'], node.get('args', [])
            if op == 'i32.const': return const(node['value'])
            if op == 'const.load': return const(doc['constants'][node['name']])
            if op == 'local.get': return get(slots[node['name']])
            if op == 'local.set': return emit(args[0]) + put(slots[node['name']])
            if op in BINARY: return emit(args[0]) + emit(args[1]) + bytes([BINARY[op]])
            if op == 'i32.eqz': return emit(args[0]) + b'\x45'
            if op == 'state.load': return address(node) + b'\x28\x02\x00'
            if op == 'state.store': return address(node) + emit(args[1]) + b'\x36\x02\x00'
            if op == 'state.reset':
                return b''.join(
                    const(plan['layout'][cell_id]['offset'] + idx * 4) + const(val) + b'\x36\x02\x00'
                    for cell_id in node['cells']
                    for idx, val in enumerate(initial_cells[cell_id])
                )
            if op == 'flow.sequence': return b''.join(emit(ref) for ref in args)
            if op == 'flow.if':
                kind = b'\x7f' if result_type(key) == 'i32' else b'\x40'
                return emit(args[0]) + b'\x04' + kind + emit(args[1]) + b'\x05' + emit(args[2]) + b'\x0b'
            if op == 'call': return b''.join(emit(ref) for ref in args) + b'\x10' + unsigned(fn_index[node['target']])
            if op == 'flow.repeat':
                counter = temp()
                head = const(0) + put(counter) + b'\x02\x40\x03\x40'
                head += get(counter) + const(node['count']) + b'\x4e\x0d\x01'
                head += get(counter) + put(slots[node['counter']])
                tail = get(counter) + const(1) + b'\x6a' + put(counter) + b'\x0c\x00\x0b\x0b'
                return head + emit(args[0]) + tail
            raise AssertionError(op)
        code = emit(fn['entry']) + b'\x0b'
        local_count = len(fn['locals']) + len(extra)
        locals_blob = vector([unsigned(local_count) + b'\x7f']) if local_count else vector([])
        body = locals_blob + code
        bodies.append(unsigned(len(body)) + body)
    exports = [name('memory') + b'\x02\x00']
    exports.extend(name(key) + b'\x00' + unsigned(fn_index[key]) for key in doc['exports'])
    data = b'\x00\x41\x00\x0b' + unsigned(len(plan['initial_data'])) + plan['initial_data']
    return WASM_HEADER + b''.join([
        section(1, types), section(3, vector([unsigned(index) for index in type_ids])),
        section(5, vector([b'\x01\x02\x02'])), section(7, vector(exports)),
        section(10, vector(bodies)), section(11, vector([data]))])
