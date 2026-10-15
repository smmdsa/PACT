# Executable expected-trap cases

Opt-in numeric module `pact.module/0.5.0` adds negative cases to the existing test declarations. A successful build checks every case on the reference machine and actual compiled WebAssembly. Source headers remain independent; module 0.5 inherits the guard/assert operations and per-export case requirement from 0.4.

```sh
python3 -m pact check examples/counter.traps.pact
python3 -m pact build examples/counter.traps.pact -o build/counter.traps.wasm
python3 -m pact migrate examples/counter.checked.pact --to pact.module/0.5.0 -o build/counter.traps.pact
```

The [authored example](../examples/counter.traps.pact) adds seven to a counter, then asserts its input predicate. It includes a normal success, an expected assertion failure and a failure after a custom initial state. Failed assertions retain earlier writes: the final negative case starts at 18 and expects 25 after trapping. Each case starts from a fresh module instance.

## Declaration

```json
{"id":"reject-zero","function":"step","args":[0],"set":{},"expect":{"counter":[10]},"trap":{"code":"ASSERTION_FAILED","function":"step","node":"check"}}
```

`trap` has exactly three fields: `code`, `function` and `node`. Its qualified site may be in an internal helper. Structural checking requires an existing node with a compatible operation:

| Code | Allowed node operations |
| --- | --- |
| `ASSERTION_FAILED` | `flow.assert`, `flow.guard` |
| `STATE_BOUNDS` | `state.load`, `state.store` |
| `ARITHMETIC_TRAP` | `i32.div_s`, `i32.rem_s` |

A trap case cannot declare `result`; it may use an empty `expect` because the trap itself is an assertion. Nonempty `expect` checks the declared prefix of each cell after the trap. `set` overlays the declared prefix before execution; all remaining initial values stay intact. No rollback occurs. Unknown fields/codes/sites, incompatible operations and malformed records reject.

## Exact acceptance and evidence

The reference diagnostic must match all three declared fields. Wasm must raise an actual `WebAssembly.RuntimeError`, and its innermost reported function-index/byte-offset must match the compiler's binary-hash-bound trap map with the same function, node and trap kind. A normal return or another trap fails. An absent/unmatched engine position fails the negative case; generic error messages cannot establish an expected trap. A truncated map can validate only actual sites it contains.

Both engines check state expectations, including after traps. Normal cases still require successful returns and any declared result. Module 0.5 evidence retains `id`/`status` and adds `reference:"tested"` and `wasm:"tested"`; negative cases also record the verified `trap` and actual `wasm_location`. Legacy manifest evidence remains unchanged.

The reference suite has a shared budget of 1,000,000 node evaluations. Exhaustion rejects with `TEST_REFERENCE_LIMIT` and cannot satisfy an expected trap. Node retains the existing 15-second subprocess deadline. Other runtime mismatches reject with `TEST_FAILED`; failed builds and executable patches do not publish candidates.

## Migration and limits

Explicit forward migration to module 0.5 changes only the format and semantic revision. Existing declarations remain, compiled bytes stay identical, and no negative cases are fabricated. Default migration remains 0.2. Formats 0.1–0.4 continue to reject `trap` metadata and retain their existing execution policy. Converting compact/JSON representations preserves the numeric version and qualified IDs.

These checks establish finite case outcomes using the toolchain's own interpreter/compiler and Node engine. They do not establish coverage, independent compiler correctness, authenticated provenance, nominal units or universal safety. Expected-trap builds require supported exact engine coordinates; replay retains its separate generic fallback for unsupported positions. See the [versioned specification](superpowers/specs/2026-10-15-expected-traps.md).
