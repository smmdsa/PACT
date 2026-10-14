import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pact.diagnostics import PactError
from pact.graph import analyze, load_document
from pact.module import analyze_module
from pact.module_wasm import compile_module
from pact.wasm import compile_plan

ROOT = Path(__file__).resolve().parents[1]


class CompactTests(unittest.TestCase):
    def frontend(self):
        try:
            from pact import compact
        except ImportError:
            self.fail('Compact frontend has not been implemented')
        return compact

    def test_examples_roundtrip_without_semantic_changes(self):
        compact = self.frontend()
        for name in ('hello', 'alien-harvest'):
            with self.subTest(name=name):
                doc = json.loads((ROOT/f'examples/{name}.pact.json').read_text())
                source = compact.dumps(doc)
                restored = compact.loads(source)
                self.assertEqual(restored, doc)
                compiler, analyzer = (compile_module, analyze_module) if 'functions' in doc else (compile_plan, analyze)
                self.assertEqual(compiler(analyzer(doc)), compiler(analyzer(restored)))

    def test_rejects_ambiguous_structure(self):
        compact = self.frontend()
        good = compact.dumps(json.loads((ROOT/'examples/hello.pact.json').read_text()))
        for source in ('pact 9\n', good+'format "other"\n', good+'bad = unknown 1\n',
                       good+'fn broken\n', good+'return x\n', good+'end\n',
                       good+'extra = utf8.literal "a" "b"\n',
                       good+'extra = utf8.literal "x"\nextra = utf8.literal "y"\n',
                       good+'extra = utf8.literal {"x":1,"x":2}\n'):
            with self.subTest(source=source[-80:]), self.assertRaises(PactError):
                compact.loads(source)

    def test_quoted_values_and_comment_lines(self):
        compact = self.frontend()
        doc = json.loads((ROOT/'examples/hello.pact.json').read_text())
        doc['nodes'][0]['value'] = 'a = b # c "quoted"\n雪'
        doc['contracts'][0]['value'] = doc['nodes'][0]['value'] + doc['nodes'][1]['value']
        source = compact.dumps(doc)
        self.assertEqual(compact.loads('# rationale\n'+source+'# trailing\n'), doc)

    def test_cli_convert_and_build(self):
        self.frontend()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'hello.pact'
            for args in (['convert',str(ROOT/'examples/hello.pact.json'),'-o',str(target),'--to','compact'],
                         ['build',str(target),'-o',str(Path(tmp)/'hello.wasm')]):
                result = subprocess.run([sys.executable,'-m','pact',*args],cwd=ROOT,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            result = subprocess.run(['node','host/run.mjs',str(Path(tmp)/'hello.wasm'),'--allow','stdout'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('alien', result.stdout)

    def test_all_valid_identifier_separators_roundtrip(self):
        compact = self.frontend()
        doc = json.loads((ROOT/'examples/hello.pact.json').read_text())
        doc['nodes'][0]['id'] = 'value:0'
        doc['nodes'][2]['args'][0] = 'value:0'
        self.assertEqual(compact.loads(compact.dumps(doc)), doc)
        from tests.test_module import tiny
        numeric = tiny()
        numeric['format'] = 'pact.module/0.2.0'
        numeric['functions'][0]['id'] = 'game:step'
        numeric['exports'][0] = 'game:step'
        self.assertEqual(compact.loads(compact.dumps(numeric)), numeric)
        legacy = tiny()
        self.assertEqual(compact.loads(compact.dumps(legacy)), legacy)

    def test_legacy_module_json_and_compact_load_to_same_ir(self):
        compact = self.frontend()
        from pact.revision import revision
        from tests.test_module import tiny
        legacy = tiny()
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp)/'legacy.json'
            compact_path = Path(tmp)/'legacy.pact'
            json_path.write_text(json.dumps(legacy), encoding='utf-8')
            compact_path.write_text(compact.dumps(legacy), encoding='utf-8')
            json_document = load_document(json_path)
            compact_document = load_document(compact_path)
        expected = legacy
        self.assertEqual(json_document, expected)
        self.assertEqual(compact_document, expected)
        self.assertEqual(revision(json_document), revision(compact_document))

    def test_unicode_separators_inside_json_are_not_source_lines(self):
        compact = self.frontend()
        for separator in ('\u2028', '\u2029', '\u0085'):
            doc = json.loads((ROOT/'examples/hello.pact.json').read_text())
            doc['nodes'][0]['value'] = 'before'+separator+'after'
            doc['contracts'][0]['value'] = doc['nodes'][0]['value']+doc['nodes'][1]['value']
            self.assertEqual(compact.loads(compact.dumps(doc)), doc)
        game = json.loads((ROOT/'examples/alien-harvest.pact.json').read_text())
        game['presentation']['title'] = 'Metadata\u2028with\u0085separators'
        self.assertEqual(compact.loads(compact.dumps(game)), game)
