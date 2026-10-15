"""Run a PACT/Python/JavaScript/C counter candidate in a configured Docker image."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

from .agent_trace_grader import frozen_oracle, grade_trace, ORACLE_SHA256, pairs, snapshot
from .agent_candidate_policy import audit_candidate
from .bounded_process import run_bounded


def create_command(container,image):
    if not isinstance(image,str) or re.fullmatch(r'sha256:[0-9a-f]{64}',image) is None:
        raise ValueError('Specify a local immutable Docker image ID: sha256:<64 lowercase hex>')
    return ['docker','create','--name',container,'--interactive','--pull','never','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534',
            '--memory','128m','--memory-swap','128m','--cpus','1','--pids-limit','32',
            '--ulimit','cpu=10:10','--ulimit','fsize=1048576:1048576','--ulimit','nofile=64:64',
            '--tmpfs','/tmp:size=16m,nosuid,nodev,noexec','--log-driver','none',
            '--entrypoint','python3',image,'-I','-B','/opt/worker.py']


def control(command):
    try:result=subprocess.run(command,capture_output=True,timeout=10)
    except FileNotFoundError:raise ValueError('Docker is required; no local execution fallback') from None
    except subprocess.TimeoutExpired:raise ValueError('Docker control operation timed out') from None
    if result.returncode:raise ValueError('Docker control failed: '+result.stderr.decode(errors='replace')[:512])
    if len(result.stdout)>1048576:raise ValueError('Docker control response exceeds 1 MiB')
    return result.stdout


def verify_configuration(info,image):
    config=info['HostConfig']
    required={'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'Memory':134217728,
              'MemorySwap':134217728,'NanoCpus':1000000000,'PidsLimit':32}
    if any(config.get(key)!=value for key,value in required.items()):raise ValueError('Container isolation configuration differs')
    if config.get('Binds') or config.get('VolumesFrom'):raise ValueError('Host mounts are forbidden')
    if any(m.get('Type')!='tmpfs' or m.get('Destination')!='/tmp' for m in info.get('Mounts',[])):
        raise ValueError('Only the bounded temporary filesystem is allowed')
    if config.get('CapDrop')!=['ALL'] or 'no-new-privileges' not in config.get('SecurityOpt',[]):
        raise ValueError('Container privilege restrictions differ')
    if info['Image']!=image or info['Config']['User']!='65534:65534':raise ValueError('Container identity differs')


def unexecuted_tests(language):
    pact=language=='pact'
    return {'engine':'wasm' if pact else None,'status':'not_run' if pact else 'not_applicable',
            'declared':None,'executed':0,'pass':None,
            'reason':'EXECUTION_NOT_COMPLETED' if pact else 'NO_DECLARATION_INTERFACE'}


def validate_embedded_tests(value):
    keys={'engine','status','declared','executed','pass','reason'}
    if not isinstance(value,dict) or set(value)!=keys or value['engine']!='wasm':
        raise ValueError('Expected separate PACT declaration evidence')
    if value['pass'] is not None and type(value['pass']) is not bool:
        raise ValueError('Expected boolean declaration result')
    count=value['declared']
    bounded=type(count) is int and 1<=count<=256
    status=value['status']
    if status=='passed':
        valid=bounded and type(value['executed']) is int and value['executed']==count and value['pass'] is True and value['reason'] is None
    elif status=='failed':
        valid=bounded and value['executed'] is None and value['pass'] is False and isinstance(value['reason'],str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,99}',value['reason'])
    elif status=='missing':
        valid=type(count) is int and count==0 and type(value['executed']) is int and value['executed']==0 and value['pass'] is False and value['reason']=='NO_DECLARED_TESTS'
    else:
        valid=value==unexecuted_tests('pact') and type(value['executed']) is int
    if not valid:raise ValueError('Inconsistent PACT declaration evidence')
    return value


def parse_observations(stdout,language):
    observations=json.loads(stdout.decode('utf-8'),object_pairs_hook=pairs)
    if not isinstance(observations,dict):raise ValueError('Unexpected worker output')
    runtime=observations.pop('runtime',None)
    if language=='pact':embedded=validate_embedded_tests(observations.pop('embedded_tests',None))
    else:
        if 'embedded_tests' in observations:raise ValueError('Unexpected declaration evidence')
        embedded=unexecuted_tests(language)
    if language in ('javascript','c'):
        keys,engine=({'engine','node','v8'},'node') if language=='javascript' else ({'engine','gcc'},'gcc')
        if (not isinstance(runtime,dict) or set(runtime)!=keys or runtime['engine']!=engine
                or any(not isinstance(value,str) or not 1<=len(value)<=100 for value in runtime.values())):
            raise ValueError('Expected bounded toolchain metadata')
    elif runtime is not None:raise ValueError('Unexpected runtime metadata')
    if set(observations)!={'execution_status','initial_counter','cases','reset_case'}:
        raise ValueError('Unexpected worker output')
    return observations,runtime,embedded


def run_candidate(candidate_path,image,language='pact'):
    if language not in ('pact','python','javascript','c'):raise ValueError('Unsupported isolated candidate language')
    create_command('validation',image)
    if sys.platform!='linux':raise ValueError('The Docker counter adapter currently requires Linux')
    candidate=snapshot(candidate_path);oracle=frozen_oracle()
    image_info=json.loads(control(['docker','image','inspect',image]))[0]
    if image_info['Id']!=image or image_info.get('Config',{}).get('Volumes'):
        raise ValueError('Image identity differs or declares automatic volumes')
    container='pact-trial-'+uuid.uuid4().hex
    command=create_command(container,image)
    stdout=stderr=b'';timed_out=False;runtime_failed=False;output_limited=False;termination_reason=None
    try:
        control(command)
        info=json.loads(control(['docker','inspect',container]))[0]
        verify_configuration(info,image)
        request=json.dumps({'cases':[c['args'] for c in oracle['cases']],
            'reset_args':oracle['embedded_test_after_edit']['args'],
            'language':language,'candidate_base64':base64.b64encode(candidate).decode()}).encode()
        result=run_bounded(['docker','start','--attach','--interactive',container],request)
        stdout,stderr=result['stdout'],result['stderr']
        runtime_failed=result['returncode']!=0;timed_out=result['timed_out'];output_limited=result['output_limited']
    finally:
        # Removal also stops a timed-out container; failure prevents a success receipt.
        control(['docker','rm','--force',container])
    failed={'execution_status':'timeout' if timed_out else 'error','initial_counter':None,'cases':[],'reset_case':None}
    termination_reason='output_limit' if output_limited else 'timeout' if timed_out else 'runtime_error' if runtime_failed else None
    runtime=None;embedded=unexecuted_tests(language)
    try:
        observations=failed
        if not termination_reason:observations,runtime,embedded=parse_observations(stdout,language)
    except (ValueError,TypeError,RecursionError):
        observations=failed;termination_reason='invalid_worker_output'
    log={'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':base64.b64encode(stderr).decode()}
    log_hash=hashlib.sha256(json.dumps(log,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    trace={'format':'pact.agent-execution-trace/0.1','task':'counter-four','language':language,
           'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'oracle_sha256':ORACLE_SHA256,
           'executor':{'command':'python3 -I -B /opt/worker.py','revision':image,'log_sha256':log_hash},**observations}
    try:grade=grade_trace(trace,candidate)
    except (ValueError,TypeError,KeyError,RecursionError):
        trace.update(failed);embedded=unexecuted_tests(language);termination_reason='invalid_worker_output';grade=grade_trace(trace,candidate)
    return {'format':'pact.agent-sandbox-receipt/0.6','image_id':image,'backend':'docker','runtime':runtime,
            'trace':trace,'grade':grade,'policy':audit_candidate(candidate,language=language),'log':log,
            'embedded_tests':embedded,
            'termination_reason':termination_reason,'output_limit_bytes':1048576,
            'timed_out':timed_out,'output_limited':output_limited,
            'isolation_configuration_checked':True,'candidate_pass':None,'model_trial':False}


def checks_passed(report):
    return (report['grade']['behavior_pass'] is True and report['policy']['policy_pass'] is True
            and (report['trace']['language']!='pact' or report['embedded_tests']['pass'] is True))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate');parser.add_argument('--image',required=True)
    parser.add_argument('--language',choices=['pact','python','javascript','c'],default='pact')
    args=parser.parse_args(argv)
    try:
        report=run_candidate(args.candidate,args.image,language=args.language)
        print(json.dumps(report,sort_keys=True,indent=2))
        return 0 if checks_passed(report) else 2
    except (ValueError,TypeError,KeyError,OSError,RecursionError) as error:
        print(json.dumps({'status':'rejected','code':'AGENT_SANDBOX_REJECTED','message':str(error)}),file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
