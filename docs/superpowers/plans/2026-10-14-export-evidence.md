# Export evidence implementation plan

Goal: optional numeric module 0.3 rejects public functions with no declared case while preserving legacy semantics and migration defaults.
Architecture: normal validator plus version-gated export coverage; existing Wasm tests provide executed build evidence. Maps stay scoped to the new format. Tech stack: Python standard library and Node/Wasm.
Spec: ../specs/2026-10-14-export-evidence.md.

## Constraints and ownership

No frozen input changes, no default migration change, no correctness/proof claims. Backend worker owns pact/module.py, pact/module_build.py, pact/inspection.py and tests/test_export_evidence.py. Root owns CLI, example, documentation, site, roadmap and publication. Reviewer is read-only.

- [x] Backend RED/GREEN: missing/multiple exports, test-ID uniqueness, malformed cases, helpers, legacy no-test modules, correct/incorrect real Wasm tests, forward/default/no-op/downgrade migration, representation/Wasm identity.
- [x] CLI/example: explicit --to module 0.3, default 0.2, invalid migration leaves no artifact; tested counter example and failed-candidate checks.
- [x] Documentation: distinguish declaration/check/build evidence; list test-quality limits and remaining contracts/units scope.
- [ ] Verify full suite, frozen game victory, real three-system and Chromium CI; independent review; PR/merge and live Pages verification.
