# Implementation plan and task ownership

Spec: docs/superpowers/specs/2026-10-14-transactions-comparison.md.

| Task | Owner | Files | Measurable acceptance |
| --- | --- | --- | --- |
| T1 Transactions | transaction agent | pact/transactions.py, pact/revision.py, pact/inspection.py, tests/test_transactions.py, docs/transactions.md | Stale/invalid patches reject; pure original unchanged; stable IDs; valid candidates compile |
| T2 Traditional comparison | benchmark agent | benchmarks/traditional.py, benchmarks/traditional/*, tests/test_traditional.py, benchmarks/results/traditional-*.json, docs/traditional-comparison.md | Same frozen observable outputs, both encodings, source hashes, explicit overhead/limits |
| T3 Resource bounds | hardening agent | pact/compact.py, benchmarks/token_counts.py, tests/test_resource_bounds.py, docs/resource-bounds.md | Bounded read, lexical regressions, parser scaling report |
| T4 Integration | root | pact/__main__.py, pact/transaction_io.py, tests/test_patch_cli.py, README, ROADMAP, AGENTS, workflow, site | Dry-run no files; invalid tests no writes; new-path atomic no-clobber publication; complete CI |
| T5 Review | fresh reviewer | read-only whole branch | Independent important findings resolved with regression evidence |

Root publishes only after full suite, playthrough, actual comparison runs, review and clean diff. Agents do not commit or publish and never modify another task's files. Every completion record states commands and results. Expected revision is document identity, not proof of author or intent. External language benchmarks remain behavioral/source measurements, not equivalent-security or real-model-cost experiments.

## Completion record

T1: 18 new pure transaction regressions plus 10 unchanged inspection tests passed. T2: seven benchmark tests and eight frozen-language executions per encoding verified; PACT has more source tokens in every kernel. T3: cursor/bounded-snapshot regressions and unchanged exact token reports verified; diagnostic parser scaling recorded. T4: CLI/format/output-limit/no-overwrite regressions plus example jump patch and full 140-case suite pass. T5: independent reviewer found JSON/.pact mismatch; regression observed successful bad output before fix and rejection afterward. No important findings remain. In-place filesystem CAS, equivalent-security comparisons and real model productivity trials are deliberately outside this stage, not claimed as delivered.

Publication and deployed Pages content are checked after the guarded GitHub update.
