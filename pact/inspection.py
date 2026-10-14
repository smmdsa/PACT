"""Deterministic context retrieval for fully validated numeric modules."""

import copy
import json

from .module import analyze_module
from .revision import revision
from .schema import GRAPH_FORMAT, require


_OMITTED = ['dependency_function_bodies', 'cell_initial_values', 'assets', 'test_case_bodies']


def _index(document):
    require(not isinstance(document, dict) or document.get('format') != GRAPH_FORMAT,
            'INSPECTION_UNSUPPORTED', 'Selective inspection supports numeric modules only; text graphs are unsupported.')
    plan = analyze_module(document)
    functions = {fn['id']: fn for fn in document['functions']}
    calls = {key: {node['target'] for node in fn['nodes'] if node['op'] == 'call'}
             for key, fn in functions.items()}
    callers = {key: set() for key in functions}
    for key, targets in calls.items():
        for target in targets:
            callers[target].add(key)
    return plan, functions, calls, callers


def _closure(key, edges):
    visited, pending = set(), list(edges[key])
    while pending:
        current = pending.pop()
        if current not in visited:
            visited.add(current)
            pending.extend(edges[current] - visited)
    return visited


def _provenance(document, output_format):
    return {'format': output_format, 'source_format': document['format'],
            'context_only': True, 'buildable': False,
            'semantic_revision_sha256': revision(document)}


def _footprint(keys, functions):
    constants, reads, writes = set(), set(), set()
    for key in keys:
        for node in functions[key]['nodes']:
            if node['op'] == 'const.load':
                constants.add(node['name'])
            elif node['op'] == 'state.load':
                reads.add(node['cell'])
            elif node['op'] == 'state.store':
                writes.add(node['cell'])
    return constants, reads, writes


def _signature(fn):
    return copy.deepcopy({field: fn[field] for field in ('id', 'params', 'locals', 'result', 'writes')})


def inspect_function(document, function_id):
    """Return bounded function context; validate the entire module first.

    Tests are ID/target summaries, and dependencies are signatures only. Call
    graph relationships do not establish semantic purpose or complete impact.
    """
    plan, functions, calls, callers = _index(document)
    require(isinstance(function_id, str) and function_id in functions,
            'FUNCTION_MISSING', 'Selected function does not exist.')
    dependencies = _closure(function_id, calls)
    affected = _closure(function_id, callers)
    constants, reads, writes = _footprint(dependencies | {function_id}, functions)

    def cell_metadata(keys):
        return [{'id': key, 'type': 'i32', 'count': plan['layout'][key]['count'],
                 'mutable': plan['layout'][key]['mutable']} for key in sorted(keys)]

    result = _provenance(document, 'pact.inspection/0.1.0')
    result.update({
        'selected_function': json.loads(json.dumps(functions[function_id], sort_keys=True)),
        'direct_callees': sorted(calls[function_id]),
        'transitive_callees': sorted(dependencies),
        'direct_callers': sorted(callers[function_id]),
        'transitive_callers': sorted(affected),
        'dependency_functions': [_signature(functions[key]) for key in sorted(dependencies)],
        'constants': {key: document['constants'][key] for key in sorted(constants)},
        'cells': {'read': cell_metadata(reads), 'write': cell_metadata(writes)},
        'test_summaries': [{'id': test['id'], 'function': test['function']}
                           for test in sorted(document['tests'], key=lambda item: item['id'])
                           if test['function'] in affected | {function_id}],
        'omitted': list(_OMITTED),
    })
    return result


def symbols(document):
    """List signatures and transitive syntactic footprints for discovery."""
    _, functions, calls, callers = _index(document)
    result = _provenance(document, 'pact.symbols/0.1.0')
    summaries = []
    for key in sorted(functions):
        dependencies = _closure(key, calls)
        constants, reads, writes = _footprint(dependencies | {key}, functions)
        summary = _signature(functions[key])
        summary.update({'exported': key in document['exports'],
                        'direct_callees': sorted(calls[key]),
                        'transitive_callees': sorted(dependencies),
                        'direct_callers': sorted(callers[key]),
                        'transitive_callers': sorted(_closure(key, callers)),
                        'constants': sorted(constants), 'read_cells': sorted(reads),
                        'write_cells': sorted(writes)})
        summaries.append(summary)
    result.update({'functions': summaries,
                   'omitted': ['function_bodies', 'constant_values', 'cell_initial_values',
                               'assets', 'test_case_bodies']})
    return result
