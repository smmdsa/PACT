# Roadmap

Goal: lower total agent cost per correct change, with explicit semantics. Alien-looking syntax is not a success criterion.

Last code audit: 2026-10-14, starting at main `882a630`. See the [implementation audit and concrete backlog](docs/roadmap-audit.md) for code/test evidence and unimplemented acceptance criteria. “Done” applies only to the scope written below, not the entire long-term area.

| Stage | Status | Acceptance criterion |
| --- | --- | --- |
| 0.0 Text kernel | Done | Greeting, exact output, capability host |
| 0.1 Stateful kernel | Done | Checked effects, atlas and playable platformer |
| 0.2 Compact frontend | Done | Reversible IR, identical Wasm, malformed input rejection |
| Public project | Live | Public docs, examples, CI and GitHub Pages |
| Representation-token baseline | Done | Versioned tokenizer results, exact input hashes and explicit measurement scope |
| Traditional-language source baseline | Done | Frozen greeting/counter traces, four executed languages, both encodings and explicit asymmetry |
| Parser and benchmark-read bounds | Done | Cursor operand parsing and bounded single-snapshot benchmark reads; general containment/peak-memory claims excluded |
| Model trial material and recorder | Done | Same task prompt, frozen contexts/oracle, external provenance and failed-trial accounting |
| Model-task trials and sandbox verifier | In progress | Trace grader, Docker PACT counter adapter and restricted canonical-IR policy implemented; other languages, broader policy/limit probes, provider integration and real trials pending |
| Runtime microbenchmark | Done | Warmup/fresh samples, independent state oracle, source hashes and local measurements |
| Readable docs and progress | Done | Safe static Markdown, navigation, TOC and committed change log |
| Numeric-module selective inspection | Done | Function discovery, call relationships, effects and test summaries; text graphs and full dependency/coverage proof excluded |
| Transactional edits | Done | Stable node/data/test replacements, revision guards, executable CLI tests and no-clobber new candidates |
| Initial data compression | Done | Bounded RLE and shared symbol dictionaries, exact IR/revision/Wasm equivalence and real token reports |
| Stable-ID literal definitions | Done | Optional source 0.4 integer/string definitions preserve IR/revision/Wasm |
| Inline argument literals and bulk resets | Done | Explicit-ID inline literals (`pact 0.4`), versioned checked `state.reset` (`pact.module/0.2.0`) and reference/Wasm equivalence checks |
| Contracts and units | In progress | Module 0.3 export cases and 0.4 explicit guard/assert conditions; nominal units and stronger contract tooling planned |
| Diagnostics and replay | In progress | Compact/JSON definition spans, semantic/migration diagnostics, reference/Wasm comparison and exact trap maps implemented; full instruction maps, interactive stepping and physical source edits pending |
| Portability | In progress | Linux/Windows/macOS correctness matrix and real Chromium smoke passed; other engines and real devices planned |
| Standard library | Planned | Actual versioned math/color/input modules with explicit effects |
| Distribution | Planned | Owner-selected license and reproducible releases |

## Prioritized unfinished work

| Order | Backlog IDs | Concrete next outcome |
| --- | --- | --- |
| 1 | E1, E2 | Add Python/JavaScript/C isolated adapters, pre-register their source policies and execute embedded-test/policy checks; current PACT policy accepts only a canonical two-field IR edit |
| 2 | E3 | Exercise hostile resource/filesystem/network attempts and cleanup failures on the actual isolation backend; configuration flags and authored fixtures are not sufficient containment evidence |
| 3 | E4, E5 | Configure provider/backend, run fresh paired real trials with actual usage/failures/retries, then broaden tasks and retrieval/repair experiments |
| 4 | L1, L2 | Versioned expected-trap cases, then nominal units and stronger contracts |
| 5 | D1, D2, P1 | Full instruction maps/debugger, byte-aware editing/CAS and more browser/device evidence |
| 6 | S1, R1, X1 | Versioned reusable library, broader runtime/build/memory measurements and owner-approved licensed reproducible releases |

The audit records the evidence and completion criteria for each ID. Task-specific policy results, finite trace matches and CI integration fixtures must not be presented as general candidate correctness or measured model productivity.

Semantics changes require versioned specifications and migrations. Compare to minified JSON and conventional languages.
