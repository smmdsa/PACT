"""Bounded, reversible cell data representation for compact source 0.3."""

import json

from .schema import closed_record, identifier, require

MAX_CELLS = 128
MAX_CELL_VALUES = 4096
MAX_STATE_VALUES = 16384


def _integer(value):
    require(type(value) is int and -(2**31) <= value < 2**31,
            'INTEGER_INVALID', 'Expected signed i32.')


def _validate_cells(records, *, packed):
    """Preflight every record and its extent without expanding any run."""
    require(isinstance(records, list) and 1 <= len(records) <= MAX_CELLS,
            'SCHEMA_INVALID', 'Expected 1..128 cells.')
    identifiers = set()
    total = 0
    for record in records:
        require(isinstance(record, dict), 'SCHEMA_INVALID', 'A cell must be a record.')
        field = 'runs' if packed and 'runs' in record else 'values'
        closed_record(record, {'id', 'mutable', field})
        identifier(record['id'])
        require(record['id'] not in identifiers, 'ID_DUPLICATE', 'Duplicate cell.')
        identifiers.add(record['id'])
        require(type(record['mutable']) is bool, 'SCHEMA_INVALID', 'Cell mutable must be boolean.')
        data = record[field]
        require(isinstance(data, list) and 1 <= len(data) <= MAX_CELL_VALUES,
                'SCHEMA_INVALID', 'Invalid cell extent.')
        if field == 'values':
            count = len(data)
            for value in data:
                _integer(value)
        else:
            count = 0
            for run in data:
                require(isinstance(run, list) and len(run) == 2,
                        'SCHEMA_INVALID', 'A run must be [positive_count, i32_value].')
                extent, value = run
                require(type(extent) is int and 1 <= extent <= MAX_CELL_VALUES,
                        'SCHEMA_INVALID', 'Run count must be an integer in 1..4096.')
                _integer(value)
                count += extent
                require(count <= MAX_CELL_VALUES, 'SCHEMA_INVALID', 'Invalid cell extent.')
        total += count
        require(total <= MAX_STATE_VALUES, 'MEMORY_LIMIT', 'State exceeds one page.')


def _record_size(record):
    return len(json.dumps(record, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False).encode('utf-8'))


def encode_cells(cells):
    """Copy ordinary cells, choosing RLE only for a strict full-record byte win."""
    _validate_cells(cells, packed=False)
    records = []
    for cell in cells:
        plain = {'id': cell['id'], 'mutable': cell['mutable'], 'values': list(cell['values'])}
        runs = []
        for value in cell['values']:
            if runs and runs[-1][1] == value:
                runs[-1][0] += 1
            else:
                runs.append([1, value])
        packed = {'id': cell['id'], 'mutable': cell['mutable'], 'runs': runs}
        records.append(packed if _record_size(packed) < _record_size(plain) else plain)
    return records


def decode_cells(records):
    """Reconstruct detached ordinary cells after validating all packed input."""
    _validate_cells(records, packed=True)
    cells = []
    for record in records:
        if 'values' in record:
            values = list(record['values'])
        else:
            values = []
            for count, value in record['runs']:
                values.extend([value] * count)
        cells.append({'id': record['id'], 'mutable': record['mutable'], 'values': values})
    return cells
