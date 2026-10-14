"""Trusted container worker: closed-schema PACT only, no host-language eval."""
import json
import base64
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


result={'execution_status':'compile_error','initial_counter':None,'cases':[],'reset_case':None}
try:
    data=sys.stdin.buffer.read(2*1024*1024+1)
    if len(data)>2*1024*1024:raise ValueError('Worker input exceeds 2 MiB')
    request=json.loads(data)
    candidate=base64.b64decode(request['candidate_base64'],validate=True)
    if len(candidate)>1024*1024:raise ValueError('Candidate exceeds 1 MiB')
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
except Exception as error:
    print(str(error)[:512],file=sys.stderr)
print(json.dumps(result,sort_keys=True))
