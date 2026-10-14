# Agent tools verification — 2026-10-14

- 103 unittest cases pass; inspect/symbols accept compact and JSON and reject unknown functions or unsupported text profiles.
- Inspection tests cover transitive reads/writes/constants/callers, omitted bulk data, detached records, full-source validation and deterministic revisions/output.
- Optional tiktoken0.12.0 real runs reproduce checked-in reports for o200k_base and cl100k_base. Game compact tokens: 24,851 / 24,840; minified JSON: 35,903 / 35,876.
- Exact player.move CLI context: 17,340 bytes; 6,229 / 6,076 tokens. It omits helper bodies, data and test-case bodies; this is not equivalent full-source context or a complete task budget.
- Two independent task verifiers selfchecked on compact/JSON candidates (four checks). No real model-success trials, repair cycles or provider costs measured.
- Site/greeting compile and input-only platformer playthrough still win at tick1,216.
- Fresh independent code reviewer found no important defects. Scope wording now describes actual call/effect/test summaries.

Deferred resource improvements: benchmark compact-input allocation can use a bounded snapshot read; compact parser can avoid repeated slicing on pathological long operand lists. Source validation still enforces the 1MiB limit. No new execution semantics, runtime dependencies or source-profile version introduced. Tokenizer dependency is confined to optional benchmark tooling.

Update: the parser slicing and bounded benchmark-read resource findings were resolved in the transactions/comparison stage; see docs/resource-bounds.md. Earlier verification entries describe their historical state.
