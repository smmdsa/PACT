"""Pure candidate construction for bounded numeric-module updates."""

import copy
import re

from .module import analyze_module
from .revision import revision
from .schema import closed_record, identifier, require

FORMAT = 'pact.patch/0.1.0'
MAX_OPERATIONS = 256
_OPERATION_FIELDS = {
    'replace_node': {'op', 'function', 'id', 'node'},
    'set_constant': {'op', 'name', 'value'},
    'replace_test': {'op', 'id', 'test'},
}


def apply_patch(document, patch):
    """Return a fully validated detached candidate; never alter either input.

    Validation checks the complete original and candidate numeric modules. It
    does not execute declared tests, read or publish files, or grant authority.
    """
    analyze_module(document)
    closed_record(patch, {'format', 'expected_revision_sha256', 'operations'})
    require(patch['format'] == FORMAT, 'PATCH_INVALID', 'Unsupported patch format.')
    expected = patch['expected_revision_sha256']
    require(isinstance(expected, str) and re.fullmatch(r'[0-9a-f]{64}', expected) is not None,
            'PATCH_INVALID', 'Expected a lowercase SHA256 revision.')
    operations = patch['operations']
    require(isinstance(operations, list) and 1 <= len(operations) <= MAX_OPERATIONS,
            'PATCH_INVALID', f'Expected 1..{MAX_OPERATIONS} operations.')
    require(expected == revision(document), 'PATCH_STALE', 'Source revision differs from expected revision.')

    candidate = copy.deepcopy(document)
    functions = {fn['id']: fn for fn in candidate['functions']}
    nodes = {key: {node['id']: index for index, node in enumerate(fn['nodes'])}
             for key, fn in functions.items()}
    tests = {test['id']: index for index, test in enumerate(candidate['tests'])}
    targets = set()
    for operation in operations:
        require(isinstance(operation, dict), 'PATCH_INVALID', 'Expected an operation record.')
        op = operation.get('op')
        require(isinstance(op, str) and op in _OPERATION_FIELDS,
                'PATCH_INVALID', 'Unsupported patch operation.')
        closed_record(operation, _OPERATION_FIELDS[op])
        if op == 'replace_node':
            function, key = operation['function'], operation['id']
            identifier(function)
            identifier(key)
            require(function in functions and key in nodes[function],
                    'PATCH_TARGET_MISSING', 'Selected function/node does not exist.')
            target = (op, function, key)
            replacement = operation['node']
            require(isinstance(replacement, dict), 'PATCH_INVALID', 'Expected a replacement node record.')
            require(replacement.get('id') == key, 'PATCH_ID_CHANGED', 'Replacement node must preserve its ID.')
        elif op == 'replace_test':
            key = operation['id']
            identifier(key)
            require(key in tests, 'PATCH_TARGET_MISSING', 'Selected test does not exist.')
            target = (op, key)
            replacement = operation['test']
            require(isinstance(replacement, dict), 'PATCH_INVALID', 'Expected a replacement test record.')
            require(replacement.get('id') == key, 'PATCH_ID_CHANGED', 'Replacement test must preserve its ID.')
        else:
            key = operation['name']
            identifier(key)
            require(key in candidate['constants'], 'PATCH_TARGET_MISSING', 'Selected constant does not exist.')
            target = (op, key)
        require(target not in targets, 'PATCH_TARGET_DUPLICATE', 'Patch repeats the same target.')
        targets.add(target)
        if op == 'replace_node':
            functions[function]['nodes'][nodes[function][key]] = copy.deepcopy(replacement)
        elif op == 'replace_test':
            candidate['tests'][tests[key]] = copy.deepcopy(replacement)
        else:
            candidate['constants'][key] = copy.deepcopy(operation['value'])
    analyze_module(candidate)
    return candidate
