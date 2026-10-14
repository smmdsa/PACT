"""Run a PACT counter candidate in an explicitly configured local Docker image."""
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


def run_candidate(candidate_path,image):
    create_command('validation',image)
    if sys.platform!='linux':raise ValueError('The Docker counter adapter currently requires Linux')
    candidate=snapshot(candidate_path);oracle=frozen_oracle()
    image_info=json.loads(control(['docker','image','inspect',image]))[0]
    if image_info['Id']!=image or image_info.get('Config',{}).get('Volumes'):
        raise ValueError('Image identity differs or declares automatic volumes')
    container='pact-trial-'+uuid.uuid4().hex
    command=create_command(container,image)
    stdout=stderr=b'';timed_out=False;runtime_failed=False
    try:
        control(command)
        info=json.loads(control(['docker','inspect',container]))[0]
        verify_configuration(info,image)
        request=json.dumps({'cases':[c['args'] for c in oracle['cases']],
            'reset_args':oracle['embedded_test_after_edit']['args'],
            'candidate_base64':base64.b64encode(candidate).decode()}).encode()
        try:
            result=subprocess.run(['docker','start','--attach','--interactive',container],input=request,
                                  capture_output=True,timeout=15)
            stdout,stderr=result.stdout,result.stderr
            runtime_failed=result.returncode!=0
        except subprocess.TimeoutExpired as error:
            timed_out=True;stdout=error.stdout or b'';stderr=error.stderr or b''
        if len(stdout)+len(stderr)>1048576:raise ValueError('Container output exceeds 1 MiB')
    finally:
        # Removal also stops a timed-out container; failure prevents a success receipt.
        control(['docker','rm','--force',container])
    observations=({'execution_status':'timeout' if timed_out else 'error','initial_counter':None,'cases':[],'reset_case':None}
                  if timed_out or runtime_failed else json.loads(stdout.decode('utf-8'),object_pairs_hook=pairs))
    if set(observations)!={'execution_status','initial_counter','cases','reset_case'}:
        raise ValueError('Unexpected worker output')
    log={'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':base64.b64encode(stderr).decode()}
    log_hash=hashlib.sha256(json.dumps(log,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    trace={'format':'pact.agent-execution-trace/0.1','task':'counter-four','language':'pact',
           'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'oracle_sha256':ORACLE_SHA256,
           'executor':{'command':'python3 -I -B /opt/worker.py','revision':image,'log_sha256':log_hash},**observations}
    return {'format':'pact.agent-sandbox-receipt/0.2','image_id':image,'backend':'docker',
            'trace':trace,'grade':grade_trace(trace,candidate),'policy':audit_candidate(candidate),'log':log,
            'isolation_configuration_checked':True,'candidate_pass':None,'model_trial':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate');parser.add_argument('--image',required=True)
    args=parser.parse_args(argv)
    try:
        report=run_candidate(args.candidate,args.image)
        print(json.dumps(report,sort_keys=True,indent=2))
        return 0 if report['grade']['behavior_pass'] and report['policy']['policy_pass'] else 2
    except (ValueError,TypeError,KeyError,OSError,RecursionError) as error:
        print(json.dumps({'status':'rejected','code':'AGENT_SANDBOX_REJECTED','message':str(error)}),file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
