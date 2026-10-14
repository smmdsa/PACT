# Traditional-language comparison

PACT uses **more source tokens in all eight language/task comparisons below**. These measurements are real `tiktoken 0.12.0` counts of frozen files, with actual execution of PACT WebAssembly, Python, JavaScript and compiled C. They measure two small kernels, not agent productivity, overall language quality or total model task cost.

| Task | Language | Source bytes | `o200k_base` tokens | `cl100k_base` tokens |
| --- | --- | ---: | ---: | ---: |
| Exact greeting | PACT | 270 | 78 | 80 |
| Exact greeting | Python | 44 | 10 | 11 |
| Exact greeting | JavaScript | 51 | 11 | 12 |
| Exact greeting | C | 101 | 27 | 28 |
| Wrapping counter | PACT | 596 | 163 | 163 |
| Wrapping counter | Python | 236 | 74 | 73 |
| Wrapping counter | JavaScript | 252 | 76 | 76 |
| Wrapping counter | C | 381 | 138 | 138 |

Sources are ordinary short implementations in [benchmarks/traditional](../benchmarks/traditional/). PACT greeting uses one literal rather than an unnecessary concatenation. C uses portable defined wrapping arithmetic; Python explicitly wraps arbitrary-precision integers; JavaScript uses its native signed 32-bit coercion. No traditional source is padded with PACT-like declarations to manufacture a result. The previously reported compact-PACT-versus-JSON savings answer a different representation question and do not show an advantage over these languages.

## Tasks and independent oracle

The greeting emits exactly `hola mundo, from an alien language` plus a single LF, without extra stdout or stderr. All four programs execute and compare their exact stdout bytes against the frozen value in [cases.json](../benchmarks/traditional/cases.json).

The counter starts with two signed i32 cells `[2147483646, -2147483647]`. Each `advance(index, amount)` performs exactly three sequential wrapping additions to the selected cell. Valid indices are 0 and 1. Invalid indices must fail before modifying either cell. Drivers normalize the error mechanism to `bounds`: PACT traps, Python/JavaScript throw, and C returns failure. That normalization measures observable behavior, not equivalence of error mechanisms or safety guarantees.

Each row below is an input call followed by the frozen expected state. The trace records both cells after **every** call, so an unexpected surviving write, including a partial write before a bounds error, is observable. Expectations are literals, not generated using PACT or any tested implementation.

| Index | Amount | Status | Expected state after call |
| ---: | ---: | --- | --- |
| 0 | 1 | ok | `[-2147483647, -2147483647]` |
| 1 | -1 | ok | `[-2147483647, 2147483646]` |
| 0 | -2 | ok | `[2147483643, 2147483646]` |
| 1 | -2147483648 | ok | `[2147483643, -2]` |
| -1 | 5 | bounds | `[2147483643, -2]` |
| 2 | 5 | bounds | `[2147483643, -2]` |
| 2147483647 | 5 | bounds | `[2147483643, -2]` |
| -2147483648 | 5 | bounds | `[2147483643, -2]` |

For example, `2147483646 + 3 = 2147483649`, represented as `-2147483647` modulo 2³². Similarly, `-2147483647 - 3 = -2147483650` wraps to `2147483646`, and `2147483646 + 3×(-2147483648)` wraps to `-2`. Python's `(value + 2**31) % 2**32 - 2**31` also handles negative intermediate values. C first adds unsigned i32 values, then converts using a representable signed i64 subtraction; it does not depend on signed-overflow undefined behavior or out-of-range unsigned-to-signed casts.

Calls use only signed-i32 integer inputs. Fractional numbers, strings and out-of-range host inputs are outside the comparison. The four valid calls and four bounds cases do not establish correctness for every input. They also do not measure division/remainder semantics, timing or performance. A regression deliberately changes Python's three updates to two and checks that the independent oracle rejects it.

## Measurement boundary and overhead

Every language's source count includes its complete UTF-8 file, all whitespace and its final newline. Files are neither minified nor selectively stripped. The report records bytes, tokens and SHA256 for each source. `encode_ordinary` counts special-token-looking text as source. Nothing here treats bytes as tokens.

The greeting sources include their output call. They execute directly in Python, Node and C; PACT requires its existing granted stdout host. Counter files contain the implementation and initial state; separate drivers supply the same input pairs and print the trace. Those drivers are counted separately:

| Task | Driver | `o200k_base` tokens | `cl100k_base` tokens |
| --- | --- | ---: | ---: |
| Greeting | Existing PACT stdout host, `host/run.mjs` | 849 | 840 |
| Greeting | Python / JavaScript / C | 0 | 0 |
| Counter | PACT Wasm loader and trace driver | 170 | 162 |
| Counter | Python trace driver | 60 | 59 |
| Counter | JavaScript trace driver | 108 | 106 |
| Counter | C trace driver | 123 | 123 |

Zero denotes no separate user-authored driver file, not a free language runtime. The common Python orchestration harness, shared frozen input/oracle file and PACT module-test runner are also measured independently in the JSON reports. Installed compiler/interpreter/runtime binaries and libraries are excluded for all languages. Input parsing is driver overhead: the harness serializes frozen signed integers as text pairs, and each driver reads those pairs. Generated Wasm and manifests are outputs, not source-token inputs.

PACT carries additional checked policy and metadata: greeting responsibility/effects and an exact-output contract; counter write declaration, assets/presentation metadata and one declared positive-wrap test. Reports annotate the exact complete declaration lines as an **overlapping subset** of the source: greeting 34/35 tokens and counter 53/53 tokens for `o200k_base`/`cl100k_base`. These counts are descriptive, not a removable-cost estimate. Tokenization across concatenated boundaries is not additive; never subtract this subset from total source tokens or add separately tokenized source/driver counts as an exact combined prompt count.

Traditional sources include the explicit bounds/wrapping behavior needed for this task, but do not replicate PACT's static write checking, fixed memory and expansion budgets, absence of arbitrary guest imports, or build-time declared contracts/tests. PACT's greeting also requires an explicit stdout grant. The independent fixture check is shared benchmark validation, while PACT's source-level contract/test is an additional asymmetrical policy. Equal traces do not establish equal capabilities, tests, safety or security contracts. Conversely, larger PACT token counts do not quantify the value of those checks.

## Reproduction

Install the optional tokenizer dependencies, then run from the repository root:

```sh
python3 -m pip install -r benchmarks/requirements.txt
python3 -m benchmarks.traditional --encoding o200k_base --require-c
python3 -m benchmarks.traditional --encoding cl100k_base --require-c
python3 -m unittest tests.test_traditional -v
```

`--encoding` accepts the two pinned baseline encoding names. Reports print to stdout only after every available implementation matches its own frozen expected trace. Failures print a rejected diagnostic to stderr and exit nonzero. Node is required. C uses `gcc -std=c11 -Wall -Wextra -Werror -O2`; without gcc, the default records both C executions as `skipped` while still reporting their source sizes. `--require-c` makes absent gcc a failure for CI. No comparison row is silently omitted.

Frozen [o200k_base](../benchmarks/results/traditional-o200k_base.json) and [cl100k_base](../benchmarks/results/traditional-cl100k_base.json) reports were generated with Python 3.12.14, Node v24.19.0 and GCC 13.3.0. All eight executions verified in each run. Reports include runtime versions and source/driver hashes; they are reproducible for those files and tokenizer resources, rather than promises of invariant counts after future source changes.

These two chosen kernels are intentionally small and are **not representative of the full Alien Harvest game**. No whole-game translation or real-model editing/debugging trial was run. Broader claims about model cost, task efficiency or productivity remain untested.
