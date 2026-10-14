"""Compact, reversible syntax for the checked PACT graph and numeric IR."""
import json
import re

from .diagnostics import PactError
from .schema import IDENTIFIER, MAX_SOURCE_BYTES, require

HEADER = 'pact 0.2'
DATA_HEADER = 'pact 0.3'
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
    cursor = 0
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue
        if text[cursor] in '[{"' or text[cursor] == '-' or text[cursor].isdigit():
            try:
                value, end = decoder.raw_decode(text, cursor)
            except json.JSONDecodeError as error:
                # Keep operand-relative diagnostics; copying occurs only on rejection.
                raise json.JSONDecodeError(error.msg, text[cursor:], error.pos - cursor) from None
            require(end == len(text) or text[end].isspace(), 'COMPACT_INVALID', 'Separate operands with spaces.')
            values.append(value)
            cursor = end
        else:
            end = cursor + 1
            while end < len(text) and not text[end].isspace():
                end += 1
            value = text[cursor:end]
            require(bool(WORD.fullmatch(value)), 'COMPACT_INVALID', 'Invalid operand.')
            values.append(value)
            cursor = end
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
        require(bool(lines) and lines[0][1] in (HEADER, DATA_HEADER), 'COMPACT_INVALID', 'Expected pact 0.2 or pact 0.3 header.')
        data_version = lines[0][1] == DATA_HEADER
        packed_sections = False
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
                packed = key in ('cells.packed', 'assets.shared')
                if packed:
                    require(data_version and function is None, 'COMPACT_INVALID', 'Compressed sections require module-level pact 0.3.')
                    encoded_key = key
                    key = 'cells' if key == 'cells.packed' else 'assets'
                target = function if function is not None else document
                require(key not in target and key not in {'nodes', 'functions', 'id'},
                        'COMPACT_INVALID', f'Duplicate or reserved field: {key}')
                if function is not None:
                    require(key in FUNCTION_FIELDS, 'COMPACT_INVALID', 'Unknown function field.')
                record = json.loads(value, object_pairs_hook=_pairs)
                if packed:
                    if encoded_key == 'cells.packed':
                        from .data_codec import decode_cells
                        record = decode_cells(record)
                    else:
                        from .atlas_codec import decode_assets
                        record = decode_assets(record)
                    packed_sections = True
                target[key] = record
        require(function is None, 'COMPACT_INVALID', 'Unterminated function.')
        require(not packed_sections or document.get('format') == 'pact.module/0.1.0',
                'COMPACT_INVALID', 'Compressed sections support numeric modules only.')
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


def dumps(document, compressed=False):
    """Serialize validated IR; canonical formatting preserves all semantic fields."""
    validate_document(document)
    lines = [DATA_HEADER if compressed else HEADER]
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
            plain = key + ' ' + _json(value)
            encoded = plain
            if compressed and key == 'cells':
                from .data_codec import encode_cells
                encoded = 'cells.packed ' + _json(encode_cells(value))
            elif compressed and key == 'assets':
                from .atlas_codec import encode_assets
                encoded = 'assets.shared ' + _json(encode_assets(value))
            lines.append(encoded if len(encoded.encode('utf-8')) < len(plain.encode('utf-8')) else plain)
    return '\n'.join(lines) + '\n'
