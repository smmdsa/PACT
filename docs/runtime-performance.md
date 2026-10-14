# Local counter runtime benchmark

`python3 -m benchmarks.runtime_performance --require-c` executes the existing trusted `benchmarks/traditional/counter.*` kernels as actual PACT Wasm, Python, JavaScript and C. It needs Node and optionally GCC, plus the repository's standard-library-only compiler. There is no tokenizer or external benchmark dependency. Omitting `--require-c` records C as skipped when GCC is unavailable. No downloaded code is executed.

Each sample runs in a fresh subprocess. The default is 100,000 calls per sample and five samples per runtime. Calls use valid signed-i32 inputs `advance(i % 2, 1)`; each call performs three wrapping additions. Each process first warms up for `min(N, 10000)` calls, then resets the counter to `[2147483646, -2147483647]` outside the timer. Warmup does not guarantee a particular JIT tier.

The internal timers measure the loop and kernel calls: Python `time.perf_counter_ns`, Node `process.hrtime.bigint`, and C `clock_gettime(CLOCK_MONOTONIC)`. PACT invokes the compiled Wasm export from JavaScript on every call, so its JavaScript loop and host bridge are included. Compilation, process startup, module loading, Wasm instantiation, warmup, reset, and final-state reading/checksum/output are excluded. Overall harness wall elapsed time is recorded separately and includes setup. C is built with GCC `-std=c11 -O2 -fno-lto -Wall -Wextra -Werror`, with separate kernel and harness translation units.

Every sample emits both its final state and a consumed checksum, preventing the measured state changes from being discarded. The C kernel is called across translation units without LTO. The parent verifies every final state against a mathematical oracle independent of the implementations: cell 0 receives `3*ceil(N/2)` additions and cell 1 receives `3*floor(N/2)`, reduced modulo 2^32 to signed i32. It also checks the checksum `(3*unsigned(cell0) + unsigned(cell1)) modulo 2^32`. Bounds checking and failure paths are not exercised by this workload.

## Recorded local run

The checked-in [raw report](../benchmarks/results/runtime-local.json) was executed on 2026-10-14 UTC, Linux 6.18.44, x86_64, AMD EPYC 9V74 80-Core Processor, with Python 3.12.14, Node v24.19.0 and GCC 13.3.0. These are observations from this machine and workload, not universal language ranks or production estimates. The report freezes the compiler source hashes at measurement time; later diagnostic/tooling changes may differ from that historical snapshot. Reproduce the command to measure a newer checkout.

| Runtime | Minimum, ms / 100k calls | Median, ms / 100k calls | p95, ms / 100k calls | Median, ns / call |
| --- | ---: | ---: | ---: | ---: |
| PACT Wasm via Node bridge | 2.726 | 2.819 | 3.083 | 28.195 |
| Python | 40.492 | 42.320 | 43.300 | 423.199 |
| JavaScript / Node | 1.589 | 1.687 | 2.475 | 16.869 |
| C / GCC -O2, no LTO | 0.135 | 0.135 | 0.287 | 1.354 |

All 20 samples produced final state `[-2147333650,-2147333647]` and checksum `599995`. The report includes raw sample timings/PIDs, warmup and sample counts, UTC start time, runtime versions, OS/architecture/CPU, complete kernel and harness source hashes, compiler source hashes, generated Wasm/C binary hashes, the Wasm manifest hash, compiler flags, and timing exclusions.

p95 uses nearest rank: sorted sample `ceil(0.95*samples)-1`. With five samples it is the maximum; this small sample does not support a stable tail estimate. No CPU affinity, frequency control or isolation from other workloads is applied. Loop overhead, differing runtime optimizations and possible JIT transitions during measurement affect the observations. Only one tiny chosen kernel is tested; these numbers do not predict full-game execution, startup cost, invalid-input cost, other hardware or equivalent security contracts. Source-token comparisons remain a separate experiment.

## Reproduce and smoke-test

```sh
python3 -m benchmarks.runtime_performance --require-c > benchmarks/results/runtime-local.json
python3 -m benchmarks.runtime_performance --iterations 1000 --samples 2 --require-c
python3 -m unittest tests.test_runtime_performance -v
```

`--iterations` accepts integers from 1 through 10,000,000; `--samples` accepts 1 through 20. Invalid bounds, missing required runtimes, failed execution and oracle mismatches reject the run without emitting a measurement report. Tests verify actual execution, final states/checksums, provenance and errors; they do not assert performance thresholds.
