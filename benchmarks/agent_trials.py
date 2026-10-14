"""Prepare immutable trial material; validate and summarize externally measured trials.

Never contacts a model, compiles candidates, executes candidates, or verifies a pass.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MATERIAL = ROOT / 'benchmarks/agent_trials'
LANGUAGES = {'pact':('.pact','PACT compact module source'),
             'python':('.py','Python source'), 'javascript':('.mjs','JavaScript ES module source'),
             'c':('.c','C11 source')}
TASK = 'counter-four'
FIELDS = {'task','language','model','model_version','attempt','pass','latency_ms',
          'input_tokens','output_tokens','provider_usage','settings','seed','budget',
          'order_index','trial_plan_seed','prompt_sha256','context_sha256','candidate_sha256','verifier'}


def material(path, source_format):
    data = path.read_bytes()
    return {'path':str(path.relative_to(ROOT)), 'source_format':source_format,
            'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest(), 'text':data.decode('utf-8')}


def integer(value, name, minimum=0, maximum=None):
    if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'{name}: expected integer in allowed range')


def prepare(language, plan_seed=0):
    if language not in LANGUAGES:
        raise ValueError('unknown language')
    integer(plan_seed,'plan_seed')
    suffix, source_format = LANGUAGES[language]
    order = [{'language':lang,'attempt':attempt} for lang in LANGUAGES for attempt in range(1,6)]
    random.Random(plan_seed).shuffle(order)
    for index, row in enumerate(order,1):
        row['order_index'] = index
    return {'format':'pact.agent-trial-pack/0.1', 'task':TASK, 'language':language,
            'prompt':material(MATERIAL/'prompt.txt','identical UTF-8 user instruction for every language'),
            'context':material(MATERIAL/('counter'+suffix),source_format),
            'oracle_material':material(MATERIAL/'cases.json','independent frozen JSON expectations; verifier-only'),
            'oracle':json.loads((MATERIAL/'cases.json').read_text()),
            'trial_plan_seed':plan_seed, 'trial_order':order, 'fresh_trials_per_language':5,
            'context_policy':'full baseline source only; no oracle, drivers, docs or previous attempts in model context',
            'automated_grading_implemented':False,
            'verifier_requirement':'External independent verifier in a disposable sandbox with no network, credentials or host mounts and explicit CPU/memory/process/output/time limits. Never run untrusted candidates in this recorder.'}


def finite_json(value):
    if value is None or type(value) in (str,bool,int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if isinstance(value,list):
        for item in value: finite_json(item)
        return
    if isinstance(value,dict) and all(isinstance(key,str) for key in value):
        for item in value.values(): finite_json(item)
        return
    raise ValueError('settings/provider usage must contain finite JSON values')


def digest(value, name):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value):
        raise ValueError(f'{name}: expected lowercase SHA-256')


def validate_records(records):
    if not isinstance(records,list):
        raise ValueError('input must be a JSON array of externally measured trial records')
    seen=set()
    for row in records:
        if not isinstance(row,dict) or set(row)!=FIELDS:
            raise ValueError('record has missing or unknown fields')
        if row['task']!=TASK or row['language'] not in LANGUAGES:
            raise ValueError('unknown task or language')
        for name in ('model','model_version'):
            if not isinstance(row[name],str) or not row[name].strip():
                raise ValueError(f'{name}: required nonempty string')
        integer(row['attempt'],'attempt',1,5)
        integer(row['seed'],'seed')
        integer(row['trial_plan_seed'],'trial_plan_seed')
        integer(row['order_index'],'order_index',1,20)
        for name in ('input_tokens','output_tokens'): integer(row[name],name)
        if type(row['pass']) is not bool:
            raise ValueError('pass must be an externally provided boolean')
        latency=row['latency_ms']
        if type(latency) not in (int,float) or not math.isfinite(latency) or latency<0:
            raise ValueError('latency_ms must be finite and nonnegative')
        if not isinstance(row['settings'],dict) or not row['settings']:
            raise ValueError('settings must explicitly record model settings')
        finite_json(row['settings'])
        budget=row['budget']
        if not isinstance(budget,dict) or set(budget)!= {'max_output_tokens','max_latency_ms'}:
            raise ValueError('budget must record both fixed limits')
        for name,value in budget.items(): integer(value,name,1)
        if row['pass'] and (row['output_tokens'] > budget['max_output_tokens'] or
                            row['latency_ms'] > budget['max_latency_ms']):
            raise ValueError('successful trial exceeds declared budget')
        usage=row['provider_usage']
        if not isinstance(usage,dict): raise ValueError('provider_usage must be an object')
        finite_json(usage)
        for name in ('input_tokens','output_tokens'):
            integer(usage.get(name),f'provider_usage.{name}')
            if usage[name]!=row[name]: raise ValueError('provider usage disagrees with recorded tokens')
        verifier=row['verifier']
        if not isinstance(verifier,dict) or set(verifier)!= {'command','revision','log_sha256'}:
            raise ValueError('external verifier provenance is required for every result')
        for name in ('command','revision'):
            if not isinstance(verifier[name],str) or not verifier[name].strip():
                raise ValueError('external verifier command and revision required')
        digest(verifier['log_sha256'],'log_sha256')
        for name in ('candidate_sha256','context_sha256','prompt_sha256'): digest(row[name],name)
        pack=prepare(row['language'],row['trial_plan_seed'])
        for name in ('context','prompt'):
            if row[name+'_sha256']!=pack[name]['sha256']:
                raise ValueError(f'{name} does not match frozen trial material')
        expected=next(item['order_index'] for item in pack['trial_order'] if item['language']==row['language'] and item['attempt']==row['attempt'])
        if row['order_index']!=expected: raise ValueError('order_index disagrees with seeded trial plan')
        key=(row['task'],row['language'],row['model'],row['model_version'],row['attempt'])
        if key in seen: raise ValueError('duplicate trial')
        seen.add(key)
    return records


def summarize(records):
    validate_records(records)
    groups={}
    configurations={}
    paired_seeds={}
    for row in records:
        comparison=(row['task'],row['model'],row['model_version'])
        config={k:row[k] for k in ('settings','budget','trial_plan_seed')}
        serialized=json.dumps(config,sort_keys=True)
        if comparison in configurations and configurations[comparison] != serialized:
            raise ValueError('comparison mixes model settings, budgets or trial plans across languages')
        configurations[comparison]=serialized
        seed_key=(*comparison,row['attempt'])
        if seed_key in paired_seeds and paired_seeds[seed_key] != row['seed']:
            raise ValueError('comparison mixes requested generation seeds for the same attempt')
        paired_seeds[seed_key]=row['seed']
        key=(row['task'],row['language'],row['model'],row['model_version'])
        groups.setdefault(key,[]).append(row)
    result=[]
    for key,rows in sorted(groups.items()):
        config={k:rows[0][k] for k in ('settings','budget','trial_plan_seed')}
        successes=sum(row['pass'] for row in rows)
        tokens=sum(row['input_tokens']+row['output_tokens'] for row in rows)
        result.append(dict(zip(('task','language','model','model_version'),key)) | {
            **config,
            'budget_exceeded_trials':sum(r['output_tokens'] > r['budget']['max_output_tokens'] or
                                        r['latency_ms'] > r['budget']['max_latency_ms'] for r in rows),
            'trials':len(rows), 'successful_trials':successes, 'failed_trials':len(rows)-successes,
            'success_rate':successes/len(rows), 'total_input_tokens':sum(r['input_tokens'] for r in rows),
            'total_output_tokens':sum(r['output_tokens'] for r in rows), 'total_tokens':tokens,
            'tokens_per_successful_task':tokens/successes if successes else None,
            'total_latency_ms':sum(r['latency_ms'] for r in rows),
            'complete_five_trial_group':len(rows)==5})
    return {'format':'pact.agent-trial-summary/0.1','result_origin':'externally supplied; provenance recorded, not authenticated',
            'automated_grading_implemented':False,'groups':result}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare'); prep.add_argument('--language',choices=LANGUAGES,required=True)
    prep.add_argument('--plan-seed',type=int,default=0)
    for command in ('record','summarize'):
        sub.add_parser(command).add_argument('input',help='JSON array file or - for stdin')
    args=parser.parse_args(argv)
    try:
        if args.command=='prepare': report=prepare(args.language,args.plan_seed)
        else:
            source=sys.stdin.read() if args.input=='-' else Path(args.input).read_text(encoding='utf-8')
            rows=json.loads(source)
            report=validate_records(rows) if args.command=='record' else summarize(rows)
        print(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False))
        return 0
    except (ValueError,TypeError,OSError) as error:
        print(json.dumps({'status':'rejected','code':'AGENT_TRIAL_INVALID','message':str(error)}),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
