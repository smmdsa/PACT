# Agent guidance

Read README.md, docs/syntax.md and docs/security.md before changing semantics. ROADMAP.md describes planned work. Compact 0.2 and optional compressed data0.3 wrap graph 0.0.1/module 0.1.0; preserve these distinctions.

Prefer focused function/dependency reads. Keep IDs stable. Do not replace semantic names with undocumented opcodes. Effects, array indices, overflow and grants remain explicit.

Use `python3 -m pact symbols SOURCE` for discovery and `python3 -m pact inspect SOURCE --function ID` for selected context. Inspect helper bodies separately when needed. Responses are not buildable modules; omitted state/test bodies require further reads. Revisions identify semantic source contents, not signatures or author authority. Use `pact patch` with an expected revision for a new candidate; inspect the receipt and executable test evidence. In-place filesystem compare-and-swap is not supported.

Parallel contributors must own nonoverlapping files and report executed checks. Read docs/agent-contributions.md before preparing a contribution.

Compact and JSON examples must reconstruct identical IR. After authoring changes regenerate JSON then explicitly convert to compact; inspect the diff before overwriting hand edits.

Run the full unittest suite for compiler changes and input-only playthrough for gameplay. Representation-only changes must preserve compiled bytes. Never report bytes as tokens or prepared deployment as live. Do not select a license without the owner.

Traditional comparisons must preserve frozen traces, count drivers separately and publish unfavorable PACT results. Equal behavior does not establish equivalent safety contracts.

Use --to compact-data for source RLE/shared-symbol compression. Keep baseline0.2 examples and frozen hashes intact; generate a separate .data.pact example. Data compression changes neither runtime semantics nor revision IDs. Tests must compare decoded IR and compiled bytes. Never expand unvalidated run counts or merge differing symbol maps.
