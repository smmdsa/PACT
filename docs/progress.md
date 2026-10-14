## Exact Wasm trap sites — 2026-10-14

Mapped compiler-emitted traps to qualified nodes using actual Node function-index/byte-offset frames and exact binary identity. Tests cover helpers, repeated definitions, bounds, arithmetic and unmapped fallback. Eleven numeric example binaries match the prior compiler exactly. Full instruction maps, interactive debugger and real model trials remain pending.

## Wasm replay and comparison — 2026-10-14

Added fresh-instance Wasm call replay and per-call reference comparison. Reports preserve generic Wasm traps, artifact/runtime hashes and Node/V8 versions. Tests cover success/trap state equivalence, changed intermediate hashes, incomplete reference traces and missing/timeout runtime errors. Wasm instruction mapping, interactive debugging and real model trials remain pending.

## Bounded reference replay — 2026-10-14

Implemented revision-checked call recordings, deterministic reports, state hashes, qualified runtime spans and a shared evaluation budget. Tests compare selected success/trap states with actual Wasm. Fixed reference store trap ordering. This executes the reference interpreter; compiled-Wasm replay, debugger and real model trials remain pending.

## Explicit migration locations — 2026-10-14

JSON migration now retains original physical definition positions on semantic rejection. Source and target validation use the existing migrator; no format defaults or codes change. Single-snapshot reads, ambiguity, escaped IDs/CRLF, preserved output on rejection and Wasm-equivalent successful migrations are covered by tests. Replay and patch-candidate spans remain pending.

## JSON semantic diagnostic attachment — 2026-10-14

Implemented source validation in locate and CLI check/build/interpret/inspection/conversion/patch input. Positions derive from the original bounded snapshot. Repeated IDs remain candidates; contract collisions and malformed containers omit spans. Migration attachment, patch-candidate locations and replay remain pending.

# Execution ledger — plan: docs/superpowers/plans/2026-10-13-bootstrap.md

Ruling: User's explicit instruction to create the basic structure and hello world authorizes implementation now. Execute locally without another approval handoff.

Ruling: There was no existing repository; use a new isolated project directory with a local bootstrap branch. No external repository or publishing is involved.

Ruling: Compiler implementation uses Python because Python and Node are installed; Rust is unavailable. This does not determine the semantics of PACT or require Python inside Wasm.

Ruling: First kernel is a bounded static text/effect graph. Numeric types, arbitrary functions, sprite atlas, game host, mutation API and general proof checking remain unimplemented. Cost: hello proves the execution path, not the broader agentic-productivity hypothesis.

Task interface scan: analyzer plan -> compiler and host; both consume ordered UTF-8 emissions and the same versioned manifest format.

Task 1: complete — 22 tests observed failing with placeholder behavior, then passing with the analyzer.

Task 2: complete — 13 execution tests observed failing, then full 35-test suite passed using real Node WebAssembly.

Ruling: The host independently reconstructs the narrowly permitted static-output bytecode. This avoids trusting a hash as a security claim and excludes loops before execution. Cost: Python and JavaScript implement the same small binary profile, so parity tests are required.

Ruling: Artifact hashes are integrity/content identifiers, not signatures or evidence that an external author's intent was correct. Documented in README.

Final independent review: no critical, important or minor findings in the production implementation. Reviewer ran the original 35-test suite.

Additional profile tests: valid infinite-loop Wasm is rejected before execution; sequence offsets greater than 127 bytes preserve Unicode and embedded NUL; newline-terminated manifest identifiers/hashes are rejected. No production change was needed for these additional checks.

Ruling: Package one source archive containing specs, plan, tests, runtime and compiled hello. Keep the local bootstrap branch; no merge, push or deployment was requested.

Task 3: complete — full suite, CLI build, Wasm output and deny-by-default verified; source archive prepared for delivery.
