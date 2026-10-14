# Transactions/comparison verification — 2026-10-14

- 140 unittest cases passed on Linux, Python3.12 and Node24.
- Pure transactions: bounded closed schemas, expected revisions, target/ID preservation, duplicate rejection, detached candidates and full validation before return.
- CLI: actual Wasm tests before success, dry-run no output, source preservation, atomic new-file publication and existing-path rejection. Serialized output limit checked for dry-run too.
- Independent reviewer caught incompatible JSON/.pact output; a real CLI regression failed before the fix, then JSON candidates roundtripped and mismatched suffixes rejected.
- Grounded-jump patch changes player.jump to -1792 and its test together; dry-run provides tested evidence and new revision.
- Eight language/task executions per encoding match independent frozen expected traces, including wrapping and bad-index cases. PACT source costs more in every reported kernel; driver costs/policies recorded separately.
- o200k source tokens: greeting PACT78/Python10/JS11/C27; counter163/74/76/138. cl100k: greeting80/11/12/28; counter163/73/76/138. No equivalent-security or model-task-productivity conclusion.
- Parser cursor and bounded snapshots preserve frozen source token counts/hashes and compiled Wasm; measured scaling in docs/resource-bounds.md.
- Full platformer playthrough still reaches victory through inputs at tick1,216.

Atomic no-clobber publication requires output filesystem hard links. It is not in-place cross-process CAS. Measurements are from two small kernels, not the full game. Actual model trials, nominal units, bulk source compression and browser/OS coverage remain roadmap work.
