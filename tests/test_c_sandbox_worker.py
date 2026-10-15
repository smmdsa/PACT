from pathlib import Path
import unittest

from benchmarks.sandbox import c_worker


class CWorkerTests(unittest.TestCase):
    def test_render_uses_only_bounded_i32_arguments(self):
        template=(Path(__file__).resolve().parents[1]/'benchmarks/sandbox/c_driver.c').read_text()
        request={'cases':[[0,-2147483648],[1,2147483647]],'reset_args':[0,1]}
        rendered=c_worker.render_driver(template,request)
        self.assertIn('{0,-2147483648},{1,2147483647}',rendered)
        self.assertNotIn('@CASES@',rendered)
        self.assertIn('reset_args[2] = {0,1}',rendered)
        for cases in ([],[[True,1]],[[0,2147483648]],[[0,'1;bad()']],[[0,1,2]],[[0,1]]*101):
            with self.assertRaises(ValueError):
                c_worker.render_driver(template,dict(request,cases=cases))
        with self.assertRaises(ValueError):
            c_worker.render_driver(template,dict(request,reset_args=[0]))

    def test_compiler_flags_and_paths_are_fixed(self):
        command=c_worker.compile_command()
        self.assertEqual(command,['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
            '/tmp/candidate.c','/tmp/driver.c','-o','/tmp/counter'])
