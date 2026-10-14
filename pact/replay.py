"""Revision-checked reference and compiler-produced Wasm call replay."""
import copy
import hashlib
import json
import subprocess
import tempfile
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


def _prepare(document, record):
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
    return machine,expected,calls


def replay_document(document, record, engine='reference'):
    require(engine in ('reference','wasm','compare'),'REPLAY_ENGINE','Unsupported replay engine.')
    machine,expected,calls=_prepare(document,record)
    if engine=='wasm':
        return _wasm_replay(machine.plan,expected,calls)
    reference=_reference_replay(machine,expected,calls)
    if engine=='reference':
        return reference
    if reference['status']=='limited':
        return {'format':'pact.replay-comparison/0.1.0','engine':'compare','status':'incomplete',
                'semantic_revision_sha256':expected,'reference':reference,'wasm':None,
                'reason':'Reference evaluation budget exhausted; Wasm was not executed.'}
    wasm=_wasm_replay(machine.plan,expected,calls)
    return compare_reports(reference,wasm)


def compare_reports(reference, wasm):
    """Compare observed outcomes; trap kind/node identity is reference-only."""
    def outcomes(report):
        return [(event['index'],event['function'],event['args'],event.get('result'),
                 'diagnostic' in event,event['state_sha256'])
                for event in report['events']]
    matched=(reference['semantic_revision_sha256']==wasm['semantic_revision_sha256'] and
             reference['status']==wasm['status'] and
             reference['initial_state_sha256']==wasm['initial_state_sha256'] and
             reference['final_state']==wasm['final_state'] and
             outcomes(reference)==outcomes(wasm))
    return {'format':'pact.replay-comparison/0.1.0','engine':'compare',
            'status':'matched' if matched else 'mismatch',
            'semantic_revision_sha256':reference['semantic_revision_sha256'],
            'reference':reference,'wasm':wasm}


def _wasm_replay(plan, expected, calls):
    from .module_wasm import compile_module_with_traps
    binary,trap_map=compile_module_with_traps(plan)
    require(len(binary)<=8*MAX_SOURCE_BYTES,'REPLAY_BINARY_LIMIT','Compiled replay exceeds 8 MiB.')
    script=Path(__file__).resolve().parents[1]/'tools/replay_module.mjs'
    runtime=script.read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);wasm=root/'module.wasm';request=root/'request.json'
        wasm.write_bytes(binary)
        host=root/'replay.mjs';host.write_bytes(runtime)
        request.write_text(json.dumps({'layout':plan['layout'],'calls':calls,'revision':expected}),encoding='utf-8')
        try:
            result=subprocess.run(['node',str(host),str(wasm),str(request)],capture_output=True,timeout=15)
        except FileNotFoundError:
            raise PactError('REPLAY_RUNTIME_MISSING','Node is required for Wasm replay.') from None
        except subprocess.TimeoutExpired:
            raise PactError('REPLAY_TIMEOUT','Wasm replay exceeded 15 seconds; no partial report is available.') from None
        require(result.returncode==0,'REPLAY_RUNTIME','Wasm replay host failed.')
        require(len(result.stdout)<=MAX_SOURCE_BYTES,'REPLAY_REPORT_LIMIT','Wasm report exceeds 1 MiB.')
        report=_json(result.stdout.decode('utf-8'))
    require(report.get('wasm_sha256')==hashlib.sha256(binary).hexdigest(),
            'REPLAY_RUNTIME','Wasm replay artifact identity differs.')
    report['runtime_sha256']=hashlib.sha256(runtime).hexdigest()
    report['timeout_seconds']=15
    report['trap_map_complete']=trap_map['complete']
    positions={(p['function_index'],p['offset']):p for p in trap_map['positions']}
    for event in report['events']:
        diagnostic=event.get('diagnostic',{})
        location=diagnostic.get('wasm_location',{})
        position=positions.get((location.get('function_index'),location.get('offset')))
        if position:
            diagnostic.update(function=position['function'],node=position['node'],
                              trap_site_kind=position['kind'])
    return report


def _reference_replay(machine, expected, calls):
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


def replay_file(source_path, record_path, engine='reference'):
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
    report=replay_document(document,_json(record_source),engine=engine)
    report.update(source_path=str(source_path),source_sha256=hashlib.sha256(data).hexdigest(),
                  record_sha256=hashlib.sha256(record_data).hexdigest())
    positions=(index_source if compact else index_json_source)(source)
    reports=[report.get('reference'),report.get('wasm')] if engine=='compare' else [report]
    for event in (event for result in reports if result for event in result['events']):
        diagnostic=event.get('diagnostic')
        if diagnostic:
            matches=[p for p in positions if p['function']==diagnostic.get('function')
                     and p['id']==diagnostic.get('node') and p['kind']!='function']
            if len(matches)==1:
                diagnostic['source_location']=matches[0]
    return report
