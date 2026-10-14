# Task plan

| Task | Owner | Files | Acceptance |
| --- | --- | --- | --- |
| D1 Cells codec | agent | pact/data_codec.py, tests/test_data_codec.py | Exact mixed/RLE roundtrip; aggregate-budget rejection before allocation; malformed/bool/duplicate targets reject |
| D2 Atlas codec | agent | pact/atlas_codec.py, tests/test_atlas_codec.py | Exact mixed symbol-table roundtrip; missing/bad references reject; shared vs different maps preserved |
| D3 Frontend and evidence | root | compact.py, CLI, tests/test_compressed.py, benchmarks/data_compression.py, examples/game.data.pact, docs/CI/site | Both versions, same IR/revision/Wasm, old source stable, actual token reports, victory |
| D4 Fresh review | agent read-only | whole diff | Important findings fixed with regression evidence |

No agent commits/publishes or edits another owner's files. Tests precede implementation. Compiler stays dependency-free. Codec cost selection uses exact full canonical UTF8 JSON, not guessed tokens. Root publishes after full suite, reviewer, actual reports, playthrough and verified GitHubPages.

## Execution record

D1: eight tests passed, full preflight before expansion, strict128/4096/16384 bounds. D2: six tests passed, shared64-symbol cap and oversized-inline compatibility. D3: three frontend/CLI tests plus whole157-case suite pass; both real encoding reports verify equalIR/revision/Wasm. Game data source43,543bytes; o200k18,328tokens, cl100k18,298. Input-only victory unchanged at tick1,216. D4: fresh reviewer independently passed157 tests and found no blockers.

Deferred minor: greedy symbol-map selection misses a jointly profitable two-group case (733byte ordinary section vs724 fully shared); result remains correct, ordinary sections retained. No global optimum claimed. Inline literals and runtime bulk resets remain pending, not silently marked done.

Root publishes with expected GitHub head, checks CI and updated Pages content.
