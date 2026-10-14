"""Docker integration checks with authored fixtures, never model measurements."""
import json
from pathlib import Path
import sys
import tempfile

from benchmarks.agent_sandbox import run_candidate

image=sys.argv[1]
receipts=Path('build/sandbox-checks');receipts.mkdir(parents=True,exist_ok=True)
baseline=Path('benchmarks/agent_trials/counter.pact').read_text()
correct=baseline.replace('repeat 3 iteration','repeat 4 iteration').replace(
    '[-2147483647,-2147483647]','[-2147483646,-2147483647]')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    for label,source,expected,policy in [('baseline',baseline,False,False),('edited',correct,True,True),
            ('invalid','broken',False,False),
            ('unapproved',correct.replace('positive.wrap','renamed.test'),True,False)]:
        path=root/(label+'.pact');path.write_text(source)
        result=run_candidate(path,image)
        assert result['grade']['behavior_pass']==expected,(label,result)
        assert result['policy']['policy_pass']==policy,(label,result)
        assert result['candidate_pass'] is None
        print(json.dumps({'fixture':label,'behavior_pass':expected,'policy_pass':policy,'image_id':image,'model_trial':False}))
        (receipts/(label+'.receipt.json')).write_text(json.dumps(result,sort_keys=True,indent=2))
