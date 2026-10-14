# Reference replay

`pact replay` executes a recorded sequence against the numeric reference interpreter. It checks the expected semantic revision before executing calls, starts from declared initial state, and stops at the first runtime trap or evaluation-budget exhaustion. It does not execute Wasm or host-language source.

```sh
python3 -m pact replay examples/counter.checked.pact --record examples/counter.checked.replay.json
```

The example's first call writes 10; its second call fails the chosen precondition. Exit code 2 is expected. Earlier writes remain committed.

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

The hash must equal the validated program's semantic revision; the placeholder above must be replaced. All calls are validated before execution. Only exported functions can be selected, with the exact parameter count and signed-i32 integer arguments; booleans reject. There are 1–64 calls, a single shared budget of 100,000 evaluated nodes, and no initial-state overrides. Helpers retain their own identities when they trap. Evaluation counts describe this reference implementation, not CPU time or Wasm instruction counts.

Source and recording files each use one bounded UTF-8 binary snapshot of at most 1 MiB. Duplicate decoded JSON keys reject. Compact and JSON source formatting can differ while sharing the same semantic revision. Exact source and recording byte hashes are reported separately. No source, recording or output artifact is modified by the command.

## Report and failures

Reports use `pact.replay-report/0.1.0`, identify `engine: reference`, and contain the semantic revision, initial/final state hashes, final state, evaluated-node count and ordered call events. Each event has arguments, either a result or diagnostic, and a hash of the state immediately after that call. State hashes use UTF-8 JSON with sorted keys and compact separators. Repeated calls begin from the preceding call's state; they do not reset implicitly.

| Exit | Meaning | Output |
| --- | --- | --- |
| 0 | Every recorded call completed | Report on stdout with status `completed` |
| 1 | Invalid source, recording, signature or stale revision | Rejection diagnostic on stderr |
| 2 | First runtime trap or reference evaluation limit | Report on stdout with status `trapped` or `limited` |

Runtime diagnostics identify the actual failing function and node: `ASSERTION_FAILED`, `STATE_BOUNDS`, `ARITHMETIC_TRAP`, or `REPLAY_LIMIT`. File reports add a qualified physical definition span when available, using the original source snapshot. These IDs come from reference evaluation, not reconstruction of a Wasm trap. A failed assertion or budget exhaustion does not roll back earlier writes. Bounds checks for stores precede value evaluation, matching the emitted Wasm order.

The input recording is reproducible under this interpreter version and revision. Reports are observations, not authenticated evidence, proof of test adequacy or a sandbox for arbitrary model-generated code. Compiled-Wasm replay, instruction/source mapping, browser-input recording, interactive stepping, negative-trap declarations and authenticated model trials remain pending. Tests compare representative success states and trap-state retention against actual Wasm; that finite comparison is not universal equivalence proof.
