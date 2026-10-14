"""Task-specific static IR policy; never execute candidate functions or host source."""
import copy
import hashlib
import json
import ast

from pact.compact import loads, validate_document
from pact.revision import revision
from .agent_trace_grader import frozen_oracle, pairs, snapshot, LIMIT
from .agent_trials import MATERIAL

BASELINE_SHA256='8752da831ade4baa876f6856404606725436fbc2a1d3c57ada2c0bcb3e4d0490'
PYTHON_BASELINE_SHA256='e5538586886c62eeb8d237e8f743956157c3f0436716cc212aeeb65ce073e819'


def audit_python(candidate):
    source=snapshot(MATERIAL/'counter.py')
    if hashlib.sha256(source).hexdigest()!=PYTHON_BASELINE_SHA256:raise ValueError('Frozen Python baseline identity differs')
    expected=ast.dump(ast.parse(source.decode().replace('range(3)','range(4)')),include_attributes=False)
    report={'format':'pact.agent-source-policy/0.1','task':'counter-four','language':'python',
            'scope':'counter-four canonical Python AST edit/0.1','policy_pass':False,'candidate_pass':None,
            'baseline_sha256':PYTHON_BASELINE_SHA256,'runtime_executed':False}
    try:
        if not isinstance(candidate,bytes) or len(candidate)>LIMIT:raise ValueError('Candidate exceeds 1 MiB')
        report['candidate_sha256']=hashlib.sha256(candidate).hexdigest()
        actual=ast.dump(ast.parse(candidate.decode('utf-8')),include_attributes=False)
    except (ValueError,TypeError,SyntaxError,RecursionError):
        report['reason']='CANDIDATE_SOURCE_INVALID';return report
    report['policy_pass']=actual==expected
    report['reason']='EXPECTED_AST_EDIT' if report['policy_pass'] else 'UNAPPROVED_AST_CHANGE'
    return report


def expected_document():
    source=snapshot(MATERIAL/'counter.pact')
    if hashlib.sha256(source).hexdigest()!=BASELINE_SHA256:
        raise ValueError('Frozen PACT baseline identity differs')
    document=copy.deepcopy(loads(source.decode('utf-8')))
    fn=next(fn for fn in document['functions'] if fn['id']=='advance')
    next(node for node in fn['nodes'] if node['id']=='repeat')['count']=4
    test=next(test for test in document['tests'] if test['id']=='positive.wrap')
    test['expect']['counter']=list(frozen_oracle()['embedded_test_after_edit']['counter'])
    return document


def audit_candidate(candidate,language='pact'):
    if language=='python':return audit_python(candidate)
    if language!='pact':raise ValueError('Unsupported candidate policy language')
    expected=expected_document()
    report={'format':'pact.agent-source-policy/0.1','task':'counter-four','language':'pact',
            'scope':'counter-four canonical IR edit/0.1','policy_pass':False,'candidate_pass':None,
            'baseline_sha256':BASELINE_SHA256,'expected_revision_sha256':revision(expected),
            'candidate_sha256':hashlib.sha256(candidate).hexdigest() if isinstance(candidate,bytes) else None,
            'runtime_executed':False}
    try:
        if not isinstance(candidate,bytes) or len(candidate)>LIMIT:raise ValueError('Expected at most 1 MiB candidate bytes')
        source=candidate.decode('utf-8')
        first=next((line.strip() for line in source.split('\n')
                    if line.strip() and not line.lstrip().startswith('#')),'')
        if first.startswith('pact '):document=loads(source)
        else:
            document=json.loads(source,object_pairs_hook=pairs)
            validate_document(document)
    except (ValueError,TypeError,KeyError,RecursionError):
        report['reason']='CANDIDATE_SOURCE_INVALID'
        return report
    report['candidate_revision_sha256']=revision(document)
    report['policy_pass']=document==expected
    report['reason']='EXPECTED_IR_EDIT' if report['policy_pass'] else 'UNAPPROVED_IR_CHANGE'
    report['changed_sections']=[key for key in expected if document.get(key)!=expected[key]]
    return report
