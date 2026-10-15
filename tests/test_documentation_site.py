from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


class Structure(HTMLParser):
    def __init__(self,source):
        super().__init__(); self.tags=[];self.links=[];self.classes=[];self.ids=[];self.feed(source)
    def handle_starttag(self,tag,attrs):
        values=dict(attrs);self.tags.append(tag)
        self.classes.extend(values.get('class','').split())
        if tag=='a':self.links.append(values.get('href',''))
        if 'id' in values:self.ids.append(values['id'])


class DocumentationSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result=subprocess.run([sys.executable,'-m','tools.build_site'],cwd=ROOT,capture_output=True,text=True)
        if result.returncode:raise AssertionError(result.stderr)

    def test_markdown_docs_render_semantic_elements_and_internal_links(self):
        source=(ROOT/'site-output/syntax.html').read_text()
        structure=Structure(source)
        self.assertIn('markdown',structure.classes)
        self.assertIn('h2',structure.tags)
        self.assertIn('table',structure.tags)
        self.assertIn('code',structure.tags)
        self.assertIn('compression.html',structure.links)
        self.assertNotIn('<pre># Compact',source)
        self.assertEqual(len(structure.ids),len(set(structure.ids)))

    def test_progress_and_published_document_links_exist(self):
        progress=ROOT/'site-output/progress.html'
        self.assertTrue(progress.exists())
        self.assertIn('markdown',Structure(progress.read_text()).classes)
        for page in (ROOT/'site-output').glob('*.html'):
            for href in Structure(page.read_text()).links:
                target=href.split('#',1)[0].split('?',1)[0]
                if target.endswith('.html') and '://' not in target:
                    self.assertTrue((page.parent/target).exists(),(page.name,href))

    def test_model_game_examples_preserve_original_candidate_bytes(self):
        for name in ('metro_a.html','metro_b.html'):
            self.assertEqual((ROOT/'site-output/metroidvania'/name).read_bytes(),
                             (ROOT/'benchmarks/metroidvania_pilot/candidates'/name).read_bytes())
        self.assertIn('sandbox="allow-scripts"',(ROOT/'site-output/metroidvania/index.html').read_text())
        self.assertIn('16/16',(ROOT/'site-output/metroidvania/index.html').read_text())
