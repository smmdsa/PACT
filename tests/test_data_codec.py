import copy
import json
import tracemalloc
import unittest

from pact.diagnostics import PactError


class DataCodecTests(unittest.TestCase):
    def codec(self):
        try:
            from pact import data_codec
        except ImportError:
            self.fail('Cell codec has not been implemented')
        return data_codec

    @staticmethod
    def cell(values, name='state', mutable=True):
        return {'id': name, 'mutable': mutable, 'values': values}

    def test_roundtrip_mixed_records_preserves_order_and_i32_extremes(self):
        codec = self.codec()
        cells = [self.cell([0] * 128, 'z'),
                 self.cell([-(2**31), 2**31 - 1, 0, -1], 'a', False),
                 self.cell([3] * 40 + [-7] * 40, 'm')]
        original = copy.deepcopy(cells)
        records = codec.encode_cells(cells)
        self.assertIn('runs', records[0])
        self.assertIn('values', records[1])
        self.assertEqual(records[2]['runs'], [[40, 3], [40, -7]])
        self.assertEqual(codec.decode_cells(records), original)
        self.assertEqual(cells, original)

    def test_encoded_and_decoded_lists_are_detached(self):
        codec = self.codec()
        source = [self.cell([1, 2])]
        records = codec.encode_cells(source)
        records[0]['values'][0] = 9
        self.assertEqual(source[0]['values'], [1, 2])
        decoded = codec.decode_cells(records)
        decoded[0]['values'][0] = 8
        self.assertEqual(records[0]['values'], [9, 2])
        runs = [{'id': 'state', 'mutable': False, 'runs': [[3, -4]]}]
        decoded = codec.decode_cells(runs)
        decoded[0]['values'][0] = 5
        self.assertEqual(runs[0]['runs'], [[3, -4]])

    def test_rle_requires_strict_full_record_byte_win(self):
        codec = self.codec()
        size = lambda record: len(json.dumps(record, sort_keys=True,
                                             separators=(',', ':'),
                                             ensure_ascii=False).encode('utf-8'))
        # Two zeros tie exactly: the shorter key offsets the run pair overhead.
        for values in ([0], [0, 0], [0, 0, 0], [0, 0, 0, 0],
                       list(range(100)), [-2147483648] * 2):
            with self.subTest(values=values):
                plain = self.cell(values)
                runs = []
                for value in values:
                    if runs and runs[-1][1] == value:
                        runs[-1][0] += 1
                    else:
                        runs.append([1, value])
                packed = {'id': plain['id'], 'mutable': plain['mutable'], 'runs': runs}
                self.assertEqual(codec.encode_cells([plain])[0],
                                 packed if size(packed) < size(plain) else plain)
        plain = self.cell([0, 0])
        packed = {'id': 'state', 'mutable': True, 'runs': [[2, 0]]}
        self.assertEqual(size(plain), size(packed))
        self.assertEqual(codec.encode_cells([plain]), [plain])

    def test_accepts_exact_cell_and_total_bounds(self):
        codec = self.codec()
        cells = [self.cell([0] * 4096, f'cell{i}') for i in range(4)]
        self.assertEqual(codec.decode_cells(codec.encode_cells(cells)), cells)
        cells = [self.cell([i], f'cell{i}') for i in range(128)]
        self.assertEqual(codec.decode_cells(codec.encode_cells(cells)), cells)

    def test_rejects_invalid_plain_cells_in_both_directions(self):
        codec = self.codec()
        invalid = [None, {}, (), [], [None],
                   [self.cell([])], [self.cell([0] * 4097)],
                   [self.cell([0], f'cell{i}') for i in range(129)],
                   [self.cell([0] * 4096, f'cell{i}') for i in range(5)],
                   [self.cell([0]), self.cell([1])]]
        for value in (True, False, 1.0, '1', None, -(2**31) - 1, 2**31):
            invalid.append([self.cell([value])])
        for name in ('', '1bad', 'a' * 65, '雪', None, True):
            invalid.append([self.cell([0], name)])
        for mutable in (0, 1, 'true', None):
            invalid.append([self.cell([0], mutable=mutable)])
        invalid.extend([[{'id': 'state', 'mutable': True}],
                        [dict(self.cell([0]), extra=0)],
                        [dict(self.cell([0]), runs=[[1, 0]])],
                        [self.cell((1,))]])
        for records in invalid:
            for operation in (codec.encode_cells, codec.decode_cells):
                with self.subTest(records=repr(records)[:100], operation=operation.__name__):
                    with self.assertRaises(PactError):
                        operation(records)

    def test_rejects_invalid_runs(self):
        codec = self.codec()
        invalid = [None, {}, (), [], [1], [[1]], [[1, 0, 2]], [(1, 0)],
                   [[True, 0]], [[False, 0]], [[0, 0]], [[-1, 0]],
                   [[1.0, 0]], [['1', 0]], [[4097, 0]], [[10**100, 0]],
                   [[4096, 0], [1, 1]]]
        for value in (True, False, 1.0, '1', None, -(2**31) - 1, 2**31):
            invalid.append([[1, value]])
        for runs in invalid:
            with self.subTest(runs=runs), self.assertRaises(PactError):
                codec.decode_cells([{'id': 'state', 'mutable': True, 'runs': runs}])

    def test_accepts_adjacent_equal_runs_without_reordering(self):
        codec = self.codec()
        records = [{'id': 'state', 'mutable': False, 'runs': [[2, 7], [1, 7], [1, -3]]}]
        self.assertEqual(codec.decode_cells(records), [self.cell([7, 7, 7, -3], mutable=False)])

    def test_rejects_entire_input_before_expanding_any_record(self):
        codec = self.codec()
        prefix = [{'id': f'cell{i}', 'mutable': True, 'runs': [[4096, 0]]}
                  for i in range(4)]
        bad_tails = [self.cell([0], 'extra'),
                     {'id': 'extra', 'mutable': True, 'runs': [[10**100, 0]]},
                     {'id': 'extra', 'mutable': True, 'runs': [[1, True]]},
                     {'id': 'cell0', 'mutable': True, 'runs': [[1, 0]]}]
        for tail in bad_tails:
            with self.subTest(tail=tail):
                tracemalloc.start()
                try:
                    with self.assertRaises(PactError):
                        codec.decode_cells(prefix + [tail])
                    _, peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
                self.assertLess(peak, 65536, 'Valid prefix was expanded before rejecting the tail')


if __name__ == '__main__':
    unittest.main()
