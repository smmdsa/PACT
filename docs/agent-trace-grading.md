# External trace grading

The counter-four experiment has a language-independent grader for **externally supplied observations**. It checks candidate byte identity, the pinned oracle, initial state, all ten ordered calls and the isolated reset case. It never compiles or executes candidate source, calls a model, authenticates a provider or supplies a sandbox.

```sh
python3 -m benchmarks.agent_trace_grader external-trace.json --candidate archived-candidate.pact
```

Use the exact archived source bytes for the language under test. The command reads at most one 1 MiB binary snapshot of each input. Output uses `pact.agent-trace-grade/0.1`, with candidate/oracle/grader hashes, the exact trace-byte hash and executor provenance. Duplicate decoded JSON keys and malformed or oversized inputs reject.

## External trace contract

The executor must return exactly the following fields:

| Field | Required content |
| --- | --- |
| `format`, `task` | `pact.agent-execution-trace/0.1`, `counter-four` |
| `language` | `pact`, `python`, `javascript` or `c` |
| `candidate_sha256` | SHA-256 of the exact submitted candidate bytes |
| `oracle_sha256` | `0013ce376abe55ecf2b0cdbce7612f032d99ec7902778625ef74ec336421c0ae` |
| `executor` | Exactly nonempty `command`, pinned `revision` and SHA-256 `log_sha256` |
| `execution_status` | `completed`, `compile_error`, `error` or `timeout` |
| `initial_counter` | Observed two-i32 state, or `null` when unavailable |
| `cases` | Up to ten ordered observations, each exactly `args`, `status`, `counter` |
| `reset_case` | Isolated reset observation with the same fields, or `null` |

Each `args` contains two signed-i32 integers. An observed counter is two signed-i32 integers or `null` when unavailable. Booleans are not integers. Per-call status is `ok`, `bounds`, `error` or `timeout`; the adapter normalizes language-specific success/bounds behavior. Call order and arguments must match the frozen cases; dropping, reordering or duplicating observations cannot pass. A partially captured trace is allowed and fails behavior grading, preserving its execution status and missing-case count. The reset observation starts from the declared initial values and calls `[0, 1]`.

The grader pins the exact frozen oracle bytes and checks its sequential expectations independently using signed wrapping arithmetic: each valid index receives `4 * amount`; invalid indices retain both counters. A changed oracle rejects rather than silently changing the grading target. Candidate-authored tests or expectations do not decide the behavioral match.

## Meaning and limits

`behavior_pass` is true only for a completed trace with matching initial state, every ordered observation and reset result. Exit 0 means this finite behavioral trace matches; exit 2 means it does not; exit 1 means invalid input or identity. Compilation failures and timeouts fail even if supplied states happen to match.

`candidate_pass` is always `null` and `execution_authenticated` is always false. The report lists unverified requirements: execution isolation, unchanged interface, minimal source edit, dependencies/policies and embedded-test correctness. Executor command, revision and log hashes are external claims; the grader does not run the command or read the log archive. A forged matching trace can pass behavior grading, even alongside syntactically invalid candidate bytes. Tests explicitly cover that distinction. Do not copy `behavior_pass` into a model trial's `pass` without the remaining independent checks.

The [trial recorder](agent-evaluation.md) remains a separate provenance/measurement recorder. Its existing formats, frozen task material and `automated_grading_implemented: false` flag are unchanged because full candidate grading remains external. Synthetic unit-test observations are not model measurements. The [Docker PACT/Python/JavaScript/C counter adapters](agent-sandbox.md) now produce these traces with fixed container workers. The adapters also add separate restricted IR/AST/exact-source policies for PACT/Python/JavaScript/C; these do not change this trace-only grade. Broader language adapters/policies, provider integration and real model runs remain pending.
