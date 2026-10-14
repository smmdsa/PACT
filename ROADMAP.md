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
| Model-task baseline | Planned | Real trials, correct edits, retries, failures and tool overhead |
| Selective inspection | Done | Function discovery, call relationships, effects and test summaries without whole-file agent reads |
| Transactional edits | Done | Stable node/data/test replacements, revision guards, executable CLI tests and no-clobber new candidates |
| Initial data compression | Done | Bounded RLE and shared symbol dictionaries, exact IR/revision/Wasm equivalence, real token reports |
| Inline literals and bulk resets | Next | Preserve explicit IDs/effects or version semantics; independent equivalence tests |
| Contracts and units | Planned | Preconditions, postconditions, nominal units, public-function evidence policy |
| Diagnostics and replay | Planned | Source locations, structured fixes and debugger |
| Portability | Planned | Windows/macOS/Linux CI and real browser tests |
| Standard library | Planned | Actual versioned math/color/input modules with explicit effects |
| Distribution | Planned | Owner-selected license and reproducible releases |

Semantics changes require versioned specifications and migrations. Compare to minified JSON and conventional languages with equivalent tooling. Do not move hidden assumptions into the host to shorten source.
