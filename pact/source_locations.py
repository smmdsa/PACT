"""Physical source locations, separate from semantic IR and revisions."""
from bisect import bisect_right
import hashlib
import json
import re

from .schema import MAX_SOURCE_BYTES, require
from .diagnostics import PactError

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


def _json_entries(source, start):
    """Walk one validated container; skip unrelated values without descending."""
    decoder = json.JSONDecoder()
    is_object = source[start] == '{'
    end_token = '}' if is_object else ']'
    cursor, index = start + 1, 0
    while True:
        while source[cursor] in ' \t\r\n':
            cursor += 1
        if source[cursor] == end_token:
            return
        key = index
        if is_object:
            key, cursor = decoder.raw_decode(source, cursor)
            while source[cursor] in ' \t\r\n:':
                cursor += 1
        value_start = cursor
        value, cursor = decoder.raw_decode(source, cursor)
        yield key, value, value_start, cursor
        index += 1
        while source[cursor] in ' \t\r\n':
            cursor += 1
        if source[cursor] == ',':
            cursor += 1


def index_json_source(source):
    """Index definition ID values only, including their quotes and escapes."""
    line_starts = [0] + [match.end() for match in re.finditer('\n', source)]
    positions = []

    def definition(kind, function, name, start, end):
        line = bisect_right(line_starts, start)
        positions.append({'kind':kind, 'function':function, 'id':name, 'line':line,
                          'column':start-line_starts[line-1]+1,
                          'end_column':end-line_starts[line-1]+1})

    def nodes(start, function):
        for _, _, node_start, _ in _json_entries(source, start):
            for key, value, begin, end in _json_entries(source, node_start):
                if key == 'id':
                    definition('node', function, value, begin, end)

    for key, _, start, _ in _json_entries(source, len(source)-len(source.lstrip())):
        if key == 'nodes':
            nodes(start, None)
        elif key == 'functions':
            for _, function, fn_start, _ in _json_entries(source, start):
                for field, value, begin, end in _json_entries(source, fn_start):
                    if field == 'id':
                        definition('function', function['id'], value, begin, end)
                    elif field == 'nodes':
                        nodes(begin, function['id'])
    return sorted(positions, key=lambda p:(p['line'], p['column']))


def locate_source(source, function_id=None, node_id=None):
    """Validate one snapshot and return deterministic qualified locations."""
    from .compact import loads, validate_document
    from .graph import _unique_pairs
    from .revision import revision
    require(len(source.encode('utf-8')) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
    first = next((line.strip() for line in source.split('\n') if line.strip() and not line.lstrip().startswith('#')), '')
    if first.startswith('pact '):
        document = loads(source)
        positions = index_source(source)
    else:
        try:
            document = json.loads(source, object_pairs_hook=_unique_pairs)
        except PactError:
            raise
        except (ValueError, RecursionError) as error:
            raise PactError('SOURCE_INVALID', str(error)) from None
        validate_document(document)
        positions = index_json_source(source)
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
