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
| Isolated counter execution | `benchmarks/agent_sandbox.py`, `benchmarks/sandbox/worker.py`, dedicated Docker CI | Linux/Docker, PACT reference interpreter, Python, JavaScript and C, one task; wider adversarial containment probes remain absent |
| Restricted source policies | `benchmarks/agent_candidate_policy.py`, policy tests and container fixtures | Canonical counter-four IR/AST edits and exact JavaScript/C source edits only; not a general minimal-diff or intent verifier |
| Public documentation | `tools/markdown_docs.py`, `tools/build_site.py`, documentation tests and Pages workflow | Generated Markdown pages; deployment must be checked separately from local build |

## Backlog status and completion criteria

| ID | Priority | Missing implementation / evidence | Completion criterion |
| --- | --- | --- | --- |
| E2 | Done for frozen counter task | Default strict policy plus opt-in registered loop/unrolled forms in four languages; PACT embedded tests execute on Wasm in Docker | Pre-registered allowed changes, preserved interfaces/policies, actual embedded tests and negative fixtures; report policy asymmetries across languages |
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

No provider SDK/client or formal provider-trial records exist in the current benchmark path. An eight-response exploratory GPT subagent pilot is now archived separately; it has no provider usage, immutable model version or statistical ranking. The Dockerfile uses a mutable base tag for building; a runtime image ID pins execution but does not make rebuilding reproducible. The sandbox inspects selected Docker settings and tests authored fixtures plus Python/JavaScript/C output/timeout, JavaScript reset-leak and C fresh-process reset/crash probes; broader hostile containment testing remains E3.

## Corrections made to the roadmap and guidance

- Narrowed “Resource bounds” to parser/benchmark-read bounds and selective inspection to numeric modules.
- Separated implemented replay and exact trap mapping from unfinished full instruction maps/debugger.
- Made the partial model-evaluation pipeline explicit instead of treating a trace match as full candidate approval.
- Corrected stale security/guidance text claiming Wasm replay lacks all source attribution, and clarified that a false guard traps before its body rather than returning normally.
- Preserved completed source/kernel milestones and owner-only license choice. The new policy completes only a restricted part of E2; it does not mark real trials complete.

## Immediate development choice

The canonical counter-four policy permits exactly the frozen numeric IR with `advance`'s `repeat.count` changed from 3 to 4 and `positive.wrap`'s expected state updated from the independent oracle. Every other semantic field, ID, order, version, interface, initial cell, write declaration, asset and test declaration must remain unchanged. Compact/JSON representation and line-ending differences may preserve that same IR.

This intentionally strict acceptance rule can reject another behaviorally correct rewrite. It does not measure textual diff minimality or authorize claiming a language-neutral policy comparison. Receipts expose `policy_pass` separately from `behavior_pass`; `candidate_pass` remains null. Candidate function bodies are not executed by the policy checker: it uses only bounded parsing and static semantic validation.

JavaScript now has a Node 24 container worker and a separate exact-source policy: only `i < 3` → `i < 4`, with CRLF normalization, is allowed. Unlike the PACT IR and Python AST policies, it rejects comment/format changes. Receipts 0.4 record unauthenticated Node/V8 observations separately from the common trace. Broader policies remain unfinished. PACT declaration execution is implemented in receipt 0.6; other task languages have no declaration interface.

E1 is now implemented for all four frozen languages: C compiles and executes only in Docker, with compiler diagnostics, GCC metadata and fresh-process reset. Receipt 0.5 adds C selection. The C exact-source policy is as strict as JavaScript's; this completes adapter coverage for one task, not E2/E3 or actual model evaluation. Native execution uses a bounded Linux memfd while `/tmp` remains noexec. E2 and E3 remain the next acceptance gates before real provider trials.

The exploratory GPT pilot covers two requested model aliases and four languages, with one valid response each plus one retained coordinator-input error. It exercises the evaluation pipeline but does not complete E4: provider-controlled settings/version/usage, repeated trials and pre-registration remain missing. See the evaluation protocol for exact limitations.

A second exploratory task now requests a five-room Metroidvania in HTML/JavaScript from both GPT aliases. Original playable artifacts, a fixed contract and independent browser observations broaden the pilot task scope without completing E4/E5 or comparing PACT to JavaScript.


## E2 increment — 2026-10-15

The PACT counter worker now executes the candidate's declared cases through actual compiled Wasm inside Docker, separately from reference-interpreter observations and source-policy checks. Receipt 0.6 reports passed/failed/missing/not-run states; Python/JavaScript/C explicitly report not-applicable. CLI success for PACT requires all three checks. Negative fixtures preserve a matching external trace while rejecting wrong expected values, missing declarations and declared traps. This closes declaration execution for the current PACT task, not broader source policies, equivalent test interfaces across languages, authenticated evaluation or E2 as a whole.


## E2 registered-form completion — 2026-10-15

An opt-in `counter-four-forms/0.2` contract now binds canonical and unrolled implementations for each frozen language. PACT compares full validated semantic revisions, Python full AST fingerprints, and JavaScript/C exact normalized-source fingerprints. Unrelated changes remain rejected, including behaviorally matching additions. The default canonical profile and archived responses/results are preserved. Docker checks execute both approved forms and a negative per language; receipts expose profile, contract identity and selected form separately from actual behavior/declarations. The bounded E2 acceptance criterion is complete for this task, with source-policy and declaration-interface asymmetries explicit. It is not a general rewrite/equivalence checker or a completed model benchmark. E3 is the next unfinished gate.
