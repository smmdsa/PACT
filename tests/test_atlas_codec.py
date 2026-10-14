import copy
import json
import unittest

from pact.diagnostics import PactError


def assets(maps):
    return {'palettes': [{'id': 'p', 'colors': {'red': '#ff0000', 'blue': '#0000ff'}}],
            'tiles': [{'id': 't' + str(i), 'palette': 'p', 'symbols': symbols,
                       'pixels': ['.' * 8] * 8} for i, symbols in enumerate(maps)]}


def size(value):
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode('utf-8'))


class AtlasCodecTests(unittest.TestCase):
    def codec(self):
        try:
            from pact import atlas_codec
        except ImportError:
            self.fail('Atlas codec has not been implemented')
        return atlas_codec

    def test_mixed_roundtrip_and_isolated_copies(self):
        codec = self.codec()
        shared = {'.': None, **{chr(65 + i): 'red' for i in range(20)}}
        original = assets([shared, {'.': 'blue'}, copy.deepcopy(shared)])
        saved = copy.deepcopy(original)
        encoded = codec.encode_assets(original)
        self.assertEqual(encoded['symbol_tables'], [shared])
        self.assertEqual([tile.get('symbol_table') for tile in encoded['tiles']], [0, None, 0])
        self.assertLess(size(encoded), size(original))
        restored = codec.decode_assets(encoded)
        self.assertEqual(restored, original)
        restored['tiles'][0]['symbols']['.'] = 'red'
        restored['palettes'][0]['colors']['red'] = '#ffffff'
        self.assertEqual(encoded['symbol_tables'][0]['.'], None)
        self.assertEqual(restored['tiles'][2]['symbols']['.'], None)
        self.assertEqual(original, saved)

    def test_small_maps_and_different_maps_stay_inline(self):
        codec = self.codec()
        original = assets([{'.': None}, {'.': None}, {'.': 'red'}])
        encoded = codec.encode_assets(original)
        self.assertEqual(encoded['symbol_tables'], [])
        self.assertTrue(all('symbols' in tile for tile in encoded['tiles']))
        self.assertEqual(codec.decode_assets(encoded), original)

    def test_unicode_cost_and_mapping_identity(self):
        codec = self.codec()
        mapping = {chr(0x4e00 + i): 'red' for i in range(20)}
        mapping['.'] = None
        original = assets([mapping, dict(reversed(list(mapping.items()))), {'.': 'blue'}])
        encoded = codec.encode_assets(original)
        self.assertEqual(len(encoded['symbol_tables']), 1)
        self.assertLess(size(encoded), size(original))
        self.assertEqual(codec.decode_assets(encoded), original)

    def test_large_valid_maps_remain_inline(self):
        codec = self.codec()
        mapping = {chr(0x4e00 + i): 'red' for i in range(5000)}
        mapping['.'] = None
        original = assets([mapping, copy.deepcopy(mapping)])
        encoded = codec.encode_assets(original)
        self.assertEqual(encoded['symbol_tables'], [])
        self.assertEqual(codec.decode_assets(encoded), original)

    def test_rejects_bad_references_records_ids_and_maps(self):
        codec = self.codec()
        good = {'palettes': [], 'symbol_tables': [{'.': None}],
                'tiles': [{'id': 't', 'palette': 'p', 'pixels': ['.' * 8] * 8, 'symbol_table': 0}]}
        cases = []
        for ref in (True, False, -1, 1, '0', None, 0.0):
            case = copy.deepcopy(good)
            case['tiles'][0]['symbol_table'] = ref
            cases.append(case)
        for field in ('symbol_table', 'id', 'palette', 'pixels'):
            case = copy.deepcopy(good)
            del case['tiles'][0][field]
            cases.append(case)
        case = copy.deepcopy(good)
        case['tiles'][0]['symbols'] = {'.': None}
        cases.append(case)
        case = copy.deepcopy(good)
        case['tiles'].append(copy.deepcopy(case['tiles'][0]))
        cases.append(case)
        for mapping in ({'ab': None}, {'.': True}, {'.': 4}, {'.': []}, {'.': 'bad color'}, None):
            case = copy.deepcopy(good)
            case['symbol_tables'] = [mapping]
            cases.append(case)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(PactError):
                codec.decode_assets(case)

    def test_bounds_and_palette_shape(self):
        codec = self.codec()
        good = codec.encode_assets(assets([{'.': None}]))
        cases = []
        for field in ('tiles', 'symbol_tables'):
            case = copy.deepcopy(good)
            case[field] = [copy.deepcopy(case[field][0] if case[field] else {'.': None})] * 129
            cases.append(case)
        for palettes in (None, {}, [{'id': 'p', 'colors': {}}, {'id': 'p', 'colors': {}}]):
            case = copy.deepcopy(good)
            case['palettes'] = palettes
            cases.append(case)
        case = copy.deepcopy(good)
        case['symbol_tables'] = [{chr(i): None for i in range(4097)}]
        cases.append(case)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(PactError):
                codec.decode_assets(case)


if __name__ == '__main__':
    unittest.main()
