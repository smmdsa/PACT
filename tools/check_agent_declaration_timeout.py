"""Verify trace retention after declaration-phase timeout on an authored image."""
import json
from pathlib import Path
import sys
import tempfile

from benchmarks.agent_sandbox import checks_passed, run_candidate


def main():
    baseline=Path('benchmarks/agent_trials/counter.pact').read_text()
    correct=baseline.replace('repeat 3 iteration','repeat 4 iteration').replace(
        '[-2147483647,-2147483647]','[-2147483646,-2147483647]')
    with tempfile.TemporaryDirectory() as tmp:
        source=Path(tmp)/'authored-counter.pact';source.write_text(correct)
        receipt=run_candidate(source,sys.argv[1])
    destination=Path('build/sandbox-checks/declaration-timeout.receipt.json')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    assert receipt['timed_out'] and receipt['termination_reason']=='timeout',receipt
    assert receipt['grade']['behavior_pass'] is True and receipt['policy']['policy_pass'] is True,receipt
    assert receipt['embedded_tests']['status']=='not_run' and receipt['embedded_tests']['pass'] is None,receipt
    assert not checks_passed(receipt) and receipt['candidate_pass'] is None,receipt
    print(json.dumps({'fixture':'declaration-phase-timeout','trace_retained':True,'cli_checks_pass':False,'model_trial':False}))


if __name__=='__main__':main()
