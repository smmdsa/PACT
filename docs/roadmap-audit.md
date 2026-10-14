# Roadmap audit — 2026-10-14

This audit checks repository implementation and tests, not just changelog claims. Baseline: main commit `882a630` (PR #15). The accompanying increment adds the restricted PACT counter source policy described below. Historical CI results establish specific executions; existing tests and source establish scope, not universal correctness or a representative model advantage.

## Implemented scope and evidence

| Area | Implementation and checks | Verified limit |
| --- | --- | --- |
| Text kernel and capability host | `pact/graph.py`, `pact/wasm.py`, `host/profile.mjs`; `tests/test_graph.py`, `tests/test_execution.py` | Small static text/effect profile; numeric modules have a different host profile |
| Numeric state and game | `pact/module.py`, `pact/module_wasm.py`, `pact/reference.py`, `tools/playthrough.mjs`; module/game tests | i32/unit and fixed arrays; no nominal units, general imports or recursion |
| Source representations | `pact/compact.py`, `pact/data_codec.py`, `pact/atlas_codec.py`; compact/compression/literal tests | Representation versions remain distinct from numeric semantic versions |
| Token and traditional baselines | `benchmarks/token_counts.py`, `benchmarks/traditional.py`, frozen JSON reports and tests | Two chosen kernels and source encodings; no demonstrated model productivity advantage |
| Parser/read bounds | Cursor parsing, bounded snapshots and `tests/test_resource_bounds.py` | These bounds do not prove arbitrary host-code containment or all peak-memory limits |
| Runtime benchmark | `benchmarks/runtime_performance.py`, frozen runtime report and tests | Chosen local counter workload with warmup, fresh samples and oracle; not a universal speed ranking |
| Selective inspection | `pact/inspection.py`, inspection CLI/tests | Numeric modules only; helper bodies/state/test bodies can be omitted explicitly |
| Revision-checked edits | `pact/transactions.py`, `pact/transaction_io.py`, patch/transaction tests | New candidate publication; no in-place filesystem compare-and-swap |
| Contracts | Module 0.3 export-case declarations, 0.4 guard/assert checking; export-evidence/assertion tests | Case presence and executed examples are not coverage proofs or nominal units |
| Locations and replay | `pact/source_locations.py`, `pact/replay.py`, compiler trap maps; location/replay tests | Definition spans and selected trap opcodes; no full instruction/source map or interactive debugger |
| Portability | OS matrix, Chromium smoke, Node input-only game playthrough | No Firefox/WebKit, physical-device run or full browser victory evidence |
| Trial material and recorder | `benchmarks/agent_trials.py`, frozen prompt/contexts/oracle; recorder tests | Records external claims; no provider requests or real trial-result dataset |
| Trace grading | `benchmarks/agent_trace_grader.py`, trace-grader tests | Finite external observations; `candidate_pass` stays null and execution is unauthenticated |
| Isolated counter execution | `benchmarks/agent_sandbox.py`, `benchmarks/sandbox/worker.py`, dedicated Docker CI | Linux/Docker, PACT reference interpreter and one task; other languages and adversarial containment probes absent |
| Restricted source policy (this increment) | `benchmarks/agent_candidate_policy.py`, policy tests and container fixtures | Canonical counter-four IR edit only; not a general minimal-diff or intent verifier |
| Public documentation | `tools/markdown_docs.py`, `tools/build_site.py`, documentation tests and Pages workflow | Generated Markdown pages; deployment must be checked separately from local build |

## Confirmed unfinished work

| ID | Priority | Missing implementation / evidence | Completion criterion |
| --- | --- | --- | --- |
| E1 | Next | Docker candidate adapters for Python, JavaScript and C | Same frozen calls and reset, bounded isolated execution and archived pass/failure receipts for each language; no trusted local performance-driver fallback |
| E2 | Next | Broader source-policy verification and embedded-test execution | Pre-registered allowed changes, preserved interfaces/policies, actual embedded tests and negative fixtures; report policy asymmetries across languages |
| E3 | Next | Adversarial execution-limit probes | Demonstrate timeout/CPU, memory, output, process, filesystem and network denials on the deployed backend, retaining failed observations and cleanup evidence |
| E4 | After E1–E3 | Provider integration and real trials | Pinned provider/model/settings, fresh paired trials, actual usage, failed attempts/retries/tool overhead and archived raw candidates/responses; credentials/backend must be configured |
| E5 | After initial trials | More tasks and retrieval/repair experiments | Pre-register multiple tasks and oracles, full-source vs selected context and repair budgets; do not generalize from counter-four alone |
| L1 | Planned | Negative-trap case declarations | Versioned test schema, reference/Wasm acceptance for expected traps, state-after-trap semantics and migration compatibility |
| L2 | Planned | Nominal units and stronger contracts | Versioned type/contract specification and enforcement; reject incompatible units with independent tests |
| D1 | Planned | Full instruction maps and interactive debugger | Define mapping/stepping semantics, bounded trace or breakpoint state and actual engine tests; retain generic fallback when unsupported |
| D2 | Planned | Physical source editing and in-place CAS | Specify exact-byte identity, stale-file races and failure atomicity; current semantic patch/new-file flow remains valid |
| P1 | Planned | Other browser engines and real devices | Executed Firefox/WebKit/device runs, browser victory and audio/mobile checks with artifacts |
| S1 | Planned | Versioned standard library | Actual reusable math/color/input modules and import/link/version/effect semantics; built-in opcodes are not a library |
| R1 | Planned | Wider runtime/build measurements | More workloads, compile cost/peak memory and hardware/toolchain-controlled comparisons |
| X1 | Owner decision + implementation | License and reproducible releases | Owner chooses licensing; add reproducible packaging, pinned toolchains/dependencies and release verification. No license file or release workflow currently supplies this |

No provider SDK/client or real trial records exist in the current benchmark path. The Dockerfile uses a mutable base tag for building; a runtime image ID pins execution but does not make rebuilding reproducible. The initial sandbox inspects selected Docker settings and tests authored fixtures; hostile containment testing remains E3.

## Corrections made to the roadmap and guidance

- Narrowed “Resource bounds” to parser/benchmark-read bounds and selective inspection to numeric modules.
- Separated implemented replay and exact trap mapping from unfinished full instruction maps/debugger.
- Made the partial model-evaluation pipeline explicit instead of treating a trace match as full candidate approval.
- Corrected stale security/guidance text claiming Wasm replay lacks all source attribution, and clarified that a false guard traps before its body rather than returning normally.
- Preserved completed source/kernel milestones and owner-only license choice. The new policy completes only a restricted part of E2; it does not mark real trials complete.

## Immediate development choice

The canonical counter-four policy permits exactly the frozen numeric IR with `advance`'s `repeat.count` changed from 3 to 4 and `positive.wrap`'s expected state updated from the independent oracle. Every other semantic field, ID, order, version, interface, initial cell, write declaration, asset and test declaration must remain unchanged. Compact/JSON representation and line-ending differences may preserve that same IR.

This intentionally strict acceptance rule can reject another behaviorally correct rewrite. It does not measure textual diff minimality or authorize claiming a language-neutral policy comparison. Receipts expose `policy_pass` separately from `behavior_pass`; `candidate_pass` remains null. Candidate function bodies are not executed by the policy checker: it uses only bounded parsing and static semantic validation.
