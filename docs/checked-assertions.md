# Checked conditions in module 0.4

Opt-in numeric module `pact.module/0.4.0` adds explicit runtime conditions. It inherits module 0.3's declared case policy. Numeric module 0.4 and the compact source header pact 0.4 are independent version domains; changing a source header does not opt into these semantics. Earlier numeric versions reject these operations; ordinary loads and source conversion preserve each declared version.

| Node | Arguments | Result | Execution |
| --- | --- | --- | --- |
| `assert` / `flow.assert` | i32 predicate | unit | Zero traps; every nonzero signed-i32 value succeeds |
| `guard` / `flow.guard` | i32 predicate, i32/unit body | Body type | Predicate runs first; false traps before the body; true executes the body once |

```text
nonnegative = i32.ge_s value zero
checked = guard nonnegative value
```

This excerpt returns the original value only when it is nonnegative. It can be a pure numeric function without changing its signature. Assertions can also appear as explicit actions in a `seq`: assert before a write for a precondition, or after the write for a postcondition. The condition is chosen by the author; the compiler checks its type and execution edges, not its truth for every input.

```sh
python -m pact check examples/identity.guarded.pact
python -m pact build examples/identity.guarded.pact -o build/identity.guarded.wasm
python -m pact build examples/counter.checked.pact -o build/counter.checked.wasm
python -m pact migrate examples/counter.tested.pact --to pact.module/0.4.0 -o build/counter.migrated.pact
```

The counter demo guards its initial value of 3, writes the declared amount of 7, then asserts the final value is 10. Repeating it without resetting violates that chosen precondition. Its declared build cases succeed. A forward migration changes only the format, adds no conditions and preserves Wasm when bodies are unchanged; defaults remain 0.1→0.2.

## Failure ordering and state

A failed guard does not evaluate its body. Earlier actions in the enclosing call remain committed: a failed postcondition does **not** roll back prior writes. Predicate evaluation itself may trap before the condition is checked. Writes of a guarded body are still included in conservative transitive effect declarations even when one input skips execution.

References evaluate at use. A shared state-load node is not a snapshot of its first result. Unit effects keep their existing single-use execution-edge restriction; repeats, depth and conservative compiler budgets remain bounded. There is no implicit wrapping, hidden guest import, new capability or memory growth.

Reference `Machine` reports `ASSERTION_FAILED` with function and node identifiers. Compiled Wasm deliberately traps with `unreachable`; legacy build hosts expose a generic runtime trap. Replay can now attach function/node and a compiler trap-site category from an exact Node stack position; missing positions remain generic. Build converts unexpected traps into `TEST_FAILED` and does not publish or overwrite an artifact. Module 0.4 declared build cases must succeed; opt-in 0.5 expected-trap declarations are described below.

Assertions are executable checks of selected conditions, not proofs of correctness, relevant tests, truthful naming or single responsibility. Bounded reference replay now records revision-checked calls and qualified reference failures; see [replay](replay.md). Static nominal units ship in opt-in module 0.6. Authenticated proof, rollback, full instruction mapping and interactive debugger remain planned.

Module 0.5 now supports [expected-trap cases](expected-traps.md) with exact reference/Wasm acceptance and retained-state assertions. Module 0.4 keeps its previous schema and rejects trap metadata.
