# Expected-trap cases implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task.

**Goal:** Complete L1 with exact expected-trap declarations and reference/Wasm acceptance.
**Architecture:** Extend the closed numeric schema, then reuse Machine and compiler trap maps in the build path. Preserve legacy build behavior.
**Tech stack:** Python standard library and actual Node WebAssembly.
**Spec:** docs/superpowers/specs/2026-10-15-expected-traps.md

## Global constraints

- Numeric format pact.module/0.5.0 is opt-in; default migration remains 0.2.
- No runtime opcode, frozen benchmark candidate or legacy receipt changes.
- Reference budget is 1,000,000 evaluated nodes per suite; Node deadline remains 15 seconds.
- Exact function/node/kind attribution is mandatory for expected Wasm traps.

## Review focus

Malformed nested trap metadata must produce PactError, never raw Python exceptions. Helper failure attribution must use the innermost frame. Prefix state assertions must retain their meaning. Missing stack coordinates and map truncation must fail closed. Reference budget exhaustion must never count as an expected trap.

## Task 1: Versioned schema and compatibility

Files: pact/module.py, pact/__main__.py, tests/test_expected_traps.py, existing version assertions.
Interface: TRAP_TESTED_FORMAT = pact.module/0.5.0; analyze_module accepts optional strict trap record only in that format.

- [x] Write schema/migration/roundtrip tests, run and observe rejection of unsupported 0.5.
- [x] Add the format, inherited operations, strict code/site validation and CLI migration choice.
- [x] Run focused schema tests; preserve byte-identical migration and default behavior.
- [x] Commit schema/spec/plan.

## Task 2: Execute both engines and verify exact failure

Files: pact/module_build.py, new pact/module_tests.py, tools/check_module.mjs, tests/test_expected_traps.py.
Interface: check_reference_tests(document) checks fresh-state cases with a shared reference budget; build_module passes the hash-bound trap map only for 0.5; Node returns ordinary tested evidence plus reference/wasm labels and trap/coordinates for negative cases.

- [x] Write executable tests for exact assertion/bounds/arithmetic/helper attribution, normal-return/wrong-site/state rejection and positive cases; observe failures.
- [x] Implement bounded reference validation; extend Node's existing test runner with exact trap-map verification.
- [x] Add missing-coordinate/hash-mismatch and reference-budget rejection tests, observing failure before each guard is added.
- [x] Run full unittest suite; inspect actual Node evidence and CLI atomic failure behavior.
- [x] Commit engine changes.

## Task 3: Public examples, evidence and integration

Files: examples/counter.traps.pact, docs/expected-traps.md, tools/build_site.py, AGENTS.md, README.md, docs/syntax.md, docs/security.md, ROADMAP.md, docs/roadmap-audit.md, CHANGELOG.md.

- [ ] Publish an authored mixed positive/negative example and versioned specification, update roadmap with bounded completion criteria.
- [ ] Build site and run full suite, request independent review and resolve actionable findings.
- [ ] Publish PR, inspect OS/browser/Docker CI, merge and verify Pages before the next backlog item.
