# Progress

Every entry distinguishes implemented behavior from measured evidence and planned work. The [roadmap](ROADMAP.md) describes remaining scope.

## Latest — exact Wasm trap locations

- Compiler-generated trap maps bind qualified node IDs and absolute opcode offsets to the exact binary hash and semantic revision.
- Node replay attaches IDs only when the actual innermost Wasm frame exactly matches a trap site; generic WASM_TRAP codes are preserved.
- Assertions/guards, bounds and signed division/remainder sites are covered. Repeated node uses remain distinct positions.
- Map collection is bounded; incomplete maps and missing engine positions do not fabricate attribution.
- All 11 numeric example binaries remain byte-identical to the prior compiler. Full instruction mapping and interactive debugging remain pending.

## Wasm replay and comparison

- `pact replay --engine wasm` executes compiler-produced modules in a fresh Node instance; `--engine compare` compares results, trap occurrence and state hashes for each recorded call.
- Wasm reports include artifact/runtime hashes and Node/V8 versions. Traps stay generic; reference node identities are not asserted for Wasm.
- Node execution has a 15-second timeout; reference-budget exhaustion produces an incomplete comparison without starting Wasm.
- Compiled bytecode/report sizes are bounded. Declared build cases are not run by replay.
- Wasm instruction mapping, interactive debugging and real model trials remain pending.

## Bounded reference replay

- Revision-checked exported-call recordings execute deterministically on the numeric reference interpreter.
- Reports include results, per-call state hashes, final state and qualified runtime diagnostic spans; traps stop execution without rollback.
- All recording inputs validate before execution; reads, call counts and evaluated nodes are bounded.
- Reference store bounds checks now precede value evaluation, matching Wasm trap ordering.
- Actual Wasm comparisons cover success and trap-state retention. Wasm replay, debugger and model trials remain pending.

## Explicit migration diagnostic locations

- JSON migration semantic errors now use definition spans from the original single bounded read, including escaped IDs and CRLF.
- Existing format/migration rejection codes, default target, structured fixes and ambiguous candidates are preserved.
- Failed migrations leave existing output files intact; successful compact/JSON migrations retain identical Wasm.
- Replay and patch-candidate locations remain planned.

## JSON semantic diagnostics

- JSON semantic rejections now carry original definition spans in locate and CLI source validation, excluding migration.
- Escaped IDs, CRLF, ambiguous candidates and structured fixes are preserved; malformed containers and contract collisions do not fabricate locations.
- Parse-only loader callers and patch documents retain their existing behavior. Runtime replay and JSON migration attachment remain planned.

## JSON source locations

- `pact locate` now queries validated JSON graphs and numeric modules as well as compact sources.
- Qualified definition spans preserve original quotes/escapes, Unicode columns, CRLF byte identity and physical ordering.
- Duplicate decoded keys and invalid programs reject; references and unrelated ID namespaces are excluded.
- No IR, revision or Wasm changes. Automatic JSON diagnostic attachment and runtime replay remain planned.

## Checked flow conditions

- Optional numeric module 0.4 adds typed assert and lazy guard nodes, inheriting declared public cases.
- False guards skip their body; postcondition failures retain earlier writes. No rollback or static proof claimed.
- Reference diagnostics and generic Wasm traps have explicitly different granularity.
- Existing sources, defaults, frozen hashes and game execution remain unchanged.

## Optional export evidence

- Numeric module 0.3 requires a declared executable case per exported function.
- Check/inspection shows declarations; build runs real Wasm tests and rejects wrong expectations.
- Explicit forward migration; legacy formats, default migration and frozen sources remain unchanged.
- Test relevance, boundary coverage, single responsibility, pre/postconditions and units remain separate work.

## Browser smoke validation

- Pinned Chromium workflow added for desktop and mobile-shaped viewport checks.
- Real DOM input, canvas, pause and documentation layout assertions; screenshots/result artifacts.
- [Chromium CI run](https://github.com/smmdsa/PACT/actions/runs/38524413016) passed 11 checks; browser 149.0.7827.55, generated HTML hash and artifacts recorded.
- Full browser victory, additional engines and real-device/audio checks remain planned.

## Operating-system validation

- Dedicated compiler/host/docs/game matrix introduced for Linux, Windows and macOS.
- Corrected matrix passed 208 tests and the game flow on each system; [run evidence](https://github.com/smmdsa/PACT/actions/runs/38523715398).
- Windows fixes preserve strict manifest checks and explicit raw stdout provenance; real browser validation remains planned.
- LF source checkout and explicit UTF-8 mode preserve text interpretation and frozen hashes.

## Physical source locations

- `pact locate` queries qualified node/function definitions, including inline constants.
- Source maps are separate from IR; source-byte hashes and semantic revisions have distinct meanings.
- Compact errors now include physical parse lines or unique semantic definitions; ambiguous IDs list candidates.
- JSON maps, Wasm trap replay and full debugger remain planned.

## Gemini integration, measured inline source and readable documentation

- Source0.4 keeps stable literal IDs while reducing syntax; old0.2/0.3 sources remain supported.
- Gemini PR #1 merged after compatibility fixes, 171 tests and successful CI. Legacy reads/conversions preserve source revisions and frozen hashes; migration is explicit.
- The complete game inline source uses 14,112 o200k_base tokens versus 24,851 in source 0.2; IR, revisions and Wasm are unchanged.
- Checked state.reset uses numeric module 0.2; a separate reset example demonstrates the new operation.
- Both standalone literal definitions and explicit-ID inline arguments work under source 0.4.
- Markdown docs render as headings, tables, lists and fenced code, with navigation and local links.
- Runtime performance is measured separately from source tokens; the [report](docs/runtime-performance.md) includes hardware/methodology.
- [External LLM trial material](docs/agent-evaluation.md) uses identical instructions with language-specific frozen contexts. Actual model trials remain pending.

## Data compression0.3

RLE initial arrays and shared sprite symbols reduced game source from24,851 to18,328 tokens. 157 tests passed, unchanged input-only victory, independent review and Pages deployment. [Evidence and limits](docs/data-compression.md).

## Transactions and traditional-language comparison

Revision-checked candidate patches, actual Wasm tests and atomic no-clobber new-file publication. 140 tests passed. Four languages matched frozen traces; PACT used more source tokens in both kernels. [Comparison](docs/traditional-comparison.md) · [Transactions](docs/transactions.md).

## Agent tools

Selective function context, call/effect/test summaries and pinned-tokenizer reports. 103 tests passed. No model-task productivity result was claimed.

## First executable platformer

Generic numeric kernel, internal pixel atlas and Alien Harvest. Input-only playthrough wins at tick1,216. Real-browser/mobile/audio and cross-OS coverage remain open.
