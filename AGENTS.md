# Agent guidance

Read README.md, docs/syntax.md and docs/security.md before changing semantics. ROADMAP.md describes planned work. Compact 0.2, compressed data 0.3 and literal/inline source 0.4 wrap graph 0.0.1 or numeric modules 0.1.0/0.2.0; preserve these distinctions. Reading/converting preserves revisions. Only explicit migration changes numeric format; state.reset requires 0.2.0.

Prefer focused function/dependency reads. Keep IDs stable. Do not replace semantic names with undocumented opcodes. Effects, array indices, overflow and grants remain explicit.

Use `python3 -m pact symbols SOURCE` for discovery and `python3 -m pact inspect SOURCE --function ID` for selected context. Inspect helper bodies separately when needed. Responses are not buildable modules; omitted state/test bodies require further reads. Revisions identify semantic source contents, not signatures or author authority. Use `pact patch` with an expected revision for a new candidate; inspect the receipt and executable test evidence. In-place filesystem compare-and-swap is not supported.

Parallel contributors must own nonoverlapping files and report executed checks. Read docs/agent-contributions.md before preparing a contribution.

Compact and JSON examples must reconstruct identical IR. After authoring changes regenerate JSON then explicitly convert to compact; inspect the diff before overwriting hand edits.

Run the full unittest suite for compiler changes and input-only playthrough for gameplay. Representation-only changes must preserve compiled bytes. Never report bytes as tokens or prepared deployment as live. Do not select a license without the owner.

Traditional comparisons must preserve frozen traces, count drivers separately and publish unfavorable PACT results. Equal behavior does not establish equivalent safety contracts.

Use --to compact-data for source RLE/shared-symbol compression. Keep baseline0.2 examples and frozen hashes intact; generate a separate .data.pact example. Data compression changes neither runtime semantics nor revision IDs. Tests must compare decoded IR and compiled bytes. Never expand unvalidated run counts or merge differing symbol maps.

Keep CHANGELOG.md and the public site in sync with concrete implemented/measured scope. Full test suite includes docs build and needs docs/site-requirements.txt; compiler runtime does not. Model trial recorder is not an authenticated evaluator or sandbox; never run generated candidates with trusted local performance fixtures. Performance numbers are local workload evidence, not universal ranks.
