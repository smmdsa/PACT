# Checked assertions implementation plan

Goal: explicit runtime guard/assert nodes in opt-in module0.4, preserving old semantics and migration defaults.
Spec: ../specs/2026-10-14-checked-assertions.md.

Ownership: backend owns module.py, module_wasm.py, reference.py, compact.py and tests/test_checked_assertions.py. Root owns CLI, dedicated examples, docs/site/roadmap and publication. Review is independent.

- [x] RED/GREEN typed arity, version gates, nonzero/zero, i32/unit guard bodies, no body execution on failure, earlier writes retained on later failure, reference/Wasm state equivalence, unit edge limits and budgets.
- [x] Forward migrations, default compatibility, source aliases/IR/Wasm roundtrip, real successful tests and failed trap builds/no publication.
- [x] Documentation names execution ordering and no rollback; generic Wasm traps remain distinct from reference diagnostics. Units/replay/proof remain planned.
- [ ] Full suite, game victory, independent review and threeOS/Chromium CI; merge and live Pages verification.
