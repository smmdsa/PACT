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
    baseline_js=Path('benchmarks/agent_trials/counter.mjs').read_text()
    correct_js=baseline_js.replace('i < 3','i < 4')
    for label,source,behavior,policy,reason in [
            ('javascript-baseline',baseline_js,False,False,None),
            ('javascript-edited',correct_js,True,True,None),
            ('javascript-invalid','export const =',False,False,None),
            ('javascript-unapproved',correct_js+'\n// extra comment\n',True,False,None),
            ('javascript-size-limit',correct_js+'/*'+'x'*(1048576-len(correct_js.encode())-4)+'*/',True,False,None),
            ('javascript-noisy',correct_js+'\nconsole.log("noise");\n',False,False,'invalid_worker_output'),
            ('javascript-reset-leak',correct_js.replace('export const counter = [2147483646, -2147483647];',
                'export const counter = globalThis.savedCounter ??= [2147483646, -2147483647];'),False,False,None),
            ('javascript-output-limit','import {writeSync} from "node:fs";\nwhile (true) writeSync(1,"x".repeat(4096));',
                False,False,'output_limit'),
            ('javascript-timeout','await new Promise(resolve => setTimeout(resolve,60000));',False,False,'timeout')]:
        path=root/(label+'.mjs');path.write_text(source)
        result=run_candidate(path,image,language='javascript')
        assert result['grade']['behavior_pass']==behavior,(label,result)
        assert result['policy']['policy_pass']==policy,(label,result)
        assert result['termination_reason']==reason,(label,result)
        assert result['candidate_pass'] is None
        if reason is None:
            assert result['runtime']['engine']=='node' and result['runtime']['node'].startswith('v24.'),(label,result)
        if label=='javascript-reset-leak':
            edited=json.loads((receipts/'javascript-edited.receipt.json').read_text())
            assert result['trace']['cases']==edited['trace']['cases']
            assert result['trace']['reset_case']['counter']!=[-2147483646,-2147483647]
        print(json.dumps({'fixture':label,'behavior_pass':behavior,'policy_pass':policy,'termination_reason':reason,
                          'runtime':result['runtime'],'image_id':image,'model_trial':False}))
        (receipts/(label+'.receipt.json')).write_text(json.dumps(result,sort_keys=True,indent=2))
    baseline_py=Path('benchmarks/agent_trials/counter.py').read_text()
    correct_py=baseline_py.replace('range(3)','range(4)')
    for label,source,expected,reason in [('python-baseline',baseline_py,False,None),
            ('python-edited',correct_py,True,None),('python-invalid','def broken(',False,None),
            ('python-noisy',correct_py+'\nprint("noise")\n',False,'invalid_worker_output'),
            ('python-output-limit','import os\nwhile True: os.write(1,b"x"*4096)\n',False,'output_limit'),
            ('python-timeout','import time\ntime.sleep(60)\n',False,'timeout')]:
        path=root/(label+'.py');path.write_text(source)
        result=run_candidate(path,image,language='python')
        assert result['grade']['behavior_pass']==expected,(label,result)
        assert result['policy']['policy_pass']==expected,(label,result)
        assert result['termination_reason']==reason,(label,result)
        assert result['candidate_pass'] is None
        print(json.dumps({'fixture':label,'behavior_pass':expected,'termination_reason':reason,
                          'image_id':image,'model_trial':False}))
        (receipts/(label+'.receipt.json')).write_text(json.dumps(result,sort_keys=True,indent=2))
