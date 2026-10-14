import importlib
import sys
import unittest


class BoundedProcessTests(unittest.TestCase):
    def module(self):
        try:return importlib.import_module('benchmarks.bounded_process')
        except ImportError:self.fail('Bounded streaming subprocess capture is missing')

    def test_captures_separate_streams_and_input(self):
        result=self.module().run_bounded([sys.executable,'-c',
            'import sys;sys.stdout.buffer.write(sys.stdin.buffer.read());sys.stderr.write("err")'],b'data',timeout=5,limit=1024)
        self.assertEqual(result['stdout'],b'data');self.assertEqual(result['stderr'],b'err')
        self.assertFalse(result['output_limited']);self.assertFalse(result['timed_out'])

    def test_output_flood_is_killed_and_capture_is_bounded(self):
        result=self.module().run_bounded([sys.executable,'-c',
            'import os\nwhile True: os.write(1,b"x"*4096)'],b'',timeout=5,limit=8192)
        self.assertTrue(result['output_limited'])
        self.assertLessEqual(len(result['stdout'])+len(result['stderr']),8192)

    def test_timeout_preserves_partial_output(self):
        result=self.module().run_bounded([sys.executable,'-c',
            'import os,time;os.write(1,b"start");time.sleep(10)'],b'',timeout=1,limit=1024)
        self.assertTrue(result['timed_out']);self.assertEqual(result['stdout'],b'start')
