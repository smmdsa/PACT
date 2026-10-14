"""Grade externally supplied counter traces; never execute candidate source."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from .agent_trials import LANGUAGES, MATERIAL, digest, integer

LIMIT=1024*1024
ORACLE_SHA256='0013ce376abe55ecf2b0cdbce7612f032d99ec7902778625ef74ec336421c0ae'
FIELDS={'format','task','language','candidate_sha256','oracle_sha256','executor',
        'execution_status','initial_counter','cases','reset_case'}


def record(value, fields):
    if not isinstance(value,dict) or set(value)!=fields:
        raise ValueError('Missing or unknown record fields')


def vector(value):
    if not isinstance(value,list) or len(value)!=2:
        raise ValueError('Expected two signed i32 values')
    for number in value:integer(number,'i32',-(2**31),2**31-1)


def observation(value):
    record(value,{'args','status','counter'})
    vector(value['args'])
    if value['status'] not in ('ok','bounds','error','timeout'):
        raise ValueError('Unknown observation status')
    if value['counter'] is not None:vector(value['counter'])


def frozen_oracle():
    data=snapshot(MATERIAL/'cases.json')
    if hashlib.sha256(data).hexdigest()!=ORACLE_SHA256:
        raise ValueError('Frozen oracle identity differs')
    oracle=json.loads(data)
    state=list(oracle['initial_counter'])
    for case in oracle['cases']:
        index,amount=case['args'];valid=0<=index<2
        if valid:state[index]=(state[index]+4*amount+2**31)%2**32-2**31
        if case['counter']!=state or case['status']!=('ok' if valid else 'bounds'):
            raise ValueError('Frozen oracle disagrees with independent arithmetic')
    return oracle


def grade_trace(trace, candidate):
    record(trace,FIELDS)
    if trace['format']!='pact.agent-execution-trace/0.1' or trace['task']!='counter-four':
        raise ValueError('Unknown trace format or task')
    if trace['language'] not in LANGUAGES:raise ValueError('Unknown language')
    for key in ('candidate_sha256','oracle_sha256'):digest(trace[key],key)
    if not isinstance(candidate,bytes) or len(candidate)>LIMIT:raise ValueError('Candidate exceeds 1 MiB or is not bytes')
    if hashlib.sha256(candidate).hexdigest()!=trace['candidate_sha256']:
        raise ValueError('Candidate bytes differ from trace identity')
    if trace['oracle_sha256']!=ORACLE_SHA256:raise ValueError('Trace oracle identity differs')
    executor=trace['executor'];record(executor,{'command','revision','log_sha256'})
    for key in ('command','revision'):
        if not isinstance(executor[key],str) or not executor[key].strip():raise ValueError('Missing executor provenance')
    digest(executor['log_sha256'],'log_sha256')
    if trace['execution_status'] not in ('completed','compile_error','error','timeout'):
        raise ValueError('Unknown execution status')
    if trace['initial_counter'] is not None:vector(trace['initial_counter'])
    oracle=frozen_oracle();cases=trace['cases']
    if not isinstance(cases,list) or len(cases)>len(oracle['cases']):raise ValueError('Too many cases or non-list cases')
    for case in cases:observation(case)
    reset=trace['reset_case']
    if reset is not None:observation(reset)
    results=[case==expected for case,expected in zip(cases,oracle['cases'])]
    expected_reset={'args':oracle['embedded_test_after_edit']['args'],'status':'ok',
                    'counter':oracle['embedded_test_after_edit']['counter']}
    initial_match=trace['initial_counter']==oracle['initial_counter']
    reset_match=reset==expected_reset
    missing=len(oracle['cases'])-len(cases)
    behavior=(trace['execution_status']=='completed' and initial_match and reset_match and not missing and all(results))
    return {'format':'pact.agent-trace-grade/0.1','task':'counter-four','language':trace['language'],
            'behavior_pass':behavior,'candidate_pass':None,'execution_authenticated':False,
            'execution_status':trace['execution_status'],'initial_match':initial_match,'reset_match':reset_match,
            'case_results':results,'missing_cases':missing,'candidate_sha256':trace['candidate_sha256'],
            'oracle_sha256':ORACLE_SHA256,'executor':dict(executor),
            'grader_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'unverified_checks':['isolated execution','interface preservation','minimal source edit',
                                 'dependencies and policy preservation','embedded test correctness']}


def snapshot(path):
    with Path(path).open('rb') as stream:data=stream.read(LIMIT+1)
    if len(data)>LIMIT:raise ValueError('Input exceeds 1 MiB')
    return data


def pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('Duplicate JSON key')
        result[key]=value
    return result


def grade_files(trace_path,candidate_path):
    data=snapshot(trace_path);candidate=snapshot(candidate_path)
    trace=json.loads(data.decode('utf-8'),object_pairs_hook=pairs)
    report=grade_trace(trace,candidate)
    report['trace_bytes_sha256']=hashlib.sha256(data).hexdigest()
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace');parser.add_argument('--candidate',required=True)
    args=parser.parse_args(argv)
    try:
        report=grade_files(args.trace,args.candidate)
        print(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2))
        return 0 if report['behavior_pass'] else 2
    except (ValueError,TypeError,OSError,RecursionError) as error:
        print(json.dumps({'status':'rejected','code':'AGENT_TRACE_INVALID','message':str(error)}),file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
