"""Compact, reversible syntax for the checked PACT graph and numeric IR."""
import json
import re

from .diagnostics import PactError
from .schema import IDENTIFIER, MAX_SOURCE_BYTES, require

HEADER = 'pact 0.2'
WORD = IDENTIFIER
FIELDS = {
    'i32.const': ('value',), 'utf8.literal': ('value',),
    'const.load': ('name',), 'local.get': ('name',),
    'local.set': ('name', 'args'), 'state.load': ('cell', 'args'),
    'state.store': ('cell', 'args'), 'flow.repeat': ('count', 'counter', 'args'),
    'call': ('target', 'args'),
}
ALIASES = {'get': 'state.load', 'set': 'state.store',
           'add.wrap': 'i32.add_wrap', 'sub.wrap': 'i32.sub_wrap',
           'mul.wrap': 'i32.mul_wrap', 'seq': 'flow.sequence', 'if': 'flow.if'}
SHORT = {value: key for key, value in ALIASES.items()}
FUNCTION_FIELDS = ('params', 'locals', 'result', 'writes')


def validate_document(document):
    from .graph import analyze
    from .module import FORMAT, analyze_module
    if isinstance(document, dict) and document.get('format') == FORMAT:
        return analyze_module(document)
    return analyze(document)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'COMPACT_INVALID', f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _values(text):
    decoder = json.JSONDecoder(object_pairs_hook=_pairs)
    values = []
    while text.strip():
        text = text.lstrip()
        if text[0] in '[{"' or text[0] == '-' or text[0].isdigit():
            value, end = decoder.raw_decode(text)
            require(end == len(text) or text[end].isspace(), 'COMPACT_INVALID', 'Separate operands with spaces.')
            values.append(value)
            text = text[end:]
        else:
            parts = text.split(maxsplit=1)
            require(bool(WORD.fullmatch(parts[0])), 'COMPACT_INVALID', 'Invalid operand.')
            values.append(parts[0])
            text = parts[1] if len(parts) == 2 else ''
    return values


def _schema(op):
    from .module import OPERATIONS
    require(op in OPERATIONS or op in {'utf8.literal', 'utf8.concat', 'stdout.emit', 'effect.sequence'},
            'COMPACT_INVALID', f'Unknown operation: {op}')
    return FIELDS.get(op, ('args',))


def _node(line):
    name, expression = line.split('=', 1)
    name = name.strip()
    require(bool(WORD.fullmatch(name)), 'COMPACT_INVALID', 'Invalid node ID.')
    parts = expression.strip().split(maxsplit=1)
    require(bool(parts), 'COMPACT_INVALID', 'Missing operation.')
    op = ALIASES.get(parts[0], parts[0])
    fields = _schema(op)
    values = _values(parts[1] if len(parts) > 1 else '')
    fixed = len(fields) - ('args' in fields)
    require(len(values) >= fixed, 'COMPACT_INVALID', 'Missing operands.')
    node = {'id': name, 'op': op}
    for key, value in zip(fields[:fixed], values[:fixed]):
        node[key] = value
    if 'args' in fields:
        tail = values[fixed:]
        node['args'] = [] if tail == [[]] else tail
    else:
        require(len(values) == fixed, 'COMPACT_INVALID', 'Unexpected operands.')
    return node


def loads(source):
    """Parse and validate; never evaluate source as host code."""
    line_number = 0
    try:
        require(len(source.encode('utf-8')) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
        lines = [(n, line.strip()) for n, line in enumerate(source.split('\n'), 1)
                 if line.strip() and not line.lstrip().startswith('#')]
        require(bool(lines) and lines[0][1] == HEADER, 'COMPACT_INVALID', 'Expected pact 0.2 header.')
        document, function, ids = {}, None, set()
        for line_number, line in lines[1:]:
            if line.startswith('fn '):
                require(function is None, 'COMPACT_INVALID', 'Nested function.')
                name = line[3:].strip()
                require(bool(WORD.fullmatch(name)), 'COMPACT_INVALID', 'Invalid function ID.')
                require('nodes' not in document, 'COMPACT_INVALID', 'Cannot mix module functions and graph nodes.')
                function = {'id': name, 'nodes': []}
                document.setdefault('functions', []).append(function)
                ids = set()
            elif line == 'end':
                require(function is not None, 'COMPACT_INVALID', 'Unexpected end.')
                function = None
                ids = set()
            elif line.startswith('return '):
                require(function is not None and 'entry' not in function, 'COMPACT_INVALID', 'Unexpected return.')
                function['entry'] = line[7:].strip()
            elif re.match(r'^[A-Za-z][A-Za-z0-9_.:\-]*\s*=', line):
                require(function is not None or 'functions' not in document,
                        'COMPACT_INVALID', 'Module nodes must be inside a function.')
                node = _node(line)
                require(node['id'] not in ids, 'COMPACT_INVALID', 'Duplicate node ID.')
                ids.add(node['id'])
                target = function if function is not None else document
                target.setdefault('nodes', []).append(node)
            else:
                key, separator, value = line.partition(' ')
                require(bool(separator), 'COMPACT_INVALID', 'Expected section and JSON value.')
                target = function if function is not None else document
                require(key not in target and key not in {'nodes', 'functions', 'id'},
                        'COMPACT_INVALID', f'Duplicate or reserved field: {key}')
                if function is not None:
                    require(key in FUNCTION_FIELDS, 'COMPACT_INVALID', 'Unknown function field.')
                target[key] = json.loads(value, object_pairs_hook=_pairs)
        require(function is None, 'COMPACT_INVALID', 'Unterminated function.')
        validate_document(document)
        return document
    except (ValueError, RecursionError) as error:
        if isinstance(error, PactError):
            raise
        raise PactError('COMPACT_INVALID', f'Line {line_number}: {error}') from None


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _operand(value, literal=False):
    return value if isinstance(value, str) and WORD.fullmatch(value) and not literal else _json(value)


def _emit_node(node):
    fields = _schema(node['op'])
    operands = []
    for field in fields:
        value = node[field]
        if field == 'args':
            operands.extend(_operand(ref) for ref in value)
            if not value:
                operands.append('[]')
        else:
            operands.append(_operand(value, field == 'value'))
    return f"{node['id']} = {SHORT.get(node['op'], node['op'])}" + (' ' + ' '.join(operands) if operands else '')


def dumps(document):
    """Serialize validated IR; canonical formatting preserves all semantic fields."""
    validate_document(document)
    lines = [HEADER]
    for key, value in document.items():
        if key == 'nodes':
            lines.extend(_emit_node(node) for node in value)
        elif key == 'functions':
            for function in value:
                lines.append('fn ' + function['id'])
                lines.extend(key + ' ' + _json(function[key]) for key in FUNCTION_FIELDS)
                lines.extend(_emit_node(node) for node in function['nodes'])
                lines.extend(['return ' + function['entry'], 'end'])
        else:
            lines.append(key + ' ' + _json(value))
    return '\n'.join(lines) + '\n'
