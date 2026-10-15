import hashlib
import json
import re
import struct

from .schema import closed_record, identifier, require

FORMAT = 'pact.module/0.2.0'
TESTED_FORMAT = 'pact.module/0.3.0'
CHECKED_FORMAT = 'pact.module/0.4.0'
TRAP_TESTED_FORMAT = 'pact.module/0.5.0'
FORMATS = ('pact.module/0.1.0', FORMAT, TESTED_FORMAT, CHECKED_FORMAT, TRAP_TESTED_FORMAT)
TRAP_OPERATIONS = {
    'ASSERTION_FAILED': {'flow.assert', 'flow.guard'},
    'STATE_BOUNDS': {'state.load', 'state.store'},
    'ARITHMETIC_TRAP': {'i32.div_s', 'i32.rem_s'},
}
BINARY = {
    'i32.add_wrap': 0x6a, 'i32.sub_wrap': 0x6b, 'i32.mul_wrap': 0x6c,
    'i32.div_s': 0x6d, 'i32.rem_s': 0x6f, 'i32.eq': 0x46, 'i32.ne': 0x47,
    'i32.lt_s': 0x48, 'i32.gt_s': 0x4a, 'i32.le_s': 0x4c, 'i32.ge_s': 0x4e,
    'i32.and': 0x71, 'i32.or': 0x72,
}
OPERATIONS = set(BINARY) | {'i32.const', 'const.load', 'local.get', 'local.set',
    'state.load', 'state.store', 'state.reset', 'flow.if', 'flow.sequence', 'flow.repeat',
    'flow.assert', 'flow.guard', 'call', 'i32.eqz'}
# pact.module/0.1.0 operations (docs/superpowers/specs/2026-10-13-platformer.md); preserved exactly.
OPERATIONS_0_2_0 = OPERATIONS - {'flow.assert', 'flow.guard'}
OPERATIONS_0_1_0 = OPERATIONS_0_2_0 - {'state.reset'}
MAX_WORK = 2_000_000


def integer(value):
    require(type(value) is int and -(2**31) <= value < 2**31, 'INTEGER_INVALID', 'Expected signed i32.')


def compile_assets(assets, offset):
    closed_record(assets, {'palettes', 'tiles'})
    require(isinstance(assets['palettes'], list) and isinstance(assets['tiles'], list), 'ASSET_INVALID', 'Expected palette/tile lists.')
    require(len(assets['tiles']) <= 128, 'ASSET_INVALID', 'At most 128 tiles.')
    palettes, tiles, data = {}, {}, bytearray()
    for palette in assets['palettes']:
        closed_record(palette, {'id', 'colors'})
        identifier(palette['id'])
        require(palette['id'] not in palettes and isinstance(palette['colors'], dict), 'ASSET_INVALID', 'Invalid palette.')
        colors = {}
        for key, color in palette['colors'].items():
            identifier(key)
            require(isinstance(color, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', color), 'ASSET_INVALID', 'Expected #RRGGBB.')
            colors[key] = bytes.fromhex(color[1:]) + b'\xff'
        palettes[palette['id']] = colors
    for tile in assets['tiles']:
        closed_record(tile, {'id', 'palette', 'symbols', 'pixels'})
        identifier(tile['id'])
        require(tile['id'] not in tiles and isinstance(tile['palette'], str) and tile['palette'] in palettes, 'ASSET_INVALID', 'Invalid tile palette/id.')
        rows, symbols = tile['pixels'], tile['symbols']
        require(isinstance(rows, list) and len(rows) == 8 and all(isinstance(row, str) and len(row) == 8 for row in rows), 'ASSET_INVALID', 'Tiles are exactly 8x8.')
        require(isinstance(symbols, dict) and all(isinstance(key, str) and len(key) == 1 for key in symbols), 'ASSET_INVALID', 'Symbols are single characters.')
        colors = palettes[tile['palette']]
        for value in symbols.values():
            require(value is None or isinstance(value, str) and value in colors, 'ASSET_INVALID', 'Unknown symbolic color.')
        pixels = bytearray()
        for row in rows:
            for symbol in row:
                require(symbol in symbols, 'ASSET_INVALID', 'Unknown pixel symbol.')
                key = symbols[symbol]
                pixels.extend(b'\x00\x00\x00\x00' if key is None else colors[key])
        tiles[tile['id']] = {'offset': offset + len(data), 'width': 8, 'height': 8}
        data.extend(pixels)
    return tiles, bytes(data)


def analyze_module(document):
    try:
        json.dumps(document, ensure_ascii=False).encode('utf-8')
    except UnicodeEncodeError:
        from .diagnostics import PactError
        raise PactError('UTF8_INVALID', 'Metadata contains an invalid Unicode surrogate.') from None
    except (TypeError, ValueError, RecursionError):
        from .diagnostics import PactError
        raise PactError('SCHEMA_INVALID', 'Module must contain finite JSON data.') from None
    closed_record(document, {'format', 'constants', 'cells', 'functions', 'exports', 'assets', 'presentation', 'tests'})
    require(document['format'] in FORMATS, 'FORMAT_UNSUPPORTED', 'Unsupported module format.')
    operations = (OPERATIONS_0_1_0 if document['format'] == FORMATS[0] else
                  OPERATIONS if document['format'] in FORMATS[3:] else OPERATIONS_0_2_0)
    constants = document['constants']
    require(isinstance(constants, dict) and len(constants) <= 1024, 'SCHEMA_INVALID', 'Expected bounded constants.')
    for key, value in constants.items():
        identifier(key)
        integer(value)
    cells = document['cells']
    require(isinstance(cells, list) and 1 <= len(cells) <= 128, 'SCHEMA_INVALID', 'Expected 1..128 cells.')
    layout, offset, initial = {}, 0, bytearray()
    for cell in cells:
        closed_record(cell, {'id', 'values', 'mutable'})
        identifier(cell['id'])
    for cell in sorted(cells, key=lambda item: item['id']):
        closed_record(cell, {'id', 'values', 'mutable'})
        key, values = cell['id'], cell['values']
        identifier(key)
        require(key not in layout, 'ID_DUPLICATE', 'Duplicate cell.')
        require(type(cell['mutable']) is bool and isinstance(values, list) and 1 <= len(values) <= 4096, 'SCHEMA_INVALID', 'Invalid cell extent.')
        for value in values:
            integer(value)
            initial.extend(struct.pack('<i', value))
        layout[key] = {'offset': offset, 'count': len(values), 'mutable': cell['mutable']}
        offset += len(values) * 4
    require(offset <= 65536, 'MEMORY_LIMIT', 'State exceeds one page.')
    tiles, atlas = compile_assets(document['assets'], offset)
    require(offset + len(atlas) <= 131072, 'MEMORY_LIMIT', 'Module exceeds two pages.')
    require(isinstance(document['presentation'], dict) and isinstance(document['tests'], list), 'SCHEMA_INVALID', 'Invalid presentation/tests.')
    from .presentation import validate_presentation
    validate_presentation(document['presentation'], layout, tiles, document['exports'])
    functions = document['functions']
    require(isinstance(functions, list) and 1 <= len(functions) <= 128, 'FUNCTION_LIMIT', 'Expected 1..128 functions.')
    indexed, graphs = {}, {}
    for function in functions:
        closed_record(function, {'id', 'params', 'locals', 'result', 'writes', 'entry', 'nodes'})
        key = function['id']
        identifier(key)
        require(key not in indexed, 'ID_DUPLICATE', 'Duplicate function.')
        for field in ('params', 'locals', 'writes'):
            require(isinstance(function[field], list) and len(function[field]) <= 128, 'SCHEMA_INVALID', 'Invalid function slots.')
            for name in function[field]:
                identifier(name)
            require(len(set(function[field])) == len(function[field]), 'ID_DUPLICATE', 'Duplicate function slot.')
        slots = function['params'] + function['locals']
        require(len(set(slots)) == len(slots), 'ID_DUPLICATE', 'Params and locals cannot overlap.')
        require(function['result'] in ('i32', 'unit'), 'TYPE_MISMATCH', 'Invalid function result.')
        nodes = function['nodes']
        require(isinstance(nodes, list) and 1 <= len(nodes) <= 2048, 'NODE_LIMIT', 'Expected bounded nodes.')
        graph = {}
        for node in nodes:
            require(isinstance(node, dict), 'SCHEMA_INVALID', 'Expected node record.')
            name, op = node.get('id'), node.get('op')
            identifier(name)
            require(isinstance(op, str) and op in operations, 'OP_UNKNOWN', 'Unknown numeric operation.', name)
            fields = {'id', 'op'}
            if op == 'i32.const': fields |= {'value'}
            elif op in ('const.load', 'local.get'): fields |= {'name'}
            elif op == 'local.set': fields |= {'name', 'args'}
            elif op in ('state.load', 'state.store'): fields |= {'cell', 'args'}
            elif op == 'state.reset': fields |= {'cells'}
            elif op == 'flow.repeat': fields |= {'count', 'counter', 'args'}
            elif op == 'call': fields |= {'target', 'args'}
            else: fields |= {'args'}
            closed_record(node, fields, name)
            require(name not in graph, 'ID_DUPLICATE', 'Duplicate node.', name)
            if op == 'i32.const': integer(node['value'])
            if 'name' in node:
                require(isinstance(node['name'], str) and node['name'] in (constants if op == 'const.load' else slots), 'REFERENCE_MISSING', 'Unknown constant/local.', name)
            if 'cell' in node:
                require(isinstance(node['cell'], str) and node['cell'] in layout, 'STATE_MISSING', 'Unknown state cell.', name)
                if op == 'state.store': require(layout[node['cell']]['mutable'], 'STATE_IMMUTABLE', 'Cannot store immutable state.', name)
            if op == 'state.reset':
                require(isinstance(node['cells'], list) and 1 <= len(node['cells']) <= 128, 'ARGUMENT_LIMIT', 'Expected 1..128 reset cells.', name)
                seen_reset = set()
                for cell_id in node['cells']:
                    identifier(cell_id, name)
                    require(cell_id in layout, 'STATE_MISSING', 'Unknown state cell.', name)
                    require(layout[cell_id]['mutable'], 'STATE_IMMUTABLE', 'Cannot reset immutable state.', name)
                    require(cell_id not in seen_reset, 'ID_DUPLICATE', 'Duplicate reset cell.', name)
                    seen_reset.add(cell_id)
            if 'args' in node:
                require(isinstance(node['args'], list) and len(node['args']) <= 128, 'ARGUMENT_LIMIT', 'Invalid arguments.', name)
                for ref in node['args']: identifier(ref, name)
            if op == 'flow.repeat':
                require(type(node['count']) is int and 0 <= node['count'] <= 256 and node['counter'] in function['locals'], 'LOOP_INVALID', 'Repeat needs bounded count and local counter.', name)
            graph[name] = node
        require(isinstance(function['entry'], str) and function['entry'] in graph, 'REFERENCE_MISSING', 'Missing entry.')
        for node in nodes:
            for ref in node.get('args', []): require(ref in graph, 'REFERENCE_MISSING', 'Missing node reference.', node['id'])
        indexed[key], graphs[key] = function, graph
    for graph in graphs.values():
        for node in graph.values():
            if node['op'] == 'call': require(isinstance(node['target'], str) and node['target'] in indexed, 'REFERENCE_MISSING', 'Missing function.', node['id'])
    exports = document['exports']
    require(isinstance(exports, list) and all(isinstance(key, str) and key in indexed and key != 'memory' for key in exports) and len(exports) == len(set(exports)), 'EXPORT_INVALID', 'Invalid exports.')
    active, finished, effects, costs, function_depth = set(), set(), {}, {}, {}

    def check_function(key):
        require(key not in active, 'CALL_RECURSION', 'Recursive functions are not permitted.', key)
        if key in finished: return
        require(len(active) < 64, 'CALL_DEPTH', 'Call nesting exceeds 64.')
        active.add(key)
        fn, graph = indexed[key], graphs[key]
        for node in graph.values():
            if node['op'] == 'call': check_function(node['target'])
        visiting, types, work, writes, depths = set(), {}, {}, set(), {}
        def infer(name):
            require(name not in visiting, 'GRAPH_CYCLE', 'Cyclic expression.', name)
            if name in types: return types[name]
            require(len(visiting) < 128, 'EXPRESSION_DEPTH', 'Expression nesting exceeds 128.', name)
            visiting.add(name)
            node, op = graph[name], graph[name]['op']
            args = node.get('args', [])
            argtypes = [infer(ref) for ref in args]
            result, arity = 'i32', None
            if op in ('i32.const', 'const.load', 'local.get'): arity = 0
            elif op in BINARY: arity = 2
            elif op == 'i32.eqz': arity = 1
            elif op in ('local.set', 'state.store'):
                result, arity = 'unit', 1 if op == 'local.set' else 2
                if op == 'state.store': writes.add(node['cell'])
            elif op == 'state.reset':
                result, arity = 'unit', 0
                writes.update(node['cells'])
            elif op == 'state.load': arity = 1
            elif op == 'flow.assert': result, arity = 'unit', 1
            elif op == 'flow.guard':
                arity = 2
                require(len(args) == arity, 'ARITY_INVALID', 'Invalid operand count.', name)
                require(argtypes[0] == 'i32', 'TYPE_MISMATCH', 'guard requires an i32 predicate.', name)
                result = argtypes[1]
            elif op == 'flow.if':
                arity = 3
                require(len(argtypes) == 3 and argtypes[0] == 'i32' and argtypes[1] == argtypes[2], 'TYPE_MISMATCH', 'if requires matching branches.', name)
                result = argtypes[1]
            elif op in ('flow.sequence', 'flow.repeat'):
                result = 'unit'
                if op == 'flow.repeat': arity = 1
                require(all(kind == 'unit' for kind in argtypes), 'TYPE_MISMATCH', 'Flow expects unit actions.', name)
            elif op == 'call':
                target = indexed[node['target']]
                arity, result = len(target['params']), target['result']
                writes.update(effects[node['target']])
            if arity is not None: require(len(args) == arity, 'ARITY_INVALID', 'Invalid operand count.', name)
            if op not in ('flow.if', 'flow.sequence', 'flow.repeat', 'flow.guard'):
                require(all(kind == 'i32' for kind in argtypes), 'TYPE_MISMATCH', 'Expected i32 operands.', name)
            depth = 1 + max((depths[ref] for ref in args), default=0)
            if op == 'call': depth += function_depth[node['target']]
            require(depth <= 128, 'EVALUATION_DEPTH', 'Combined call/expression depth exceeds 128.', name)
            depths[name] = depth
            base_work = sum(layout[cell_id]['count'] for cell_id in node['cells']) if op == 'state.reset' else 1
            estimate = base_work + sum(work[ref] for ref in args)
            if op == 'flow.repeat': estimate *= node['count'] + 1
            if op == 'call': estimate += costs[node['target']]
            require(estimate <= MAX_WORK, 'WORK_LIMIT', 'Expanded execution budget exceeded.', name)
            visiting.remove(name)
            types[name], work[name] = result, estimate
            return result
        result = infer(fn['entry'])
        require(result == fn['result'], 'TYPE_MISMATCH', 'Function result differs from its body.', key)
        require(set(types) == set(graph), 'NODE_UNREACHABLE', 'Unused function nodes.', key,
                fix={'op': 'remove_unreachable', 'function': key,
                     'unreachable_nodes': sorted(set(graph) - set(types))})
        references = {name: 0 for name in graph}
        for node in graph.values():
            for ref in node.get('args', []): references[ref] += 1
        require(all(references[name] <= 1 for name, kind in types.items() if kind == 'unit'), 'EFFECT_SHARED', 'Unit actions cannot have multiple execution edges.', key)
        require(writes == set(fn['writes']), 'WRITE_MISMATCH', 'Declared writes differ from transitive writes.', key,
                fix={'op': 'set_writes', 'function': key,
                     'declared_writes': list(fn['writes']), 'expected_writes': sorted(writes)})
        require(fn['result'] == 'unit' or not writes, 'IMPURE_EXPRESSION', 'Numeric functions cannot mutate state.', key)
        effects[key], costs[key] = writes, work[fn['entry']]
        function_depth[key] = depths[fn['entry']]
        active.remove(key)
        finished.add(key)
    for key in indexed: check_function(key)
    require(sum(costs.values()) <= 500_000, 'COMPILER_BUDGET', 'Aggregate expansion exceeds 500,000 operations.')
    test_ids = set()
    require(len(document['tests']) <= 256, 'TEST_INVALID', 'Too many tests.')
    for test in document['tests']:
        require(isinstance(test, dict), 'TEST_INVALID', 'Expected test record.')
        fields = {'id', 'function', 'set', 'expect'} | (set(test) & {'args', 'result'})
        if document['format'] == TRAP_TESTED_FORMAT and 'trap' in test:
            fields.add('trap')
        closed_record(test, fields)
        identifier(test['id'])
        require(test['id'] not in test_ids, 'ID_DUPLICATE', 'Duplicate test ID.')
        test_ids.add(test['id'])
        require(isinstance(test['function'], str) and test['function'] in exports, 'TEST_INVALID', 'Tests call exported functions only.')
        test_args = test.get('args', [])
        require(isinstance(test_args, list) and len(test_args) == len(indexed[test['function']]['params']), 'TEST_INVALID', 'Invalid test arguments.')
        for value in test_args: integer(value)
        if 'result' in test: integer(test['result'])
        if 'trap' in test:
            trap = test['trap']
            closed_record(trap, {'code', 'function', 'node'})
            require('result' not in test, 'TEST_INVALID', 'A trap case cannot expect a return value.')
            require(isinstance(trap['code'], str) and trap['code'] in TRAP_OPERATIONS,
                    'TEST_INVALID', 'Unknown expected trap code.')
            require(isinstance(trap['function'], str) and trap['function'] in indexed,
                    'TEST_INVALID', 'Unknown expected trap function.')
            sites = {node['id']: node for node in indexed[trap['function']]['nodes']}
            require(isinstance(trap['node'], str) and trap['node'] in sites,
                    'TEST_INVALID', 'Unknown expected trap node.')
            require(sites[trap['node']]['op'] in TRAP_OPERATIONS[trap['code']],
                    'TEST_INVALID', 'Expected trap code does not match the node operation.')
        require(test['expect'] or 'result' in test or 'trap' in test,
                'TEST_EMPTY', 'Tests require an expected value or trap.')
        for category in ('set', 'expect'):
            require(isinstance(test[category], dict), 'TEST_INVALID', 'Expected test cell values.')
            for cell, values in test[category].items():
                require(cell in layout and isinstance(values, list) and 1 <= len(values) <= layout[cell]['count'], 'TEST_INVALID', 'Invalid test state extent.')
                require(category != 'set' or layout[cell]['mutable'], 'STATE_IMMUTABLE', 'Tests cannot overwrite immutable cells.')
                for value in values: integer(value)
    export_evidence = None
    if document['format'] in FORMATS[2:]:
        export_evidence = {key: sorted(test['id'] for test in document['tests']
                                      if test['function'] == key) for key in sorted(exports)}
        missing = [key for key, cases in export_evidence.items() if not cases]
        require(not missing, 'EXPORT_EVIDENCE_MISSING',
                'Every exported function requires at least one declared test.',
                fix={'op': 'add_export_tests', 'functions': missing})
    normalized = dict(document)
    normalized['functions'] = sorted(functions, key=lambda fn: fn['id'])
    normalized['cells'] = sorted(cells, key=lambda cell: cell['id'])
    source = json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    plan = {'format': 'pact.module-plan/' + document['format'].rsplit('/', 1)[-1], 'document': document, 'layout': layout,
            'function_types': {key: {'params': len(fn['params']), 'result': fn['result']} for key, fn in indexed.items()},
            'source_sha256': hashlib.sha256(source).hexdigest(), 'tiles': tiles, 'atlas_offset': offset,
            'initial_data': bytes(initial) + atlas, 'work': costs}
    if export_evidence is not None:
        plan['declared_export_tests'] = export_evidence
    return plan


def migrate_module(document, target_format=FORMAT):
    """Migrate a validated numeric module strictly forward to a supported format.

    The historical default remains 0.1.0 to 0.2.0. Only the format changes:
    the migration adds no state.reset nodes or tests,
    so every cell write remains an explicit state.store. The migrated document
    compiles to byte-identical WebAssembly, while its canonical semantic
    revision differs because the format version is semantic content.
    """
    import copy
    analyze_module(document)
    require(target_format in FORMATS and
            FORMATS.index(document['format']) < FORMATS.index(target_format),
            'MIGRATION_UNSUPPORTED', 'Migration requires a supported strictly newer module format.')
    migrated = copy.deepcopy(document)
    migrated['format'] = target_format
    analyze_module(migrated)
    return migrated
