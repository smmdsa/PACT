"""Timed calls to the trusted Python counter; startup and warmup excluded."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from time import perf_counter_ns

source = Path(__file__).resolve().parents[1] / 'traditional/counter.py'
spec = importlib.util.spec_from_file_location('trusted_counter', source)
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)
n, warmup = map(int, sys.argv[1:])
for i in range(warmup):
    kernel.advance(i % 2, 1)
kernel.counter[:] = [2147483646, -2147483647]
start = perf_counter_ns()
for i in range(n):
    kernel.advance(i % 2, 1)
elapsed = perf_counter_ns() - start
state = kernel.counter
checksum = (3 * (state[0] & 0xffffffff) + (state[1] & 0xffffffff)) & 0xffffffff
print(json.dumps({'elapsed_ns': elapsed, 'state': state, 'checksum': checksum, 'pid': os.getpid()}))
