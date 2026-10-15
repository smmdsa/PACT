"""Static nominal-unit contracts over already validated scalar numeric graphs."""
from .diagnostics import PactError
from .schema import closed_record, identifier, require


def check_units(document):
    declarations = document.get('units', {'names': [], 'cells': {}, 'constants': {}, 'functions': {}})
    closed_record(declarations, {'names', 'cells', 'constants', 'functions'})
    names = declarations['names']
    require(isinstance(names, list) and len(names) <= 128, 'UNIT_INVALID', 'Expected at most 128 nominal units.')
    for name in names:
        identifier(name)
        require(name not in ('i32', 'unit'), 'UNIT_INVALID', 'Reserved scalar/effect type cannot name a nominal unit.')
    require(len(set(names)) == len(names), 'UNIT_INVALID', 'Duplicate nominal unit.')
    numeric = set(names) | {'i32'}
    functions = {fn['id']: fn for fn in document['functions']}

    def bindings(record, available):
        require(isinstance(record, dict), 'UNIT_INVALID', 'Expected a unit binding map.')
        for key, value in record.items():
            require(isinstance(key, str) and key in available, 'UNIT_INVALID', 'Unknown unit binding target.')
            require(isinstance(value, str) and value in numeric, 'UNIT_INVALID', 'Unknown numeric unit.')
        return {key: record.get(key, 'i32') for key in sorted(available)}

    cells = bindings(declarations['cells'], {cell['id'] for cell in document['cells']})
    constants = bindings(declarations['constants'], document['constants'])
    declared_functions = declarations['functions']
    require(isinstance(declared_functions, dict), 'UNIT_INVALID', 'Expected function unit contracts.')
    require(all(isinstance(key, str) and key in functions for key in declared_functions),
            'UNIT_INVALID', 'Unknown function unit contract.')
    contracts = {}
    for key, fn in functions.items():
        raw = declared_functions.get(key, {'params': {}, 'locals': {}, 'literals': {}, 'result': fn['result']})
        closed_record(raw, {'params', 'locals', 'literals', 'result'})
        params = bindings(raw['params'], fn['params'])
        locals_ = bindings(raw['locals'], fn['locals'])
        literals = bindings(raw['literals'], {node['id'] for node in fn['nodes'] if node['op'] == 'i32.const'})
        result = raw['result']
        require(isinstance(result, str) and (result == 'unit' if fn['result'] == 'unit' else result in numeric),
                'UNIT_INVALID', 'Function unit contract has an incompatible result kind.', key)
        contracts[key] = {'params': params, 'locals': locals_, 'result': result,
                          'literals': {node: literals[node] for node in sorted(raw['literals'])}}

    for key, fn in functions.items():
        contract = contracts[key]
        graph = {node['id']: node for node in fn['nodes']}
        slots = contract['params'] | contract['locals']
        inferred = {}

        def same(actual, expected, node):
            require(actual == expected, 'UNIT_MISMATCH',
                    f'Expected nominal unit {expected}, got {actual}.', node)

        def infer(node_id):
            if node_id in inferred:
                return inferred[node_id]
            node = graph[node_id];op = node['op']
            args = [infer(ref) for ref in node.get('args', [])]
            result = 'unit'
            if op == 'i32.const': result = contract['literals'].get(node_id, 'i32')
            elif op == 'const.load': result = constants[node['name']]
            elif op == 'local.get': result = slots[node['name']]
            elif op == 'local.set': same(args[0], slots[node['name']], node_id)
            elif op in ('state.load', 'state.store'):
                same(args[0], 'i32', node_id)
                if op == 'state.load': result = cells[node['cell']]
                else: same(args[1], cells[node['cell']], node_id)
            elif op in ('i32.add_wrap', 'i32.sub_wrap', 'i32.rem_s'):
                same(args[1], args[0], node_id);result = args[0]
            elif op == 'i32.mul_wrap':
                require('i32' in args, 'UNIT_MISMATCH', 'Unitful products require unsupported derived units.', node_id)
                result = args[1] if args[0] == 'i32' else args[0]
            elif op == 'i32.div_s':
                if args[1] == 'i32': result = args[0]
                else:
                    same(args[0], args[1], node_id);result = 'i32'
            elif op in ('i32.eq', 'i32.ne', 'i32.lt_s', 'i32.gt_s', 'i32.le_s', 'i32.ge_s'):
                same(args[1], args[0], node_id);result = 'i32'
            elif op in ('i32.and', 'i32.or'):
                for arg in args: same(arg, 'i32', node_id)
                result = 'i32'
            elif op == 'i32.eqz': result = 'i32'
            elif op in ('flow.if', 'flow.guard', 'flow.assert'):
                same(args[0], 'i32', node_id)
                if op == 'flow.if': same(args[2], args[1], node_id)
                if op != 'flow.assert': result = args[1]
            elif op == 'flow.repeat': same(slots[node['counter']], 'i32', node_id)
            elif op == 'call':
                target = contracts[node['target']]
                for actual, param in zip(args, functions[node['target']]['params']):
                    same(actual, target['params'][param], node_id)
                result = target['result']
            elif op not in ('state.reset', 'flow.sequence'):
                raise AssertionError(op)
            inferred[node_id] = result
            return result

        try:
            same(infer(fn['entry']), contract['result'], fn['entry'])
        except PactError as error:
            error.diagnostic['function'] = key
            raise
    return {'format': 'pact.unit-contracts/0.1.0', 'names': sorted(names),
            'cells': cells, 'constants': constants, 'functions': dict(sorted(contracts.items()))}
