from .module import analyze_module
from .diagnostics import PactError


def wrap(value): return (value + 2**31) % 2**32 - 2**31


class Machine:
    def __init__(self, document):
        self.plan = analyze_module(document)
        self.document = document
        self.initial_state = {cell['id']: list(cell['values']) for cell in document['cells']}
        self.state = {cell_id: list(values) for cell_id, values in self.initial_state.items()}
        self.functions = {fn['id']: fn for fn in document['functions']}

    def call(self, name, *args):
        fn = self.functions[name]
        if len(args) != len(fn['params']): raise ValueError('arity')
        locals_ = dict.fromkeys(fn['locals'], 0)
        locals_.update(zip(fn['params'], args))
        nodes = {node['id']: node for node in fn['nodes']}
        def evaluate(key):
            node = nodes[key]
            op, refs = node['op'], node.get('args', [])
            if op == 'i32.const': return node['value']
            if op == 'const.load': return self.document['constants'][node['name']]
            if op == 'local.get': return locals_[node['name']]
            if op == 'local.set': locals_[node['name']] = evaluate(refs[0]); return None
            if op == 'state.reset':
                for cell_id in node['cells']:
                    self.state[cell_id] = list(self.initial_state[cell_id])
                return None
            if op == 'flow.if': return evaluate(refs[1] if evaluate(refs[0]) else refs[2])
            if op in ('flow.assert', 'flow.guard'):
                if not evaluate(refs[0]):
                    error = PactError('ASSERTION_FAILED', 'Runtime predicate was zero.', key)
                    error.diagnostic['function'] = name
                    raise error
                return evaluate(refs[1]) if op == 'flow.guard' else None
            if op == 'flow.sequence':
                for ref in refs: evaluate(ref)
                return None
            if op == 'flow.repeat':
                for index in range(node['count']):
                    locals_[node['counter']] = index
                    evaluate(refs[0])
                return None
            if op == 'call': return self.call(node['target'], *[evaluate(ref) for ref in refs])
            values = [evaluate(ref) for ref in refs]
            if op.startswith('state.'):
                array, index = self.state[node['cell']], values[0]
                if index < 0 or index >= len(array): raise IndexError('state bounds')
                if op == 'state.load': return array[index]
                array[index] = values[1]
                return None
            if op == 'i32.eqz': return int(values[0] == 0)
            a, b = values
            if op == 'i32.add_wrap': return wrap(a+b)
            if op == 'i32.sub_wrap': return wrap(a-b)
            if op == 'i32.mul_wrap': return wrap(a*b)
            if op in ('i32.div_s','i32.rem_s'):
                if b == 0 or op == 'i32.div_s' and a == -(2**31) and b == -1: raise ArithmeticError('division trap')
                quotient = (abs(a)//abs(b)) * (-1 if (a<0) != (b<0) else 1)
                return quotient if op == 'i32.div_s' else a-quotient*b
            if op == 'i32.eq': return int(a == b)
            if op == 'i32.ne': return int(a != b)
            if op == 'i32.lt_s': return int(a < b)
            if op == 'i32.gt_s': return int(a > b)
            if op == 'i32.le_s': return int(a <= b)
            if op == 'i32.ge_s': return int(a >= b)
            if op == 'i32.and': return wrap(a & b)
            if op == 'i32.or': return wrap(a | b)
            raise AssertionError(op)
        return evaluate(fn['entry'])
