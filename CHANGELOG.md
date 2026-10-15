# Progress

Every entry distinguishes implemented behavior from measured evidence and planned work. The [roadmap](ROADMAP.md) describes remaining scope.

## Latest — Órbita, an authored PACT interface experiment

- Added an editorial spatial interface: six speculative futures, three visual lenses, an attention budget and reversible decisions, plus a list alternative.
- The authored PACT 0.4 source compiles to real WebAssembly: selection, lens, allocation bounds, six-seed budget, rolling 32-state history, undo/redo, branch truncation and reset live in the kernel. HTML/CSS/SVG/JavaScript handle presentation and events.
- Six export cases execute on Wasm at build time. Behavioral tests cover bounds, rejection before writes, history and reference/Wasm agreement over a deterministic mixed action sequence. Chromium checks exercise the interface on desktop and mobile-shaped viewports.
- Added Órbita to the shared demo library with source and runtime-boundary documentation. It is an authored application, separate from generated model benchmark candidates; no historical-uniqueness, productivity or prediction claim is made.

## Demos & Examples catalog

- Added a shared-navigation and homepage entry collecting the three playable games and every published PACT source, replay and patch fixture.
- Added search, type filters, source downloads, evidence links and a sandboxed inline player, with direct links retained when JavaScript is unavailable.
- Catalog browser checks cover search, empty results, filters, responsive layout and opening/closing the authored Alien Harvest game on desktop and mobile. GPT originals remain unchanged and use their separate isolated verifier.

## Metroidvania generation pilot and playable examples

- Gave GPT-6.1 and GPT-6 Astra the same fresh-session HTML/JavaScript game contract: five rooms, gated double jump, key, pit, enemies, checkpoint, boss and victory.
- Preserved both original single-file games without coordinator repairs and added a public comparison shell, original downloads and a project-homepage link.
- Added a separate restricted Docker Chromium worker with bounded observations, actual keyboard checks, deterministic action-only progression routes and screenshots. A third session implemented the initial verifier blind to candidate sources.
- Both original games passed 16/16 finite browser checks, including victory; frozen observations bind the CI run, runtime image, verifier and candidate hashes.
- Four infrastructure runs are retained: a trusted Canvas control exposed the original 1 MiB temporary-file limit; the browser profile now allows bounded 32 MiB graphics files while candidate input stays at 1 MiB. A later Chromium thread-creation timeout is retained separately; its task limit is now 256.
- Runtime checks and failures are retained separately from generated artifacts. Provider usage/version/latency remain unavailable, one attempt is not a ranking, and this same-language test is not PACT-versus-JavaScript evidence.

## Exploratory GPT subagent counter pilot

- Archived real final responses from sessions requested as GPT-6.1 and GPT-6 Astra, with fresh context for every language and the same frozen task instruction.
- Eight valid responses cover PACT/Python/JavaScript/C once per model. Both models returned identical edits per language and all eight pass their static task policies.
- One coordinator-copy error in Astra's JavaScript input is retained and excluded explicitly; its replacement used a new session. No response body was repaired.
- Inputs, coordinator-visible responses, extraction rule, candidates and hashes are archived; Docker CI re-evaluates each candidate and retains per-trial behavior/policy receipts.
- This is exploratory evidence, with no provider usage, immutable model versions, generation latency or statistical ranking. It does not complete the formal model benchmark or establish a PACT advantage.

## Isolated C counter adapter

- `--language c` compiles C11 and executes native code only inside Docker, using the same frozen calls and independent trace grader as PACT/Python/JavaScript.
- A bounded Linux memfd loads the compiled binary while `/tmp` remains noexec; reset forks and re-executes the binary so C static state starts fresh.
- Compiler diagnostics use the existing bounded capture. Receipt 0.5 includes unauthenticated GCC metadata; compile failures, crashes and source-policy failures remain explicit.
- The C policy allows only the exact frozen loop-bound edit, with CRLF normalization. Source-policy asymmetries remain documented.
- CI exercises authored baseline/edited/invalid/comment/1-MiB/reset/noise/output/timeout/crash fixtures. They are not real model trials.
- All four task adapters exist. Broader source policies, embedded declaration execution, hostile containment probes and actual provider/model trials remain unfinished.

## Isolated JavaScript counter adapter

- `--language javascript` runs the frozen counter task as a Node 24 ES module only inside Docker, with the existing calls, independent oracle, output cap and timeout.
- A distinct module URL re-evaluates top-level state for reset; CI includes a global-state leakage fixture.
- A separate static policy permits only the exact loop-bound edit, with CRLF normalization. Unlike PACT IR/Python AST policies, it also rejects extra comments and formatting changes.
- Receipt 0.4 adds unauthenticated Node/V8 metadata separately from the common trace. Immutable image identity, logs and separate behavior/policy outcomes remain explicit.
- Docker fixtures cover baseline/edited/invalid/noisy source, unapproved comments, an exact 1 MiB candidate, reset leakage, output flood and timeout. These are authored tests, not model trials.
- C, broader containment probes, embedded declaration execution, broader policies and actual model runs remain pending.

## Isolated Python counter adapter and bounded output

- `--language python` runs candidate code only in the Docker worker; PACT remains the default. Both use the same frozen calls, reset and trace grader.
- Added a frozen-baseline Python AST policy allowing only the canonical range(3)→range(4) edit, separate from trace grading.
- Streaming capture limits combined stdout/stderr before unbounded allocation; excess output and timeout kill the Docker CLI and force container cleanup.
- Receipt 0.3 retains termination reasons, bounded raw logs and separate policy/behavior outcomes. Malformed/noisy worker output becomes a failed observation.
- Docker CI covers baseline, edited, malformed/noisy source, output flood and timeout fixtures. These are authored integration tests, not model measurements.
- JavaScript/C adapters, wider containment probes, broader policies and actual model runs remain pending.

## Code-backed roadmap audit and restricted source policy

- Audited every roadmap area against implementation/tests, narrowed overbroad completed labels and added a prioritized backlog with concrete missing acceptance criteria.
- Corrected stale guard/replay/security guidance. No real model measurements, general source-policy proof or complete instruction debugger is claimed.
- Counter-four sandbox receipts now include a static canonical-IR policy: only the repeat count and independent embedded expectation may change.
- Sandbox receipt 0.2 makes CLI success require both behavioral and policy matches; historical 0.1 receipts are not retroactively approved.
- Behavioral match and policy match remain separate; a matching trace with an unapproved semantic edit is rejected by the policy. Full candidate approval remains unset.
- Other language adapters, broader policies, hostile containment probes, provider runs, expected-trap cases, units, standard library and releases remain pending.

## Initial isolated PACT counter adapter

- A Linux/Docker adapter produces finite counter-four observations from a fixed reference worker, using an immutable local image ID.
- Candidate execution requests no network/host mounts, a read-only filesystem, dropped privileges and explicit resource/time limits; effective configuration is inspected before execution.
- Missing backend or weakened configuration rejects with no host fallback. Containers are forcibly removed; receipts retain image, candidate and log identity.
- Dedicated CI exercises authored baseline, edited and malformed fixtures in actual containers and archives receipts. These are not model results.
- Broader language adapters, source-policy checks, adversarial containment probes and real model trials remain pending.

## Independent external trace grading

- External counter-four observations can be graded for PACT, Python, JavaScript and C against exact candidate bytes and a pinned, independently derived oracle.
- Initial/reset state, ordered cases, bounds-state preservation and incomplete/error outcomes are checked; identity and malformed-input rejections retain provenance.
- No candidate code or model is executed. Behavioral match is separate from full candidate approval, with unauthenticated execution and outstanding checks explicit.
- Sandbox adapters, policy verification and real model measurements remain pending.

## Exact Wasm trap locations

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
