# Checked flow contracts: numeric module 0.4

Intent: agents express runtime conditions at explicit execution edges instead of relying on names or commentary. New opt-in numeric format 0.4 inherits module0.3 declared export cases; old versions reject the new operations and retain identical behavior.

Two operations, same ordered `args` schema:
- `flow.assert` (source alias `assert`): one i32 predicate, returns unit. Zero traps; any nonzero signed-i32 value succeeds. No writes of its own.
- `flow.guard` (source alias `guard`): i32 predicate followed by a body expression/action, returns the body's i32/unit type. Evaluates predicate first; zero traps before evaluating the body. Nonzero evaluates the body once and returns its result. This supports pure numeric and action preconditions without changing function ABI.

A postcondition for an action is an assert explicitly sequenced after its writes. Traps preserve earlier writes; there is no rollback, snapshot, recovery or implicit function wrapping. Predicate evaluation may itself trap. Syntactic transitive write inference includes guarded bodies, even if some input skips them. Unit actions retain existing single-use execution edges. Source nodes are evaluated at use; shared pure reads are not snapshots.

Add CHECKED_FORMAT0.4 while FORMAT remains historical default0.2 and TESTED_FORMAT remains0.3. FORMATS extends in increasing order. 0.1 permits original operations; 0.2/0.3 permit reset but reject assert/guard; 0.4 supports both new operations and reset. Forward migration changes only format and preserves Wasm for unchanged bodies; 0.3 export-case validation applies to 0.4. CLI --to gains explicit0.4; default stays0.2.

Reference Machine raises PactError ASSERTION_FAILED with function/node identifiers for a false predicate. Compiled Wasm uses an explicit unreachable trap; current hosts expose generic Wasm runtime failure and cannot identify assertion versus bounds traps or map an instruction back to a node. Do not claim identical trap classification across these engines. Positive and negative tests compare resulting state and trap behavior independently. Build treats any unexpected trap as TEST_FAILED and publishes no new artifact.

No new imports, eval, memory growth, authority or dependencies. Existing source size, depth, graph/effect, repeat and conservative compiler budgets apply. Assertions are runtime checks of chosen conditions, not static proofs, evidence quality, nominal units or universal correctness. Negative-trap test declarations and debugger/replay remain planned; normal declared build cases must succeed.
