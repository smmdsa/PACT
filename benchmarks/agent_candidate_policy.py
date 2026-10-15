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
JAVASCRIPT_BASELINE_SHA256='e24527b2f7f7b299fc4e954a37dea3b06db95c74a75b2c68052aa9480716cb6f'
C_BASELINE_SHA256='905e7f8378c205b3bb65cd9cb90567b9e0b1ba8d316903139300cf565a846a7e'


def audit_javascript(candidate):
    return audit_exact(candidate,'javascript','JavaScript','counter.mjs',JAVASCRIPT_BASELINE_SHA256)


def audit_exact(candidate,language,label,filename,baseline_hash):
    source=snapshot(MATERIAL/filename)
    if hashlib.sha256(source).hexdigest()!=baseline_hash:
        raise ValueError('Frozen '+label+' baseline identity differs')
    expected=source.replace(b'i < 3',b'i < 4')
    report={'format':'pact.agent-source-policy/0.1','task':'counter-four','language':language,
            'scope':'counter-four exact '+label+' source edit/0.1','policy_pass':False,'candidate_pass':None,
            'baseline_sha256':baseline_hash,'runtime_executed':False}
    if not isinstance(candidate,bytes) or len(candidate)>LIMIT:
        report['reason']='CANDIDATE_SOURCE_INVALID';return report
    report['candidate_sha256']=hashlib.sha256(candidate).hexdigest()
    report['policy_pass']=candidate.replace(b'\r\n',b'\n')==expected
    report['reason']='EXPECTED_SOURCE_EDIT' if report['policy_pass'] else 'UNAPPROVED_SOURCE_CHANGE'
    return report


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


CANONICAL_PROFILE='canonical/0.1'
FORMS_PROFILE='counter-four-forms/0.2'
POLICY_PROFILES=(CANONICAL_PROFILE,FORMS_PROFILE)
FORMS_CONTRACT=MATERIAL/'policy_forms/0.2/contract.json'
FORMS_CONTRACT_SHA256='f772647a2f5298d407222a7b2cc365acc27dd48841a12b3a0c0871d584b63ac7'
POLICY_LANGUAGES={'pact':('counter.pact','pact-semantic-revision'),
                  'python':('counter.py','python-ast-sha256'),
                  'javascript':('counter.mjs','normalized-source-sha256'),
                  'c':('counter.c','normalized-source-sha256')}


def parse_pact(candidate):
    source=candidate.decode('utf-8')
    first=next((line.strip() for line in source.split('\n')
                if line.strip() and not line.lstrip().startswith('#')),'')
    if first.startswith('pact '):return loads(source)
    document=json.loads(source,object_pairs_hook=pairs)
    validate_document(document)
    return document


def form_fingerprint(candidate,language):
    if not isinstance(candidate,bytes) or len(candidate)>LIMIT:raise ValueError('Expected at most 1 MiB')
    source=candidate.decode('utf-8')
    if language=='pact':return revision(parse_pact(candidate))
    if language=='python':
        source=ast.dump(ast.parse(source),include_attributes=False)
        return hashlib.sha256(source.encode()).hexdigest()
    return hashlib.sha256(candidate.replace(b'\r\n',b'\n')).hexdigest()


def load_forms_contract():
    data=snapshot(FORMS_CONTRACT)
    if hashlib.sha256(data).hexdigest()!=FORMS_CONTRACT_SHA256:
        raise ValueError('Registered source-policy contract identity differs')
    return json.loads(data,object_pairs_hook=pairs)


def audit_forms(candidate,language):
    contract=load_forms_contract();entry=contract['languages'][language]
    baseline=snapshot(MATERIAL/POLICY_LANGUAGES[language][0])
    if hashlib.sha256(baseline).hexdigest()!=entry['baseline_sha256']:
        raise ValueError('Frozen baseline identity differs')
    report={'format':'pact.agent-source-policy/0.2','task':'counter-four','language':language,
            'scope':'two registered counter-four forms; not general equivalence',
            'profile':FORMS_PROFILE,'contract_sha256':FORMS_CONTRACT_SHA256,
            'baseline_sha256':entry['baseline_sha256'],'fingerprint_kind':entry['fingerprint_kind'],
            'policy_pass':False,'candidate_pass':None,'runtime_executed':False,'accepted_form':None,
            'candidate_sha256':hashlib.sha256(candidate).hexdigest() if isinstance(candidate,bytes) else None}
    try:fingerprint=form_fingerprint(candidate,language)
    except (ValueError,TypeError,KeyError,SyntaxError,RecursionError):
        report['reason']='CANDIDATE_SOURCE_INVALID';return report
    report['candidate_fingerprint']=fingerprint
    report['accepted_form']=next((name for name,value in entry['forms'].items() if value==fingerprint),None)
    report['policy_pass']=report['accepted_form'] is not None
    report['reason']='REGISTERED_FORM' if report['policy_pass'] else 'UNREGISTERED_FORM'
    return report


def audit_candidate(candidate,language='pact',profile=CANONICAL_PROFILE):
    if profile not in POLICY_PROFILES:raise ValueError('Unsupported source-policy profile')
    if language not in POLICY_LANGUAGES:raise ValueError('Unsupported candidate policy language')
    if profile==FORMS_PROFILE:return audit_forms(candidate,language)
    if language=='c':return audit_exact(candidate,'c','C','counter.c',C_BASELINE_SHA256)
    if language=='javascript':return audit_javascript(candidate)
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
        document=parse_pact(candidate)
    except (ValueError,TypeError,KeyError,RecursionError):
        report['reason']='CANDIDATE_SOURCE_INVALID'
        return report
    report['candidate_revision_sha256']=revision(document)
    report['policy_pass']=document==expected
    report['reason']='EXPECTED_IR_EDIT' if report['policy_pass'] else 'UNAPPROVED_IR_CHANGE'
    report['changed_sections']=[key for key in expected if document.get(key)!=expected[key]]
    return report
