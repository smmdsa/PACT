"""Bounded deterministic reference replay; no host source or Wasm execution."""
import copy
import hashlib
import json
from pathlib import Path

from .diagnostics import PactError
from .graph import _unique_pairs
from .module import integer
from .reference import Machine
from .revision import revision
from .schema import MAX_SOURCE_BYTES, closed_record, require

MAX_CALLS = 64
MAX_EVALUATIONS = 100_000


def state_hash(state):
    return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def replay_document(document, record):
    closed_record(record, {'format','expected_revision_sha256','calls'})
    require(record['format']=='pact.replay-input/0.1.0','REPLAY_FORMAT','Unsupported replay input format.')
    machine=Machine(document,evaluation_limit=MAX_EVALUATIONS,runtime_diagnostics=True)
    expected=revision(document)
    require(record['expected_revision_sha256']==expected,'REVISION_MISMATCH','Replay source revision differs.')
    calls=record['calls']
    require(isinstance(calls,list) and 1<=len(calls)<=MAX_CALLS,'REPLAY_CALLS','Expected 1–64 calls.')
    # Validate the entire recording before executing any call.
    for call in calls:
        closed_record(call,{'function','args'})
        name=call['function']
        require(isinstance(name,str) and name in document['exports'],'REPLAY_FUNCTION','Call must select an export.')
        args=call['args']
        require(isinstance(args,list) and len(args)==len(machine.functions[name]['params']),
                'REPLAY_ARGUMENTS','Call arguments must match the exported signature.')
        for value in args:
            integer(value)
    events=[]
    status='completed'
    for index,call in enumerate(calls):
        event={'index':index,'function':call['function'],'args':list(call['args'])}
        try:
            event['result']=machine.call(call['function'],*call['args'])
        except PactError as error:
            event['diagnostic']=error.diagnostic
            status='limited' if error.diagnostic['code']=='REPLAY_LIMIT' else 'trapped'
        event['state_sha256']=state_hash(machine.state)
        events.append(event)
        if status!='completed':
            break
    return {'format':'pact.replay-report/0.1.0','engine':'reference','status':status,
            'semantic_revision_sha256':expected,'initial_state_sha256':state_hash(machine.initial_state),
            'events':events,'final_state':copy.deepcopy(machine.state),
            'final_state_sha256':state_hash(machine.state),'evaluations':machine.evaluations,
            'evaluation_limit':MAX_EVALUATIONS,'requested_calls':len(calls)}


def _snapshot(path):
    try:
        with Path(path).open('rb') as stream:
            data=stream.read(MAX_SOURCE_BYTES+1)
        require(len(data)<=MAX_SOURCE_BYTES,'SOURCE_LIMIT','Source exceeds 1 MiB.')
        return data, data.decode('utf-8')
    except (OSError,UnicodeError) as error:
        raise PactError('SOURCE_INVALID',str(error)) from None


def _json(source):
    try:
        return json.loads(source,object_pairs_hook=_unique_pairs)
    except PactError:
        raise
    except (ValueError,RecursionError) as error:
        raise PactError('SOURCE_INVALID',str(error)) from None


def replay_file(source_path, record_path):
    from .compact import loads
    from .source_locations import index_source, index_json_source, validate_json_source
    data,source=_snapshot(source_path)
    first=next((line.strip() for line in source.split('\n')
                if line.strip() and not line.lstrip().startswith('#')),'')
    compact=Path(source_path).suffix=='.pact' or first.startswith('pact ')
    document=loads(source) if compact else _json(source)
    if not compact:
        validate_json_source(source,document)
    record_data,record_source=_snapshot(record_path)
    report=replay_document(document,_json(record_source))
    report.update(source_path=str(source_path),source_sha256=hashlib.sha256(data).hexdigest(),
                  record_sha256=hashlib.sha256(record_data).hexdigest())
    positions=(index_source if compact else index_json_source)(source)
    for event in report['events']:
        diagnostic=event.get('diagnostic')
        if diagnostic:
            matches=[p for p in positions if p['function']==diagnostic.get('function')
                     and p['id']==diagnostic.get('node') and p['kind']!='function']
            if len(matches)==1:
                diagnostic['source_location']=matches[0]
    return report
