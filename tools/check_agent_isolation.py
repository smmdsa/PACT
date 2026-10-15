"""Observe finite Docker attacks using the exact counter isolation profile."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import uuid

from benchmarks.agent_sandbox import cleanup_container, control, create_command, verify_configuration
from benchmarks.bounded_process import run_bounded

PROBES=('filesystem','network','file_size','temporary_space','processes','cpu','memory','output','wall_time')


def probe_passed(name,result):
    if not result['started'] or not result['cleanup_verified']:return False
    if name=='memory':return (result['state'].get('OOMKilled') is True and result['state'].get('Running') is False
                             and result['returncode']==137 and not result['timed_out'])
    if name=='output':return result['output_limited'] and result['captured_bytes']<=1048576
    if name=='wall_time':return result['timed_out']
    observed=result['observation']
    if not isinstance(observed,dict) or observed.get('probe')!=name or observed.get('stage')!='finished':return False
    if result['returncode']!=0 or result['timed_out'] or result['output_limited'] or observed.get('denied') is not True:return False
    if name=='filesystem':return observed.get('interpreted_control') is True
    if name=='network':return observed.get('loopback_control') is True and observed.get('interfaces')==['lo']
    return True


def run_probe(name,image,host_sentinel):
    container='pact-probe-'+uuid.uuid4().hex
    command=create_command(container,image);command[-1]='/opt/isolation_probes.py'
    started_at=time.monotonic();raw=None
    result={'format':'pact.isolation-probe/0.1','probe':name,'image_id':image,'container':container,
            'started':False,'observation':{},'state':{},'cleanup_verified':False,
            'returncode':None,'timed_out':False,'output_limited':False,'captured_bytes':0,'log':{}}
    try:
        control(command);info=json.loads(control(['docker','inspect',container]))[0]
        verify_configuration(info,image)
        raw=run_bounded(['docker','start','--attach','--interactive',container],
                        json.dumps({'probe':name,'host_sentinel':str(host_sentinel)}).encode())
        result['state']=json.loads(control(['docker','inspect',container]))[0]['State']
    except Exception as error:result['infrastructure_error']=str(error)
    finally:
        try:cleanup_container(container);result['cleanup_verified']=True
        except Exception as error:result['cleanup_error']=str(error)
    if raw is not None:
        lines=raw['stdout'].splitlines()
        try:result['started']=json.loads(lines[0])=={'probe':name,'stage':'started'}
        except (ValueError,IndexError):pass
        if len(lines)==2:
            try:result['observation']=json.loads(lines[1])
            except ValueError:pass
        result.update({key:raw[key] for key in ('returncode','timed_out','output_limited')})
        result['captured_bytes']=len(raw['stdout'])+len(raw['stderr'])
        result['log']={key+'_base64':base64.b64encode(raw[key]).decode() for key in ('stdout','stderr')}
    result['elapsed_seconds']=time.monotonic()-started_at
    result['pass']=not result.get('infrastructure_error') and probe_passed(name,result)
    return result


def main():
    image=sys.argv[1];create_command('validation',image)
    info=json.loads(control(['docker','image','inspect',image]))[0]
    if info['Id']!=image or info.get('Config',{}).get('Volumes'):raise ValueError('Unexpected probe image')
    output=Path('build/sandbox-checks/isolation');output.mkdir(parents=True,exist_ok=True)
    reports=[]
    with tempfile.TemporaryDirectory(prefix='pact-host-sentinel-') as tmp:
        sentinel=Path(tmp)/'sentinel';sentinel.write_text('authored non-secret control')
        for name in PROBES:
            try:report=run_probe(name,image,sentinel)
            except Exception as error:report={'probe':name,'pass':False,'infrastructure_error':str(error)}
            reports.append(report);(output/(name+'.json')).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
            print(json.dumps({key:report.get(key) for key in ('probe','pass','started','returncode','timed_out','output_limited')}),flush=True)
        absent='pact-probe-'+uuid.uuid4().hex
        # A real daemon error for an absent container must propagate, never certify cleanup.
        try:cleanup_container(absent);cleanup={'probe':'cleanup_failure','pass':False}
        except ValueError as error:
            cleanup={'probe':'cleanup_failure','pass':'No such container' in str(error),'error':str(error)}
        reports.append(cleanup);(output/'cleanup_failure.json').write_text(json.dumps(cleanup,indent=2)+'\n')
    summary={'format':'pact.isolation-probe-suite/0.1','image_id':image,'model_trial':False,
             'probe_source_sha256':hashlib.sha256(Path('benchmarks/sandbox/isolation_probes.py').read_bytes()).hexdigest(),
             'pass':all(row['pass'] for row in reports),'results':[{'probe':row['probe'],'pass':row['pass']} for row in reports]}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True),flush=True)
    if not summary['pass']:raise SystemExit('Isolation probes failed; inspect retained observations')


if __name__=='__main__':main()
