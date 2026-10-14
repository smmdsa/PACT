# Reference and Wasm replay

`pact replay` executes a recorded sequence against the numeric reference interpreter by default. It checks the expected semantic revision before executing calls, starts from declared initial state, and stops at the first runtime trap or evaluation-budget exhaustion. `--engine wasm` executes freshly compiler-produced Wasm in Node. `--engine compare` compares both engines on the same recording; neither mode accepts arbitrary third-party bytecode or evaluates host-language source from a recording.

```sh
python3 -m pact replay examples/counter.checked.pact --record examples/counter.checked.replay.json
python3 -m pact replay examples/counter.checked.pact --record examples/counter.checked.replay.json --engine wasm
python3 -m pact replay examples/counter.checked.pact --record examples/counter.checked.replay.json --engine compare
```

The example's first call writes 10; its second call fails the chosen precondition. Exit code 2 is expected for either individual engine. Comparison exits 0 when both observed traces match, including matching trap/state outcomes. Earlier writes remain committed.

[Source](../examples/counter.checked.pact) · [Recording](../examples/counter.checked.replay.json)

## Recording

A recording is a closed JSON object:

```json
{
  "format": "pact.replay-input/0.1.0",
  "expected_revision_sha256": "SHA-256 from pact symbols",
  "calls": [{"function": "step", "args": []}]
}
```

The hash must equal the validated program's semantic revision; the placeholder above must be replaced. All calls are validated before execution. Only exported functions can be selected, with the exact parameter count and signed-i32 integer arguments; booleans reject. There are 1–64 calls, a single shared reference budget of 100,000 evaluated nodes, and no initial-state overrides. Reference helpers retain their own identities when they trap. Evaluation counts describe this reference implementation, not CPU time or Wasm instruction counts.

Source and recording files each use one bounded UTF-8 binary snapshot of at most 1 MiB. Duplicate decoded JSON keys reject. Compact and JSON source formatting can differ while sharing the same semantic revision. Exact source and recording byte hashes are reported separately. No source, recording or output artifact is modified by the command.

## Report and failures

Reports use `pact.replay-report/0.1.0`, identify `engine: reference`, and contain the semantic revision, initial/final state hashes, final state, evaluated-node count and ordered call events. Each event has arguments, either a result or diagnostic, and a hash of the state immediately after that call. State hashes use UTF-8 JSON with sorted keys and compact separators. Repeated calls begin from the preceding call's state; they do not reset implicitly.

| Exit | Meaning | Output |
| --- | --- | --- |
| 0 | Every recorded call completed | Report on stdout with status `completed` |
| 1 | Invalid source, recording, signature or stale revision | Rejection diagnostic on stderr |
| 2 | First runtime trap or reference evaluation limit | Report on stdout with status `trapped` or `limited` |

Comparison reports use `pact.replay-comparison/0.1.0`, nest both engine reports and return status `matched`, `mismatch` or `incomplete`. Matching checks the source revision, call index/function/arguments, result versus trap outcome, initial state hash, every call's state hash and final state. Trap categories and node identities are deliberately not compared: Wasm retains `WASM_TRAP`, with optional exact compiler trap-site attribution. A limited reference trace yields `incomplete` without executing Wasm. Comparison exit 0 means matching observations; exit 2 means mismatch or incomplete. It does not mean all calls succeeded or prove equivalence for other inputs.

Wasm replay requires Node, uses a fresh instance, and stops at its first trap. It compiles the validated document directly without running declared build cases. The host accepts only its compiler-produced module and generated layout/calls. Source bounds, compiler structural/work limits, at most 64 calls and a 15-second subprocess timeout apply. The reference node budget does not instrument Wasm; a timeout rejects with `REPLAY_TIMEOUT` on stderr and exit 1, with no partial report. Compiled replay binaries are limited to 8 MiB and captured reports to 1 MiB. These are execution limits, not a sandbox or independent bytecode verifier. Reports include Wasm/runtime-script hashes and Node/V8 versions; temporary files are removed after execution. Runtime-script identity describes the captured bytes actually executed.

Runtime diagnostics identify the actual failing function and node: `ASSERTION_FAILED`, `STATE_BOUNDS`, `ARITHMETIC_TRAP`, or `REPLAY_LIMIT`. File reports add a qualified physical definition span when available, using the original source snapshot. Reference IDs come from reference evaluation. Wasm IDs, when present, come from an exact compiler trap-map lookup against the engine-reported function index and absolute byte offset. A failed assertion or budget exhaustion does not roll back earlier writes. Bounds checks for stores precede value evaluation, matching the emitted Wasm order.

The input recording is reproducible under the recorded engine version and revision. Reports are observations, not authenticated evidence, proof of test adequacy or a sandbox for arbitrary model-generated code. Full instruction/source mapping for Wasm, browser-input recording, interactive stepping, negative-trap declarations and authenticated model trials remain pending. Tests compare representative success states and trap-state retention against actual Wasm; that finite comparison is not universal equivalence proof.

## Exact Wasm trap sites

`compile_module_with_traps(plan)` returns byte-identical Wasm plus a separate `pact.wasm-traps/0.1.0` map. The map is bound to the exact binary hash and semantic revision. Positions are zero-based absolute Wasm byte offsets, with function index, qualified node ID and trap-site kind (`assertion`, `bounds`, `arithmetic`). Repeated uses of a definition can produce several instruction sites. The map covers emitted assertion/guard and bounds `unreachable` instructions and signed division/remainder opcodes; it is not an AST, complete instruction map or a list of all runtime outcomes. It does not change IR, revisions or compiled bytes, and ordinary build manifests are unchanged.

Replay extracts the first Wasm frame only when Node's observed stack text includes `wasm-function[INDEX]:0xOFFSET`. It attaches function/node and `trap_site_kind` only for an exact match in the map generated with that binary. It never uses the reference diagnosis to label the Wasm trap. File reports then attach the original source definition span. The engine diagnostic stays `WASM_TRAP`; the compiler category is separate metadata. Node stack formatting is engine/version dependent: missing or unmatched positions retain the generic trap without guessing.

Map collection is capped at 16,384 sites. `trap_map_complete: false` reports truncation; retained sites remain exact, while unrecorded ones cannot be attributed. Tests execute actual Node traps, check helpers and repeated definitions, and verify instruction bytes and byte identity. Eleven numeric examples were also compared against the prior compiler with identical binaries. Further browser/runtime stacks, full instruction coverage and interactive stepping remain pending.
