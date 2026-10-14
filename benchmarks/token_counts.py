"""Count exact, equivalent source representations using an optional tokenizer."""

import argparse
import hashlib
import importlib
from importlib import metadata
import json
from pathlib import Path
import sys

from pact.compact import loads, validate_document
from pact.diagnostics import PactError
from pact.graph import _unique_pairs, load_document
from pact.schema import MAX_SOURCE_BYTES, require

TIKTOKEN_VERSION = '0.12.0'
ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ('hello', 'alien-harvest')


class BenchmarkError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def load_tokenizer(name):
    try:
        tokenizer = importlib.import_module('tiktoken')
        version = metadata.version('tiktoken')
    except (ImportError, metadata.PackageNotFoundError) as error:
        raise BenchmarkError('TOKENIZER_MISSING',
                             'Install optional benchmarks/requirements.txt dependencies: ' + str(error)) from None
    if version != TIKTOKEN_VERSION:
        raise BenchmarkError('TOKENIZER_VERSION',
                             f'Expected tiktoken {TIKTOKEN_VERSION}; installed {version}. Install benchmarks/requirements.txt.')
    try:
        return tokenizer.get_encoding(name)
    except Exception as error:
        raise BenchmarkError('TOKENIZER_RESOURCES',
                             f'Unable to load tokenizer resources for {name}: {error}. '
                             'Provide network access or a populated TIKTOKEN_CACHE_DIR.') from None


def _read_source(path):
    with Path(path).open('rb') as stream:
        source = stream.read(MAX_SOURCE_BYTES + 1)
    require(len(source) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Source exceeds 1 MiB.')
    return source


def _load_snapshot(source, path):
    # Match load_document's format detection and JSON diagnostics without reopening.
    try:
        text = source.decode('utf-8')
        if Path(path).suffix == '.pact' or text.lstrip().startswith('pact '):
            return loads(text)
        return json.loads(text, object_pairs_hook=_unique_pairs)
    except PactError:
        raise
    except (ValueError, RecursionError) as error:
        raise PactError('SOURCE_INVALID', str(error)) from None


def measure_pair(name, compact_path, json_path, encoding):
    compact = _read_source(compact_path)
    compact_document = loads(compact.decode('utf-8'))
    json_document = _load_snapshot(_read_source(json_path), json_path)
    validate_document(compact_document)
    validate_document(json_document)
    if compact_document != json_document:
        raise BenchmarkError('REPRESENTATION_MISMATCH', f'{name}: source representations differ')
    minified = json.dumps(json_document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    result = {'example': name}
    for representation, source in (('compact', compact), ('minified_json', minified)):
        # Ordinary text encoding counts literal special-token-looking strings as source.
        result[representation] = {
            'bytes': len(source),
            'tokens': len(encoding.encode_ordinary(source.decode('utf-8'))),
            'sha256': hashlib.sha256(source).hexdigest(),
        }
    return result


def measure_context(name, source_path, function_id, encoding):
    from pact.inspection import inspect_function
    context = inspect_function(load_document(source_path), function_id)
    source = (json.dumps(context, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode('utf-8')
    return {
        'example': name, 'function': function_id,
        'scope': 'selective CLI context subset; not equivalent executable source',
        'context_only': context['context_only'], 'buildable': context['buildable'],
        'omitted': context['omitted'],
        'bytes': len(source), 'tokens': len(encoding.encode_ordinary(source.decode('utf-8'))),
        'sha256': hashlib.sha256(source).hexdigest(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoding', choices=('o200k_base', 'cl100k_base'), default='o200k_base')
    args = parser.parse_args(argv)
    try:
        encoding = load_tokenizer(args.encoding)
        results = [measure_pair(name, ROOT/f'examples/{name}.pact',
                                ROOT/f'examples/{name}.pact.json', encoding) for name in EXAMPLES]
        report = {
            'format': 'pact.token-baseline/0.1',
            'metric': 'representation_tokens',
            'tokenizer': {'package': 'tiktoken', 'version': TIKTOKEN_VERSION, 'encoding': encoding.name},
            'scope': 'exact compact file and minified JSON; excludes prompts and tool framing',
            'agent_task_trials_run': False,
            'results': results,
            'selective_context': [measure_context('alien-harvest', ROOT/'examples/alien-harvest.pact',
                                                   'player.move', encoding)],
        }
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (BenchmarkError, PactError, OSError, UnicodeError) as error:
        diagnostic = (error.diagnostic if isinstance(error, PactError) else
                      {'status': 'rejected', 'code': getattr(error, 'code', 'BENCHMARK_IO'), 'message': str(error)})
        print(json.dumps(diagnostic, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
