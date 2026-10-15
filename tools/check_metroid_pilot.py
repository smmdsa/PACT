"""Evaluate model-generated HTML only inside a disposable Docker browser worker."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

from benchmarks.agent_sandbox import control, create_command as validate_image
from benchmarks.agent_trace_grader import pairs, snapshot
from benchmarks.bounded_process import run_bounded

ROOT=Path(__file__).resolve().parents[1]
PILOT=ROOT/'benchmarks/metroidvania_pilot'


def create_command(name,image):
    validate_image(name,image)
    return ['docker','create','--name',name,'--interactive','--pull','never','--network','none','--read-only',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--user','65534:65534',
            '--memory','768m','--memory-swap','768m','--cpus','1','--pids-limit','128',
            '--ulimit','cpu=45:45','--ulimit','fsize=33554432:33554432','--ulimit','nofile=1024:1024',
            '--tmpfs','/tmp:size=64m,nosuid,nodev,noexec','--log-driver','none',
            '--entrypoint','node',image,'/opt/verify/verify_browser.mjs']


def verify_configuration(info,image):
    host=info['HostConfig']
    required={'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'Memory':805306368,
              'MemorySwap':805306368,'NanoCpus':1000000000,'PidsLimit':128}
    if any(host.get(key)!=value for key,value in required.items()):raise ValueError('Browser isolation differs')
    if host.get('Binds') or host.get('VolumesFrom'):raise ValueError('Host mounts forbidden')
    if any(m.get('Type')!='tmpfs' or m.get('Destination')!='/tmp' for m in info.get('Mounts',[])):
        raise ValueError('Unexpected container mount')
    if host.get('CapDrop')!=['ALL'] or 'no-new-privileges' not in host.get('SecurityOpt',[]):
        raise ValueError('Browser privileges differ')
    if info['Image']!=image or info['Config']['User']!='65534:65534':raise ValueError('Browser identity differs')


def short(value,limit=512):return isinstance(value,str) and len(value)<=limit


def parse_output(data):
    result=json.loads(data.decode('utf-8'),object_pairs_hook=pairs)
    if (not isinstance(result,dict) or set(result)!={'format','checks','runtime','screenshots','page_errors'}
            or result['format']!='pact.metroid-browser-observations/0.1'):
        raise ValueError('Unexpected browser observations')
    runtime=result['runtime']
    if not isinstance(runtime,dict) or set(runtime)!={'chromium','playwright'} or not all(short(v,100) for v in runtime.values()):
        raise ValueError('Invalid browser runtime')
    if not isinstance(result['checks'],list) or not 1<=len(result['checks'])<=50:raise ValueError('Invalid checks')
    for check in result['checks']:
        if (not isinstance(check,dict) or set(check)!={'id','pass','detail'} or not short(check['id'],64)
                or type(check['pass']) is not bool or not short(check['detail'])):raise ValueError('Invalid check result')
    if not isinstance(result['page_errors'],list) or len(result['page_errors'])>10 or not all(short(e) for e in result['page_errors']):
        raise ValueError('Invalid page errors')
    if not isinstance(result['screenshots'],list) or len(result['screenshots'])>2:raise ValueError('Invalid screenshots')
    for shot in result['screenshots']:
        if (not isinstance(shot,dict) or set(shot)!={'id','png_base64'} or not isinstance(shot['id'],str)
                or re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',shot['id']) is None or not isinstance(shot['png_base64'],str)):
            raise ValueError('Invalid screenshot identity')
        png=base64.b64decode(shot['png_base64'],validate=True)
        if len(png)>300000 or not png.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid screenshot bytes')
    return result


def run_candidate(path,image):
    create_command('validation',image)
    if sys.platform!='linux':raise ValueError('Browser adapter requires Linux/Docker')
    source=snapshot(path)
    info=json.loads(control(['docker','image','inspect',image]))[0]
    if info['Id']!=image or info.get('Config',{}).get('Volumes'):raise ValueError('Unexpected browser image')
    name='pact-metroid-'+uuid.uuid4().hex
    try:
        control(create_command(name,image))
        verify_configuration(json.loads(control(['docker','inspect',name]))[0],image)
        payload=json.dumps({'candidate_base64':base64.b64encode(source).decode()}).encode()
        captured=run_bounded(['docker','start','--attach','--interactive',name],payload,timeout=60)
    finally:control(['docker','rm','--force',name])
    reason='output_limit' if captured['output_limited'] else 'timeout' if captured['timed_out'] else 'runtime_error' if captured['returncode'] else None
    observations=None
    if reason is None:
        try:observations=parse_output(captured['stdout'])
        except (ValueError,TypeError,KeyError,RecursionError):reason='invalid_worker_output'
    log={key+'_base64':base64.b64encode(captured[key]).decode() for key in ('stdout','stderr')}
    return {'format':'pact.metroid-pilot-receipt/0.1','candidate_sha256':hashlib.sha256(source).hexdigest(),
            'image_id':image,'observations':observations,'termination_reason':reason,'log':log,
            'log_sha256':hashlib.sha256(json.dumps(log,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'isolation_configuration_checked':True,'formal_benchmark':False,'execution_authenticated':False,
            'candidate_pass':None,'provider_usage':None}


def main():
    manifest=json.loads((PILOT/'manifest.json').read_text());output=ROOT/'build/metroidvania-pilot'
    output.mkdir(parents=True,exist_ok=True);summary=[]
    prompt_hash=hashlib.sha256(snapshot(PILOT/'prompt.txt')).hexdigest()
    if prompt_hash!=manifest['prompt_sha256']:raise ValueError('Prompt identity differs')
    for trial in manifest['trials']:
        if trial['artifact'] not in ('metro_a.html','metro_b.html'):raise ValueError('Unexpected artifact')
        path=PILOT/'candidates'/trial['artifact']
        if hashlib.sha256(snapshot(path)).hexdigest()!=trial['candidate_sha256']:raise ValueError('Candidate identity differs')
        receipt=run_candidate(path,sys.argv[1])
        if receipt['candidate_sha256']!=trial['candidate_sha256']:raise ValueError('Execution identity differs')
        observations=receipt['observations'];checks=observations['checks'] if observations else []
        harness_checks=[check for check in checks if check['id'].startswith('verifier_')]
        if any(not check['pass'] for check in harness_checks):receipt['termination_reason']='verifier_control_failed';checks=[]
        else:checks=[check for check in checks if not check['id'].startswith('verifier_')]
        row={'trial_id':trial['trial_id'],'model_alias':trial['model_alias'],'termination_reason':receipt['termination_reason'],
             'checks':checks,'harness_checks':harness_checks,'checks_passed':sum(check['pass'] for check in checks),'checks_total':len(checks),
             'runtime':observations['runtime'] if observations else None,'candidate_pass':None,'formal_benchmark':False}
        if receipt['termination_reason'] or any(c['id']=='bootstrap' and not c['pass'] for c in checks):
            row['diagnostic_excerpt']=base64.b64decode(receipt['log']['stderr_base64']).decode(errors='replace')[-2000:]
        summary.append(row);print(json.dumps(row),flush=True)
        (output/(trial['trial_id']+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        if observations:
            for shot in observations['screenshots']:
                (output/(trial['trial_id']+'-'+shot['id']+'.png')).write_bytes(base64.b64decode(shot['png_base64']))
    (output/'summary.json').write_text(json.dumps({'image_id':sys.argv[1],'trials':summary},indent=2)+'\n')


if __name__=='__main__':main()
