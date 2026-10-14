"""Physical compact-source locations, separate from semantic IR and revisions."""
import hashlib
import json
import re

from .schema import MAX_SOURCE_BYTES, require

_ID = r'[A-Za-z][A-Za-z0-9_.:\-]{0,63}'
_FUNCTION = re.compile(r'^\s*fn\s+(' + _ID + r')\s*$')
_NODE = re.compile(r'^\s*(' + _ID + r')\s*=\s*')
_INLINE = re.compile('(' + _ID + r')=(0|-?[1-9][0-9]*)$')


def _inline_positions(line, start):
    """Skip JSON operands, including quoted identifier lookalikes."""
    decoder = json.JSONDecoder()
    cursor = start
    while cursor < len(line):
        if line[cursor].isspace():
            cursor += 1
            continue
        if line[cursor] in '[{"-' or line[cursor].isdigit():
            try:
                _, cursor = decoder.raw_decode(line, cursor)
            except ValueError:
                return
        else:
            end = cursor + 1
            while end < len(line) and not line[end].isspace():
                end += 1
            match = _INLINE.fullmatch(line[cursor:end])
            if match:
                yield match[1], cursor, end
            cursor = end


def index_source(source):
    """Lexical candidates only; callers validate before exposing query results."""
    require(len(source.encode('utf-8')) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
    positions = []
    function = None
    for number, line in enumerate(source.split('\n'), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = _FUNCTION.fullmatch(line)
        if match:
            function = match[1]
            positions.append({'kind':'function', 'function':function, 'id':function,
                              'line':number, 'column':match.start(1)+1, 'end_column':match.end(1)+1})
        elif line.strip() == 'end':
            function = None
        else:
            match = _NODE.match(line)
            if match:
                positions.append({'kind':'node','function':function,'id':match[1],
                                  'line':number,'column':match.start(1)+1,'end_column':match.end(1)+1})
                if function is not None:
                    for name, start, end in _inline_positions(line, match.end()):
                        positions.append({'kind':'inline_constant','function':function,'id':name,
                                          'line':number,'column':start+1,'end_column':end+1})
    return positions


def attach_semantic_location(diagnostic, source, document):
    name = diagnostic.get('node')
    if name is None:
        return
    contracts = document.get('contracts', []) if isinstance(document, dict) else []
    if isinstance(contracts, list) and any(isinstance(c, dict) and c.get('id') == name for c in contracts):
        # Contract IDs occupy a separate namespace; an unqualified ID is insufficient.
        return
    positions = [p for p in index_source(source) if p['id'] == name]
    if len(positions) == 1:
        diagnostic['source_location'] = positions[0]
    elif positions:
        diagnostic['source_candidates'] = positions


def locate_source(source, function_id=None, node_id=None):
    """Validate a compact snapshot and return deterministic qualified locations."""
    from .compact import loads
    from .revision import revision
    require(len(source.encode('utf-8')) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
    first = next((line.strip() for line in source.split('\n') if line.strip() and not line.lstrip().startswith('#')), '')
    require(first.startswith('pact '), 'SOURCE_MAP_UNSUPPORTED',
            'Physical source maps support compact source only; JSON locations are unsupported.')
    document = loads(source)
    positions = index_source(source)
    if function_id is not None:
        require(any(p['kind'] == 'function' and p['id'] == function_id for p in positions),
                'FUNCTION_MISSING', 'Selected function does not exist.')
        positions = [p for p in positions if p['function'] == function_id]
    if node_id is not None:
        positions = [p for p in positions if p['kind'] != 'function' and p['id'] == node_id]
        require(bool(positions), 'NODE_MISSING', 'Selected node does not exist in selected scope.')
    return {'format':'pact.source-map/0.1.0', 'source_format':document['format'],
            'context_only':True, 'buildable':False,
            'source_sha256':hashlib.sha256(source.encode('utf-8')).hexdigest(),
            'semantic_revision_sha256':revision(document),
            'coordinates':'1-based Unicode code points; end_column is exclusive; tabs count as one',
            'selection_ambiguous':node_id is not None and len(positions) > 1,
            'positions':positions}


def locate_file(path, function_id=None, node_id=None):
    """Read one bounded binary snapshot, retaining CRLF and exact byte identity."""
    from pathlib import Path
    from .diagnostics import PactError
    try:
        with Path(path).open('rb') as stream:
            data = stream.read(MAX_SOURCE_BYTES + 1)
        require(len(data) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
        result = locate_source(data.decode('utf-8'), function_id, node_id)
        result['source_path'] = str(path)
        return result
    except PactError:
        raise
    except (OSError, UnicodeError) as error:
        raise PactError('SOURCE_INVALID', str(error)) from None
