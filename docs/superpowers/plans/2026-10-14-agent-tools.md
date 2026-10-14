# Agent tooling implementation plan

Goal: reduce needed context and measure actual representation token counts.
Spec: docs/superpowers/specs/2026-10-14-agent-tools.md.

1. Parallel task A owns benchmarks/token_counts.py, requirements, tests/test_token_counts.py and benchmarks/README.md. Tests first; record optional-tokenizer failures honestly.
2. Parallel task B owns pact/inspection.py, tests/test_inspection.py and docs/inspection.md. Tests first for closure, effects, no cell bulk data, deterministic revision, unknown functions and invalid sources.
3. Root integrates inspect/symbols CLI, CLI regressions, site/docs/roadmap/contributor guidance. Tests first; run full suite, examples and input-only playthrough.
4. Fresh independent review; fix important issues with regressions. Publish using expected remote head and check GitHub Actions plus Pages content.

Constraints: Python3.10+, Node20+, compiler remains dependency-free. No execution or source-version changes. No task-productivity claims absent model experiments. Review focus: transitive context, readonly data, stale revision, malformed source, nondeterministic output and token resource availability.

## Execution record

Tasks A/B delivered by separate agents; root integrated CLI/site/contribution guidance. 103 tests pass. Actual token counts and four task-verifier selfchecks executed without real model task trials. Fresh reviewer found no important code defects. Roadmap wording was narrowed to actual call/effect/test-summary capabilities. Deferred minor: benchmark reads compact file before its size check, so a bounded read would improve allocation behavior; normal compiler loader remains bounded. Existing compact-parser long-list cost also remains deferred.

Publication is verified separately in GitHub Actions and Pages after upload.
