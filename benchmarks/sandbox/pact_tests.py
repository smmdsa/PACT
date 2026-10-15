"""Execute PACT declarations in the container; never import candidate host code."""
import sys
from pact.diagnostics import PactError
from pact.module_build import build_module


def execute_declared_tests(document):
    count=len(document['tests'])
    report={'engine':'wasm','status':'missing','declared':count,'executed':0,
            'pass':False,'reason':'NO_DECLARED_TESTS'}
    if not count:return report
    try:
        _,manifest=build_module(document)
    except PactError as error:
        print(error.diagnostic['message'][:512],file=sys.stderr)
        report.update(status='failed',executed=None,reason=error.diagnostic['code'])
        return report
    report.update(status='passed',executed=len(manifest['evidence']),**{'pass':True,'reason':None})
    return report
