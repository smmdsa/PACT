# Roadmap

Goal: lower total agent cost per correct change, with explicit semantics. Alien-looking syntax is not a success criterion.

| Stage | Status | Acceptance criterion |
| --- | --- | --- |
| 0.0 Text kernel | Done | Greeting, exact output, capability host |
| 0.1 Stateful kernel | Done | Checked effects, atlas and playable platformer |
| 0.2 Compact frontend | Done | Reversible IR, identical Wasm, malformed input rejection |
| Public project | Live | Public docs, examples, CI and GitHub Pages |
| Representation-token baseline | Done | Versioned tokenizer results, exact input hashes and explicit measurement scope |
| Traditional-language source baseline | Done | Frozen greeting/counter traces, four executed languages, both encodings and explicit asymmetry |
| Resource bounds | Done | Cursor operand parsing and bounded single-snapshot benchmark reads |
| Model trial material and recorder | Done | Same task prompt, frozen contexts/oracle, external provenance and failed-trial accounting |
| Model-task trials and sandbox verifier | Planned | Real trials, independent execution, correct edits, retries, failures and tool overhead |
| Runtime microbenchmark | Done | Warmup/fresh samples, independent state oracle, source hashes and local measurements |
| Readable docs and progress | Done | Safe static Markdown, navigation, TOC and committed change log |
| Selective inspection | Done | Function discovery, call relationships, effects and test summaries without whole-file agent reads |
| Transactional edits | Done | Stable node/data/test replacements, revision guards, executable CLI tests and no-clobber new candidates |
| Initial data compression | Done | Bounded RLE and shared symbol dictionaries, exact IR/revision/Wasm equivalence and real token reports |
| Stable-ID literal definitions | Done | Optional source 0.4 integer/string definitions preserve IR/revision/Wasm |
| Inline argument literals and bulk resets | Done | Explicit-ID inline literals (`pact 0.4`), versioned checked `state.reset` (`pact.module/0.2.0`) and reference/Wasm equivalence checks |
| Contracts and units | In progress | Module 0.3 export cases and 0.4 explicit guard/assert conditions; nominal units and stronger contract tooling planned |
| Diagnostics and replay | In progress | Structured diagnostic fixes and qualified compact/JSON source positions; JSON diagnostic attachment and runtime replay/debugger planned |
| Portability | In progress | Linux/Windows/macOS correctness matrix and real Chromium smoke passed; other engines and real devices planned |
| Standard library | Planned | Actual versioned math/color/input modules with explicit effects |
| Distribution | Planned | Owner-selected license and reproducible releases |

Semantics changes require versioned specifications and migrations. Compare to minified JSON and conventional languages.
