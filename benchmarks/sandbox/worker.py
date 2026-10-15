"""Container worker: candidate host-language execution is allowed only inside Docker."""
import json
import base64
import os
from pathlib import Path
import sys

sys.path.insert(0,'/opt/runtime')
from pact.diagnostics import PactError
from pact.graph import load_document
from pact.reference import Machine


def observe(machine,args):
    status='ok'
    try:machine.call('advance',*args)
    except PactError as error:
        if error.diagnostic['code']=='STATE_BOUNDS':status='bounds'
        else:raise
    return {'args':args,'status':status,'counter':list(machine.state['counter'])}


def python_scope(candidate):
    scope={'__name__':'candidate'}
    exec(compile(candidate.decode('utf-8'),'/tmp/candidate.py','exec'),scope)
    if not callable(scope.get('advance')) or not isinstance(scope.get('counter'),list) or len(scope['counter'])!=2:
        raise ValueError('Expected advance and two-element counter')
    return scope


def observe_python(scope,args):
    status='ok'
    try:scope['advance'](*args)
    except IndexError:status='bounds'
    return {'args':args,'status':status,'counter':list(scope['counter'])}


result={'execution_status':'compile_error','initial_counter':None,'cases':[],'reset_case':None}
try:
    data=sys.stdin.buffer.read(2*1024*1024+1)
    if len(data)>2*1024*1024:raise ValueError('Worker input exceeds 2 MiB')
    request=json.loads(data)
    if request.get('language','pact')=='pact':
        result['embedded_tests']={'engine':'wasm','status':'not_run','declared':None,'executed':0,
                                  'pass':None,'reason':'EXECUTION_NOT_COMPLETED'}
    candidate=base64.b64decode(request['candidate_base64'],validate=True)
    if len(candidate)>1024*1024:raise ValueError('Candidate exceeds 1 MiB')
    if request.get('language')=='c':
        from c_worker import execute_c
        execute_c(candidate,request,result)
        print(json.dumps(result,sort_keys=True));sys.exit(0)
    if request.get('language')=='javascript':
        Path('/tmp/candidate.mjs').write_bytes(candidate)
        Path('/tmp/request.json').write_text(json.dumps({'cases':request['cases'],'reset_args':request['reset_args']}))
        # Replace this process: the outer Docker capture/timeout governs Node directly.
        os.execv('/usr/local/bin/node',['node','/opt/javascript_worker.mjs','/tmp/request.json'])
    if request.get('language','pact')=='python':
        scope=python_scope(candidate)
        result['initial_counter']=list(scope['counter']);result['execution_status']='error'
        for args in request['cases']:result['cases'].append(observe_python(scope,args))
        result['reset_case']=observe_python(python_scope(candidate),request['reset_args'])
        result['execution_status']='completed'
        print(json.dumps(result,sort_keys=True));sys.exit(0)
    Path('/tmp/candidate.pact').write_bytes(candidate)
    document=load_document('/tmp/candidate.pact',validate_source=True)
    machine=Machine(document,evaluation_limit=100000,runtime_diagnostics=True)
    fn=machine.functions.get('advance',{})
    if 'advance' not in document['exports'] or fn.get('params')!=['index','amount'] or fn.get('result')!='unit':
        raise ValueError('Expected exported advance(index, amount) -> unit')
    if 'counter' not in machine.state or len(machine.state['counter'])!=2:
        raise ValueError('Expected two counter cells')
    result['initial_counter']=list(machine.state['counter'])
    result['execution_status']='error'
    for args in request['cases']:result['cases'].append(observe(machine,args))
    reset=Machine(document,evaluation_limit=100000,runtime_diagnostics=True)
    result['reset_case']=observe(reset,request['reset_args'])
    result['execution_status']='completed'
    print(json.dumps({'format':'pact.reference-checkpoint/0.1','observations':{
        key:value for key,value in result.items() if key!='embedded_tests'}},sort_keys=True),flush=True)
    from pact_tests import execute_declared_tests
    result['embedded_tests']=execute_declared_tests(document)
except Exception as error:
    print(str(error)[:512],file=sys.stderr)
print(json.dumps(result,sort_keys=True))
