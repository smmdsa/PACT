# Roadmap

Goal: lower total agent cost per correct change, with explicit semantics. Alien-looking syntax is not a success criterion.

| Stage | Status | Acceptance criterion |
| --- | --- | --- |
| 0.0 Text kernel | Done | Greeting, exact output, capability host |
| 0.1 Stateful kernel | Done | Checked effects, atlas and playable platformer |
| 0.2 Compact frontend | Done | Reversible IR, identical Wasm, malformed input rejection |
| Public project | Prepared | Docs/examples/CI/Pages; owner enables Pages |
| Token/task baseline | Next | Versioned tokenizer/model results, correct edits, retries, tool overhead |
| Selective inspection | Planned | Symbol/dependency/contract/impact queries without whole-file reads |
| Transactional edits | Planned | Stable node patches, revision guards, atomic validation |
| Data compression | Planned | Inline literals, bulk resets, palette sharing and RLE with equivalence tests |
| Contracts and units | Planned | Preconditions, postconditions, nominal units, public-function evidence policy |
| Diagnostics and replay | Planned | Source locations, structured fixes and debugger |
| Portability | Planned | Windows/macOS/Linux CI and real browser tests |
| Standard library | Planned | Actual versioned math/color/input modules with explicit effects |
| Distribution | Planned | Owner-selected license and reproducible releases |

Semantics changes require versioned specifications and migrations. Compare to minified JSON and conventional languages with equivalent tooling. Do not move hidden assumptions into the host to shorten source.
