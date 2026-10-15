"""Bounded reference acceptance for opt-in module 0.5 declared cases."""
from .diagnostics import PactError
from .reference import Machine
from .schema import require

REFERENCE_TEST_BUDGET = 1_000_000


def check_reference_tests(document):
    remaining = REFERENCE_TEST_BUDGET
    for test in document['tests']:
        machine = Machine(document, evaluation_limit=remaining, runtime_diagnostics=True)
        for cell, values in test['set'].items():
            machine.state[cell][:len(values)] = values
        observed = None
        result = None
        try:
            result = machine.call(test['function'], *test.get('args', []))
        except PactError as error:
            if error.diagnostic['code'] == 'REPLAY_LIMIT':
                raise PactError('TEST_REFERENCE_LIMIT',
                                f"{test['id']}: Reference test suite exceeded {REFERENCE_TEST_BUDGET} node evaluations.") from None
            observed = {key: error.diagnostic.get(key) for key in ('code', 'function', 'node')}
        remaining -= machine.evaluations
        require(observed == test.get('trap'), 'TEST_FAILED',
                f"{test['id']}: Reference trap {observed!r}, expected {test.get('trap')!r}.")
        if 'result' in test:
            require(result == test['result'], 'TEST_FAILED', f"{test['id']}: Reference return value differs.")
        for cell, values in test['expect'].items():
            require(machine.state[cell][:len(values)] == values, 'TEST_FAILED',
                    f"{test['id']}: Reference state {cell} differs.")
