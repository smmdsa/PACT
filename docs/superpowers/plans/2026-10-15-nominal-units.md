# Nominal units implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, task by task.

**Goal:** Complete L2 static nominal-unit/signature contracts.
**Architecture:** Run a separate bounded unit inference pass after existing scalar validation. Reuse runtime compiler and module 0.5 test machinery unchanged.
**Tech stack:** Python standard library and actual Node WebAssembly.
**Spec:** docs/superpowers/specs/2026-10-15-nominal-units.md

## Global constraints

- Opt-in pact.module/0.6.0; optional units section; legacy schemas/output/default migration unchanged.
- Reserved scalar/effect types remain i32/unit; at most 128 nominal names.
- No runtime opcodes, casts, boxed units or derived-unit algebra.
- All module 0.5 test execution/expected-trap rules are inherited.

## Review focus

Malformed metadata must reject without Python exceptions. Locals/repeat counters must not erase units. Calls/results and lazy branches must retain units. Compact conversions and patches must preserve annotations. Hosts use untagged i32 ABI and cannot authenticate units.

## Task 1: Schema and static inference

Files: pact/module.py, new pact/units.py, pact/__main__.py, tests/test_nominal_units.py, existing version assertions.
Interface: UNIT_FORMAT = pact.module/0.6.0; check_units(document) returns pact.unit-contracts/0.1.0 or rejects.

- [x] Write failing schema/operator tests and observe unsupported-version failure.
- [x] Implement strict metadata validation and memoized unit inference after existing graph/type/effect validation.
- [x] Inherit module 0.5 trap declarations/build path and add CLI migration choice.
- [x] Verify operator/signature/malformed metadata tests and legacy suite; commit.

## Task 2: Exposed contracts and executable compatibility

Files: pact/module_build.py, pact/inspection.py, tests/test_nominal_units.py.
Interface: plans/manifests expose unit_contracts; inspection filters contracts to retrieved context; symbols omits literal maps.

- [x] Write failing manifest/inspection/representation/migration/CLI tests.
- [x] Add output metadata while preserving legacy shapes and compiler bytes.
- [x] Execute authored reference/Wasm positive/negative cases and patch failure atomicity; run full suite; commit.

## Task 3: Public example and integration

Files: examples/counter.units.pact, docs/nominal-units.md, public navigation, AGENTS/README/syntax/security/roadmap/audit/progress and this plan.

- [ ] Publish versioned specification and authored units example; add example execution test.
- [ ] Build public site and run full suite, independent review and CI; fix actionable findings with regression tests.
- [ ] Merge only green reviewed result; verify public Pages and continue next pending item.
