"""Reversible shared symbol maps; palette and pixel semantics stay in module.py."""

import copy
import json

from .diagnostics import PactError
from .schema import closed_record, identifier, require

MAX_TILES = 128
MAX_TABLES = 128
MAX_TABLE_SYMBOLS = 64


def _canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8')
    except UnicodeEncodeError:
        raise PactError('UTF8_INVALID', 'Assets contain an invalid Unicode surrogate.') from None
    except (TypeError, ValueError, RecursionError):
        raise PactError('ASSET_INVALID', 'Assets must contain finite JSON data.') from None


def _symbols(value, shared=False):
    require(isinstance(value, dict), 'ASSET_INVALID', 'Expected a symbol mapping.')
    if shared:
        require(len(value) <= MAX_TABLE_SYMBOLS, 'ASSET_INVALID', 'At most 64 shared symbols.')
    for key, color in value.items():
        require(isinstance(key, str) and len(key) == 1, 'ASSET_INVALID', 'Symbols are single characters.')
        if color is not None:
            identifier(color)


def _palettes(value):
    require(isinstance(value, list), 'ASSET_INVALID', 'Expected a palette list.')
    seen = set()
    for palette in value:
        closed_record(palette, {'id', 'colors'})
        identifier(palette['id'])
        require(palette['id'] not in seen, 'ID_DUPLICATE', 'Duplicate palette ID.')
        seen.add(palette['id'])
        require(isinstance(palette['colors'], dict), 'ASSET_INVALID', 'Expected palette colors.')
        for name, color in palette['colors'].items():
            identifier(name)
            require(isinstance(color, str), 'ASSET_INVALID', 'Expected color text.')


def _tiles(value, tables=None):
    require(isinstance(value, list) and len(value) <= MAX_TILES,
            'ASSET_INVALID', 'Expected at most 128 tiles.')
    seen = set()
    for tile in value:
        require(isinstance(tile, dict), 'ASSET_INVALID', 'Expected a tile record.')
        reference = tables is not None and 'symbol_table' in tile
        closed_record(tile, {'id', 'palette', 'pixels', 'symbol_table' if reference else 'symbols'})
        identifier(tile['id'])
        require(tile['id'] not in seen, 'ID_DUPLICATE', 'Duplicate tile ID.')
        seen.add(tile['id'])
        identifier(tile['palette'])
        rows = tile['pixels']
        require(isinstance(rows, list) and len(rows) == 8 and
                all(isinstance(row, str) and len(row) == 8 for row in rows),
                'ASSET_INVALID', 'Tiles are exactly 8x8.')
        if reference:
            index = tile['symbol_table']
            require(type(index) is int and 0 <= index < len(tables),
                    'ASSET_INVALID', 'Invalid symbol table reference.')
        else:
            _symbols(tile['symbols'])


def decode_assets(record):
    """Validate compressed structure before copying into the existing asset IR."""
    closed_record(record, {'palettes', 'symbol_tables', 'tiles'})
    tables = record['symbol_tables']
    require(isinstance(tables, list) and len(tables) <= MAX_TABLES,
            'ASSET_INVALID', 'Expected at most 128 symbol tables.')
    for table in tables:
        _symbols(table, shared=True)
    _palettes(record['palettes'])
    _tiles(record['tiles'], tables)
    _canonical(record)
    result = {'palettes': copy.deepcopy(record['palettes']), 'tiles': []}
    for tile in record['tiles']:
        restored = copy.deepcopy(tile)
        if 'symbol_table' in restored:
            restored['symbols'] = copy.deepcopy(tables[restored.pop('symbol_table')])
        result['tiles'].append(restored)
    return result


def encode_assets(assets):
    """Share identical bounded maps only when complete canonical JSON shrinks.

    Large maps remain inline for compatibility with existing valid metadata.
    Tables and tiles follow first-occurrence and original tile ordering.
    """
    closed_record(assets, {'palettes', 'tiles'})
    _palettes(assets['palettes'])
    _tiles(assets['tiles'])
    cost = len(_canonical(assets))
    result = {'palettes': copy.deepcopy(assets['palettes']), 'symbol_tables': [],
              'tiles': copy.deepcopy(assets['tiles'])}
    groups = {}
    for index, tile in enumerate(assets['tiles']):
        if len(tile['symbols']) <= MAX_TABLE_SYMBOLS:
            groups.setdefault(_canonical(tile['symbols']), []).append(index)
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        candidate = copy.deepcopy(result)
        table_index = len(candidate['symbol_tables'])
        candidate['symbol_tables'].append(copy.deepcopy(assets['tiles'][indexes[0]]['symbols']))
        for index in indexes:
            tile = candidate['tiles'][index]
            del tile['symbols']
            tile['symbol_table'] = table_index
        candidate_cost = len(_canonical(candidate))
        if candidate_cost < cost:
            result, cost = candidate, candidate_cost
    return result
