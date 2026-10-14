"""Compact, reversible syntax for the checked PACT graph and numeric IR."""
import json
import re

from .diagnostics import PactError
from .schema import IDENTIFIER, MAX_SOURCE_BYTES, require

HEADER = 'pact 0.2'
DATA_HEADER = 'pact 0.3'
INLINE_HEADER = 'pact 0.4'
WORD = IDENTIFIER
INLINE_LITERAL = re.compile(r'([A-Za-z][A-Za-z0-9_.:\-]{0,63})=((?:0|-?[1-9][0-9]*))', re.ASCII)
FIELDS = {
    'i32.const': ('value',), 'utf8.literal': ('value',),
    'const.load': ('name',), 'local.get': ('name',),
    'local.set': ('name', 'args'), 'state.load': ('cell', 'args'),
    'state.store': ('cell', 'args'), 'state.reset': ('cells',),
    'flow.repeat': ('count', 'counter', 'args'),
    'call': ('target', 'args'),
}
ALIASES = {'get': 'state.load', 'set': 'state.store', 'reset': 'state.reset',
           'add.wrap': 'i32.add_wrap', 'sub.wrap': 'i32.sub_wrap',
           'mul.wrap': 'i32.mul_wrap', 'seq': 'flow.sequence', 'if': 'flow.if'}
SHORT = {value: key for key, value in ALIASES.items()}
FUNCTION_FIELDS = ('params', 'locals', 'result', 'writes')


def validate_document(document):
    from .graph import analyze
    from .module import FORMATS, analyze_module
    if isinstance(document, dict) and document.get('format') in FORMATS:
        return analyze_module(document)
    return analyze(document)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'COMPACT_INVALID', f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _values(text, allow_inline=False):
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
            if allow_inline and '=' in value:
                match = INLINE_LITERAL.fullmatch(value)
                require(match is not None, 'COMPACT_INVALID', 'Invalid inline literal.')
                const_id, raw_int = match.group(1), int(match.group(2))
                require(-(2**31) <= raw_int < 2**31, 'INTEGER_INVALID', 'Expected signed i32.')
                values.append(('inline_const', const_id, raw_int))
            else:
                require(bool(WORD.fullmatch(value)), 'COMPACT_INVALID', 'Invalid operand.')
                values.append(value)
            cursor = end
    return values


def _schema(op):
    from .module import OPERATIONS
    require(op in OPERATIONS or op in {'utf8.literal', 'utf8.concat', 'stdout.emit', 'effect.sequence'},
            'COMPACT_INVALID', f'Unknown operation: {op}')
    return FIELDS.get(op, ('args',))


def _node(line, allow_inline=False):
    name, expression = line.split('=', 1)
    name = name.strip()
    require(bool(WORD.fullmatch(name)), 'COMPACT_INVALID', 'Invalid node ID.')
    expression = expression.strip()
    if allow_inline and expression and (expression[0] in '-"' or expression[0].isdigit()):
        values = _values(expression)
        require(len(values) == 1, 'COMPACT_INVALID', 'Expected one literal value.')
        value = values[0]
        require(type(value) is int or isinstance(value, str), 'COMPACT_INVALID', 'Expected i32 or UTF-8 literal.')
        if type(value) is int:
            require(-2147483648 <= value <= 2147483647, 'COMPACT_INVALID', 'Literal exceeds signed i32.')
            require(expression == str(value), 'COMPACT_INVALID', 'Expected canonical integer.')
        node = {'id': name, 'op': 'i32.const' if type(value) is int else 'utf8.literal', 'value': value}
        return [], node
    parts = expression.strip().split(maxsplit=1)
    require(bool(parts), 'COMPACT_INVALID', 'Missing operation.')
    op = ALIASES.get(parts[0], parts[0])
    fields = _schema(op)
    values = _values(parts[1] if len(parts) > 1 else '', allow_inline=allow_inline)
    fixed = len(fields) - ('args' in fields)
    require(len(values) >= fixed, 'COMPACT_INVALID', 'Missing operands.')
    node = {'id': name, 'op': op}
    for key, value in zip(fields[:fixed], values[:fixed]):
        require(not (isinstance(value, tuple) and value[0] == 'inline_const'),
                'COMPACT_INVALID', 'Inline literals are permitted in args only.')
        node[key] = value
    inline_nodes = []
    if 'args' in fields:
        tail = values[fixed:]
        if tail == [[]]:
            node['args'] = []
        else:
            args = []
            for item in tail:
                if isinstance(item, tuple) and item[0] == 'inline_const':
                    _, const_id, raw_int = item
                    inline_nodes.append({'id': const_id, 'op': 'i32.const', 'value': raw_int})
                    args.append(const_id)
                else:
                    args.append(item)
            node['args'] = args
    else:
        require(len(values) == fixed, 'COMPACT_INVALID', 'Unexpected operands.')
    return (inline_nodes, node) if allow_inline else node


def loads(source, migrate_legacy=False):
    """Parse and validate; never evaluate source as host code."""
    line_number = 1
    validating = False
    try:
        require(len(source.encode('utf-8')) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
        lines = [(n, line.strip()) for n, line in enumerate(source.split('\n'), 1)
                 if line.strip() and not line.lstrip().startswith('#')]
        line_number = lines[0][0] if lines else 1
        require(bool(lines) and lines[0][1] in (HEADER, DATA_HEADER, INLINE_HEADER),
                'COMPACT_INVALID', 'Expected pact 0.2, pact 0.3 or pact 0.4 header.')
        data_version = lines[0][1] in (DATA_HEADER, INLINE_HEADER)
        inline_version = lines[0][1] == INLINE_HEADER
        packed_sections = False
        inline_literals = False
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
                if inline_version:
                    inline_nodes, node = _node(line, allow_inline=True)
                    inline_literals = inline_literals or bool(inline_nodes)
                else:
                    inline_nodes, node = [], _node(line)
                target = function if function is not None else document
                for inl in inline_nodes:
                    require(inl['id'] not in ids, 'COMPACT_INVALID', 'Duplicate node ID.')
                    ids.add(inl['id'])
                    target.setdefault('nodes', []).append(inl)
                require(node['id'] not in ids, 'COMPACT_INVALID', 'Duplicate node ID.')
                ids.add(node['id'])
                target.setdefault('nodes', []).append(node)
            else:
                key, separator, value = line.partition(' ')
                require(bool(separator), 'COMPACT_INVALID', 'Expected section and JSON value.')
                packed = key in ('cells.packed', 'assets.shared')
                if packed:
                    require(data_version and function is None, 'COMPACT_INVALID', 'Compressed sections require module-level pact 0.3 or pact 0.4.')
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
        validating = True
        from .module import FORMATS, migrate_module
        require(not packed_sections or document.get('format') in FORMATS,
                'COMPACT_INVALID', 'Compressed sections support numeric modules only.')
        require(not inline_literals or document.get('format') in FORMATS,
                'COMPACT_INVALID', 'Inline literals require a numeric module.')
        if migrate_legacy and document.get('format') == FORMATS[0]:
            document = migrate_module(document)
        validate_document(document)
        return document
    except (ValueError, RecursionError) as error:
        if isinstance(error, PactError):
            if validating:
                from .source_locations import attach_semantic_location
                attach_semantic_location(error.diagnostic, source, document)
            elif error.diagnostic['code'] != 'SOURCE_LIMIT':
                error.diagnostic['source_location'] = {'line':line_number, 'column':1}
            raise
        rejection = PactError('COMPACT_INVALID', f'Line {line_number}: {error}')
        rejection.diagnostic['source_location'] = {'line':line_number, 'column':1}
        raise rejection from None


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _operand(value, literal=False):
    return value if isinstance(value, str) and WORD.fullmatch(value) and not literal else _json(value)


def _emit_node(node, inlined=None, literals=False):
    if literals and node['op'] in ('i32.const', 'utf8.literal'):
        return f"{node['id']} = {_json(node['value'])}"
    fields = _schema(node['op'])
    operands = []
    for field in fields:
        value = node[field]
        if field == 'args':
            operands.extend(inlined[ref] if inlined and ref in inlined else _operand(ref) for ref in value)
            if not value:
                operands.append('[]')
        else:
            operands.append(_operand(value, field == 'value'))
    return f"{node['id']} = {SHORT.get(node['op'], node['op'])}" + (' ' + ' '.join(operands) if operands else '')


def _emit_function_nodes(function, inline=False, literals=False):
    nodes = function['nodes']
    if not inline:
        return [_emit_node(node, literals=literals) for node in nodes]
    refs = {}
    for node in nodes:
        for ref in node.get('args', []):
            refs[ref] = refs.get(ref, 0) + 1
    refs[function['entry']] = refs.get(function['entry'], 0) + 1
    inlined_map, skip_ids = {}, set()
    index = 0
    while index < len(nodes):
        run = []
        cursor = index
        while (cursor < len(nodes) and nodes[cursor]['op'] == 'i32.const'
               and refs.get(nodes[cursor]['id'], 0) == 1):
            run.append(nodes[cursor])
            cursor += 1
        if run and cursor < len(nodes) and 'args' in _schema(nodes[cursor]['op']):
            consumer = nodes[cursor]
            run_ids = [item['id'] for item in run]
            run_set = set(run_ids)
            c_args = [arg for arg in consumer.get('args', []) if arg in run_set]
            if c_args and len(c_args) == len(set(c_args)) and c_args == run_ids[-len(c_args):]:
                for item in run[-len(c_args):]:
                    inlined_map[item['id']] = f"{item['id']}={item['value']}"
                    skip_ids.add(item['id'])
                index = cursor + 1
                continue
        index += 1
    return [_emit_node(node, inlined_map, literals=literals) for node in nodes if node['id'] not in skip_ids]


def dumps(document, compressed=False, inline=False, literals=False):
    """Serialize validated IR; canonical formatting preserves all semantic fields."""
    validate_document(document)
    if inline:
        compressed = True
    header = INLINE_HEADER if inline or literals else (DATA_HEADER if compressed else HEADER)
    lines = [header]
    for key, value in document.items():
        if key == 'nodes':
            lines.extend(_emit_node(node, literals=literals) for node in value)
        elif key == 'functions':
            for function in value:
                lines.append('fn ' + function['id'])
                lines.extend(key + ' ' + _json(function[key]) for key in FUNCTION_FIELDS)
                lines.extend(_emit_function_nodes(function, inline=inline, literals=literals))
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
