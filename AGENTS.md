# Agent guidance

Read README.md, docs/syntax.md and docs/security.md before changing semantics. ROADMAP.md describes planned work. Compact 0.2, compressed data 0.3 and literal/inline source 0.4 wrap graph 0.0.1 or numeric modules 0.1.0/0.2.0/0.3.0/0.4.0; preserve these distinctions. Reading/converting preserves revisions. Only explicit migration changes numeric format; state.reset requires module 0.2.0, 0.3.0 or 0.4.0.

Prefer focused function/dependency reads. Keep IDs stable. Do not replace semantic names with undocumented opcodes. Effects, array indices, overflow and grants remain explicit.

Use `python3 -m pact symbols SOURCE` for discovery and `python3 -m pact inspect SOURCE --function ID` for selected context. Inspect helper bodies separately when needed. Responses are not buildable modules; omitted state/test bodies require further reads. Revisions identify semantic source contents, not signatures or author authority. Use `pact patch` with an expected revision for a new candidate; inspect the receipt and executable test evidence. In-place filesystem compare-and-swap is not supported.

Parallel contributors must own nonoverlapping files and report executed checks. Read docs/agent-contributions.md before preparing a contribution.

Compact and JSON examples must reconstruct identical IR. After authoring changes regenerate JSON then explicitly convert to compact; inspect the diff before overwriting hand edits.

Run the full unittest suite for compiler changes and input-only playthrough for gameplay. Representation-only changes must preserve compiled bytes. Never report bytes as tokens or prepared deployment as live. Do not select a license without the owner.

Traditional comparisons must preserve frozen traces, count drivers separately and publish unfavorable PACT results. Equal behavior does not establish equivalent safety contracts.

Use --to compact-data for source RLE/shared-symbol compression. Keep baseline0.2 examples and frozen hashes intact; generate a separate .data.pact example. Data compression changes neither runtime semantics nor revision IDs. Tests must compare decoded IR and compiled bytes. Never expand unvalidated run counts or merge differing symbol maps.

Keep CHANGELOG.md and the public site in sync with concrete implemented/measured scope. Full test suite includes docs build and needs docs/site-requirements.txt; compiler runtime does not. Model trial recorder is not an authenticated evaluator or sandbox; never run generated candidates with trusted local performance fixtures. Performance numbers are local workload evidence, not universal ranks.

Use `pact locate SOURCE --function ID --node ID` for qualified compact/JSON physical positions. Coordinates use Unicode code points and belong to the exact source-byte hash, not just the semantic revision. JSON spans include ID value quotes/escapes. Ambiguous diagnostic candidates are not permission to guess a scope. JSON semantic diagnostic attachment covers locate and CLI source validation (excluding migration). Runtime replay and JSON migration diagnostic attachment are not implemented.

Compiler CLI JSON uses UTF-8/LF on every OS. Keep strict manifest format checks; tampering fixtures must write exact bytes. Traditional Windows trace comparisons explicitly normalize CRLF and retain raw transport hashes; do not confuse this with byte-identical output.

Module 0.3 requires declared cases for every export. Inspection declared_export_tests is a declaration map, not execution. Build manifests add actual tested receipts. Never generate arbitrary expected values just to satisfy missing-case hints. Default migration still targets 0.2; opt into 0.3 explicitly.

Module 0.4 guard/assert nodes check chosen runtime conditions. Guards skip bodies on false; traps retain prior writes. Reference ASSERTION_FAILED IDs and generic Wasm traps are not interchangeable diagnostics. Negative-trap declarations and replay are planned.
