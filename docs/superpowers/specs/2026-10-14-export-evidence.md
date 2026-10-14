# Export evidence policy: numeric module 0.3

Intent: give agents a checked signal that every public function has at least one declared executable case, without silently tightening legacy sources or claiming correctness from test presence.

Add opt-in `pact.module/0.3.0` with the same closed module fields, operations and Wasm semantics as 0.2. After normal test validation, require every exported function to be the target of at least one declared test. Missing exports reject with `EXPORT_EVIDENCE_MISSING`, a sorted function list in a structured `add_export_tests` hint. Helpers do not need direct tests; existing export-only test rules remain unchanged.

`FORMAT` keeps the historical 0.2 migration default for API compatibility; add `TESTED_FORMAT` for 0.3 and extend `FORMATS`. `migrate_module(document, target_format=FORMAT)` accepts strictly forward 0.1→0.2, 0.1→0.3 or 0.2→0.3 conversions. It validates before and after copying; missing evidence rejects migration and never writes output. Default 0.1→0.2 behavior and rejection of no-op/downgrade migrations remain. CLI `migrate --to` chooses 0.2/0.3; default stays 0.2.

Ordinary reads/conversions preserve the declared format and revision. Versions 0.1/0.2 validation remains unchanged. A successful migration changes only format/revision and preserves Wasm bytes. A separate tested counter example demonstrates 0.3; frozen games, patches and benchmark fixtures remain untouched.

Check/inspection verifies declared cases and export coverage, not test execution. Build executes all declared tests through the existing real Wasm runner and rejects incorrect expectations before publication. Only 0.3 plans, inspection responses and build manifests add an `declared_export_tests` map from exported function to sorted test IDs; legacy responses retain their previous shape. Actual build evidence remains the existing tested receipt.

Security limits: case presence does not imply relevance, boundary coverage, adequate assertions, naming truth, single responsibility or universal correctness. A weak/unrelated assertion can satisfy the structural policy. Nominal units, pre/postconditions, mutation testing and proof remain separate planned work. No new imports, dependencies or guest instructions.
