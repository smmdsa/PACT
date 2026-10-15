"""Re-evaluate archived exploratory model responses only through Docker."""
import hashlib
import json
from pathlib import Path
import sys

from benchmarks.agent_sandbox import run_candidate
from benchmarks.agent_trace_grader import snapshot

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'benchmarks/subagent_pilots/2026-10-15-counter'
EXTENSIONS={'pact':'pact','python':'py','javascript':'mjs','c':'c'}


def archived(path):
    selected=(ROOT/path).resolve()
    if not selected.is_relative_to(ARCHIVE):raise ValueError('Path outside pilot archive')
    return snapshot(selected)


def validate_pilot(manifest):
    if manifest['format']!='pact.subagent-pilot/0.1' or manifest['formal_benchmark'] is not False:
        raise ValueError('Expected exploratory pilot')
    prefix=(ARCHIVE/'input-prefix.txt').read_bytes()
    for row in manifest['trials']:
        baseline=snapshot(ROOT/('benchmarks/agent_trials/counter.'+EXTENSIONS[row['language']]))
        if hashlib.sha256(baseline).hexdigest()!=row['baseline_sha256']:raise ValueError('Baseline identity differs')
        for field in ('input','response','candidate'):
            if hashlib.sha256(archived(row[field+'_path'])).hexdigest()!=row[field+'_sha256']:
                raise ValueError('Archived '+field+' identity differs')
        if archived(row['input_path'])!=prefix+baseline:raise ValueError('Trial input differs')
        if archived(row['candidate_path'])!=archived(row['response_path'])+b'\n':
            raise ValueError('Candidate extraction differs')
    for row in manifest['excluded_attempts']:
        for field in ('input','response'):
            if hashlib.sha256(archived(row[field+'_path'])).hexdigest()!=row[field+'_sha256']:
                raise ValueError('Excluded '+field+' identity differs')
    return manifest


def load_pilot():
    return validate_pilot(json.loads((ARCHIVE/'manifest.json').read_text()))


def main():
    manifest=load_pilot();output=ROOT/'build/subagent-pilot';output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for trial in manifest['trials']:
        receipt=run_candidate(ROOT/trial['candidate_path'],sys.argv[1],language=trial['language'])
        if receipt['trace']['candidate_sha256']!=trial['candidate_sha256']:raise ValueError('Execution identity differs')
        row={'trial_id':trial['trial_id'],'model_alias':trial['model_alias'],'language':trial['language'],
             'behavior_pass':receipt['grade']['behavior_pass'],'policy_pass':receipt['policy']['policy_pass'],
             'candidate_pass':None,'formal_benchmark':False,'provider_usage':None}
        rows.append(row);print(json.dumps(row),flush=True)
        (output/(trial['trial_id']+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps({'format':'pact.subagent-pilot-results/0.1',
        'image_id':sys.argv[1],'excluded_attempts':len(manifest['excluded_attempts']),'trials':rows},indent=2)+'\n')


if __name__=='__main__':main()
