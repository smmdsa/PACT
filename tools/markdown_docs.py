"""Safe, static Markdown for the public docs (optional build dependency)."""
import posixpath
import re
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urlsplit, urlunsplit


REPOSITORY = 'https://github.com/smmdsa/PACT/blob/main/'


def _safe_url(url):
    # Check decoded text too: browsers can interpret encoded slashes differently.
    decoded = unquote(url)
    if any(ord(char) < 32 or ord(char) == 127 for char in decoded):
        return False
    if '\\' in decoded or decoded.startswith('//'):
        return False
    try:
        parts = urlsplit(decoded)
    except ValueError:
        return False
    if parts.scheme:
        if parts.scheme.lower() in ('http', 'https'):
            return bool(parts.netloc)
        return parts.scheme.lower() == 'mailto'
    return not parts.netloc


def _resolve_url(url, source_path, page_map):
    if not _safe_url(url):
        return None
    parts = urlsplit(url)
    if parts.scheme or not parts.path:
        return url
    path = unquote(parts.path)
    if path.startswith('/'):
        path = path.lstrip('/')
    else:
        path = posixpath.join(str(PurePosixPath(source_path).parent), path)
    path = posixpath.normpath(path)
    if path == '..' or path.startswith('../'):
        return None
    target = page_map.get(path, REPOSITORY + quote(path, safe='/'))
    # The publication map is trusted build configuration, but validate its URLs
    # as well so an erroneous entry cannot introduce an executable link.
    if not _safe_url(target):
        return None
    destination = urlsplit(target)
    return urlunsplit((destination.scheme, destination.netloc, destination.path,
                       parts.query or destination.query, parts.fragment or destination.fragment))


def _plain_text(tokens):
    result = []
    for token in tokens:
        if token.type in ('text', 'code_inline'):
            result.append(token.content)
        elif token.type in ('softbreak', 'hardbreak'):
            result.append(' ')
        elif token.type == 'image':
            result.append(_plain_text(token.children or []))
    return ''.join(result)


def render_markdown(text, source_path, page_map):
    """Return rendered HTML and heading metadata for a repository document.

    ``source_path`` is repository-relative; ``page_map`` maps normalized
    repository paths to published URLs, including copied downloadable files.
    Raw HTML is escaped, and only HTTP(S), mailto, or local URLs are accepted.
    """
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise ImportError('Site build requires: python3 -m pip install -r docs/site-requirements.txt') from exc

    parser = MarkdownIt('commonmark', {'html': False}).enable('table')
    parser.validateLink = _safe_url
    tokens = parser.parse(text)
    toc = []
    used_ids = set()
    for index, token in enumerate(tokens):
        if token.type == 'heading_open':
            title = _plain_text(tokens[index + 1].children or [])
            base = re.sub(r'[^\w\s-]', '', title.lower())
            base = re.sub(r'\s+', '-', base.strip()) or 'section'
            heading_id = base
            suffix = 0
            while heading_id in used_ids:
                suffix += 1
                heading_id = f'{base}-{suffix}'
            used_ids.add(heading_id)
            token.attrSet('id', heading_id)
            toc.append({'id': heading_id, 'title': title, 'level': int(token.tag[1:])})
        suppressed_links = []
        for inline in token.children or []:
            if inline.type == 'link_close':
                if suppressed_links.pop():
                    inline.type, inline.tag, inline.nesting = 'text', '', 0
                    inline.content = ''
                continue
            attribute = 'href' if inline.type == 'link_open' else 'src' if inline.type == 'image' else None
            if attribute:
                destination = _resolve_url(inline.attrGet(attribute), source_path, page_map)
                if inline.type == 'link_open':
                    suppressed_links.append(destination is None)
                if destination is None:
                    content = _plain_text(inline.children or []) if inline.type == 'image' else ''
                    inline.type, inline.tag, inline.nesting = 'text', '', 0
                    inline.content = content
                    inline.attrs = {}
                    inline.children = None
                else:
                    inline.attrSet(attribute, destination)
    return parser.renderer.render(tokens, parser.options, {}), toc
