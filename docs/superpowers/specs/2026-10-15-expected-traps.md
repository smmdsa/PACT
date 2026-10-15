# Expected-trap cases — numeric module 0.5

L1 extends the existing declared-test flow. The goal is executable negative cases that verify the exact failure and retained writes in both the reference machine and actual compiled Wasm. This is finite case evidence, not coverage or proof.

## Version and schema

Opt-in `pact.module/0.5.0` inherits 0.4 operations and the per-export declaration requirement. Source headers remain unchanged. Legacy schemas reject the new field. Default migration remains 0.2; explicit strictly forward migration to 0.5 changes only the numeric format, preserving compiled bytes and existing case declarations.

A test may add `trap:{"code":"ASSERTION_FAILED","function":"step","node":"check"}`. Exactly these three keys are required. Supported codes/sites are `ASSERTION_FAILED` at flow.assert/flow.guard, `STATE_BOUNDS` at state.load/state.store, and `ARITHMETIC_TRAP` at i32.div_s/i32.rem_s. Qualified functions may be internal helpers. Static validation requires that the qualified node exists and has the corresponding operation; execution establishes that the call actually reaches it. A trap case cannot declare `result`. It may use empty `expect`, because the trap is an assertion; nonempty expect retains the existing prefix-of-cell assertion semantics. IDs/arguments/set/expect and export-case rules retain existing bounds.

## Execution

Every case has fresh initial state with its set overlay. For module 0.5, build executes every case on both engines. Negative cases require the reference diagnostic to match code/function/node exactly, and an actual WebAssembly.RuntimeError whose innermost reported function-index/absolute-offset matches a compiler trap-map entry with the expected kind/function/node. The map is bound to the exact compiled binary hash. Normal return, a different trap, missing/unsupported stack coordinates or a mismatched map rejects the build. No message-text guessing or generic-trap acceptance.

Both engines check expected state after the call, including after traps; earlier writes persist and skipped bodies do not execute. Positive cases retain normal return/result/state requirements and reject any trap. Reference evaluation uses one shared 1,000,000-node budget across the suite; exhaustion rejects with TEST_REFERENCE_LIMIT and cannot satisfy an expected trap. Node retains the existing 15-second subprocess deadline. A truncated map may accept a case only when its actual exact trap site is present; unmatched sites fail closed.

Successful 0.5 per-case evidence retains id/status and adds reference/wasm tested labels. Negative Wasm evidence records the verified expected trap plus actual coordinates. Legacy evidence and execution stay unchanged. Build artifacts remain compiler-produced, unauthenticated evidence; unsupported engine coordinates cause rejection of negative cases rather than a false pass.

## Alternatives and scope

Accepting any Wasm trap would confuse failures; engine-message matching is unstable. Requiring exact existing trap maps provides stronger finite evidence without a new debugger subsystem. No runtime instruction change, nominal units, rollback, new exports, external imports or automatic test generation is included.

## Verification

Test legacy rejection and defaults; strict malformed/unknown/wrong-kind trap declarations; positive and negative guard/assert cases; helper attribution; bounds/division/remainder/overflow cases; wrong and unreachable sites; retained writes and fresh instances; mixed positive/negative cases; state/result mismatches; missing stack positions/map hash mismatch; reference budget rejection; all compact representations, migration binary identity, CLI build/patch failure atomicity. Run the full compiler/site suite and existing OS/browser/Docker workflows.
