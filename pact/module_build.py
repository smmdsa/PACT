import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from .diagnostics import PactError
from .module import FORMATS, analyze_module
from .module_wasm import compile_module, compile_module_with_traps
from .module_tests import check_reference_tests
from .schema import require


def build_module(document):
    plan=analyze_module(document)
    trap_tests = document['format'] in FORMATS[4:]
    request = {'tests':document['tests'],'layout':plan['layout']}
    if trap_tests:
        check_reference_tests(document)
        binary, trap_map = compile_module_with_traps(plan)
        request.update(trap_map=trap_map, reference_tested=True)
    else:
        binary=compile_module(plan)
    with tempfile.TemporaryDirectory() as directory:
        directory=Path(directory)
        (directory/'module.wasm').write_bytes(binary)
        (directory/'tests.json').write_text(json.dumps(request))
        command=['node',str(Path(__file__).resolve().parents[1]/'tools/check_module.mjs'),str(directory/'module.wasm'),str(directory/'tests.json')]
        try:result=subprocess.run(command,capture_output=True,timeout=15)
        except FileNotFoundError:raise PactError('TEST_RUNTIME_MISSING','Node is required to validate module builds.') from None
        except subprocess.TimeoutExpired:raise PactError('TEST_TIMEOUT','Module tests exceeded 15 seconds.') from None
        if result.returncode:
            try:message=json.loads(result.stderr)['message']
            except (ValueError,KeyError):message=result.stderr.decode(errors='replace')
            raise PactError('TEST_FAILED',message)
        evidence=json.loads(result.stdout)['evidence']
    manifest={'format':'pact.module-artifact/0.1.0','source_sha256':plan['source_sha256'],
        'wasm_sha256':hashlib.sha256(binary).hexdigest(),'layout':plan['layout'],'tiles':plan['tiles'],
        'presentation':document['presentation'],'exports':document['exports'],'constants':document['constants'],
        'evidence':evidence,'work':plan['work']}
    if 'declared_export_tests' in plan:
        manifest['declared_export_tests']=plan['declared_export_tests']
    if 'unit_contracts' in plan:
        manifest['unit_contracts']=plan['unit_contracts']
    return binary,manifest
