"""Exercise registered authored alternatives only through the Docker verifier."""
import json
from pathlib import Path
import sys
import tempfile

from benchmarks.agent_candidate_policy import CANONICAL_PROFILE, FORMS_PROFILE, audit_candidate, expected_document
from benchmarks.agent_sandbox import checks_passed, run_candidate
from pact.compact import dumps, loads


ROOT=Path(__file__).resolve().parents[1]
EXTENSIONS={'pact':'pact','python':'py','javascript':'mjs','c':'c'}


def main():
    output=ROOT/'build/sandbox-checks/policy-forms';output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for language,extension in EXTENSIONS.items():
            baseline=(ROOT/'benchmarks/agent_trials'/('counter.'+extension)).read_bytes()
            canonical=(dumps(expected_document()).encode() if language=='pact' else
                       baseline.replace(b'range(3)',b'range(4)') if language=='python' else
                       baseline.replace(b'i < 3',b'i < 4'))
            unrolled=(ROOT/'benchmarks/agent_trials/policy_forms/0.2'/('counter.unrolled.'+extension)).read_bytes()
            if language=='pact':
                changed=loads(unrolled.decode());changed['constants']['unapproved']=0;unapproved=dumps(changed).encode()
            else:
                extra={'python':b'\nunapproved = 0\n','javascript':b'\nconst unapproved = 0;\n','c':b'\nint unapproved = 0;\n'}
                unapproved=unrolled+extra[language]
            assert not audit_candidate(unrolled,language,profile=CANONICAL_PROFILE)['policy_pass']
            for form,source,allowed in [('canonical',canonical,True),('unrolled',unrolled,True),('unapproved',unapproved,False)]:
                path=Path(tmp)/('candidate.'+extension);path.write_bytes(source)
                receipt=run_candidate(path,sys.argv[1],language=language,policy_profile=FORMS_PROFILE)
                (output/(language+'-'+form+'.json')).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
                assert receipt['grade']['behavior_pass'] is True,(language,form,receipt)
                assert receipt['policy']['policy_pass'] is allowed,(language,form,receipt)
                assert receipt['policy_profile']==FORMS_PROFILE
                assert receipt['policy']['accepted_form']==(form if allowed else None)
                assert checks_passed(receipt) is allowed,(language,form,receipt)
                assert receipt['embedded_tests']['pass'] is (True if language=='pact' else None)
                assert receipt['candidate_pass'] is None
                print(json.dumps({'language':language,'form':form,'behavior_pass':True,'policy_pass':allowed,
                                  'contract_sha256':receipt['policy']['contract_sha256'],'model_trial':False}),flush=True)


if __name__=='__main__':main()
