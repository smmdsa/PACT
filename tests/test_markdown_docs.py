import unittest
from html.parser import HTMLParser
from pathlib import Path

from tools.markdown_docs import render_markdown


ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.urls.extend(value for name, value in attrs if name in ('href', 'src'))


class MarkdownDocsTests(unittest.TestCase):
    def test_renders_markdown_structure_and_escaped_code(self):
        text = '# Guide\n\nA **bold** and *emphasized* `value`.\n\n- first\n- second\n\n1. ordered\n\n| Name | Value |\n| --- | --- |\n| cell | 42 |\n\n```pact\n<script>& value\n```\n'
        rendered, toc = render_markdown(text, 'docs/guide.md', {})
        for expected in ('<h1 id="guide">Guide</h1>', '<p>A <strong>bold</strong>', '<em>emphasized</em>', '<code>value</code>', '<ul>', '<ol>', '<table>', '<th>Name</th>', '<td>42</td>', '<pre><code class="language-pact">&lt;script&gt;&amp; value'):
            self.assertIn(expected, rendered)
        self.assertEqual(toc, [{'id': 'guide', 'title': 'Guide', 'level': 1}])
        self.assertFalse(rendered.startswith('<pre>'))

    def test_heading_ids_are_unique_and_stable_with_inline_markup(self):
        text = '# Hello *world*\n## Hello world\n## Hello world-1\n## Hello world\n## !!!\n## !!!\n'
        rendered, toc = render_markdown(text, 'README.md', {})
        self.assertEqual([item['id'] for item in toc], ['hello-world', 'hello-world-1', 'hello-world-1-1', 'hello-world-2', 'section', 'section-1'])
        self.assertEqual(toc[0]['title'], 'Hello world')
        self.assertEqual(render_markdown(text, 'README.md', {}), (rendered, toc))

    def test_rewrites_published_pages_downloads_and_repository_fallback(self):
        text = '[syntax](./syntax.md#compact-source-02) [roadmap](../ROADMAP.md) [report](../benchmarks/report.json?raw=1#data) [source](../examples/hello.pact) [unknown](../pact/compact.py#L1) [anchor](#same) [web](https://example.com/a?b=1&c=2#d) [email](mailto:test@example.com)'
        mapping = {'docs/syntax.md': 'syntax.html', 'ROADMAP.md': 'roadmap.html', 'benchmarks/report.json': 'downloads/report.json', 'examples/hello.pact': 'hello.pact'}
        rendered, _ = render_markdown(text, 'docs/guide.md', mapping)
        self.assertEqual(Links(rendered).urls, ['syntax.html#compact-source-02', 'roadmap.html', 'downloads/report.json?raw=1#data', 'hello.pact', 'https://github.com/smmdsa/PACT/blob/main/pact/compact.py#L1', '#same', 'https://example.com/a?b=1&c=2#d', 'mailto:test@example.com'])

    def test_blocks_raw_html_and_unsafe_links_and_images(self):
        text = '<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n'
        unsafe = ['javascript:alert%281%29', 'JaVaScRiPt:alert%281%29', 'data:text/html,test', 'data:image/png;base64,AA', 'vbscript:evil', 'file:///etc/passwd', '//evil.test/path', '%5C%5Cevil.test/path', '/%5Cevil.test/path', 'https:%5C%5Cevil.test/path', 'https://safe.test/%5Cevil', 'ftp://evil.test', '../../../outside.md']
        text += '\n\n'.join(f'[bad]({url}) ![bad]({url})' for url in unsafe)
        rendered, _ = render_markdown(text, 'docs/guide.md', {})
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img ', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertEqual(Links(rendered).urls, [])

    def test_renders_real_repository_document(self):
        rendered, toc = render_markdown((ROOT / 'docs/syntax.md').read_text(), 'docs/syntax.md', {})
        self.assertIn('<table>', rendered)
        self.assertIn('<pre><code class="language-text">', rendered)
        self.assertGreater(len(toc), 0)
        self.assertNotIn('<pre># Compact', rendered)


if __name__ == '__main__':
    unittest.main()
