# Agent guidance

Read README.md, docs/syntax.md and docs/security.md before changing semantics. ROADMAP.md describes planned work. Compact 0.2 wraps graph 0.0.1/module 0.1.0; preserve these distinctions.

Prefer focused function/dependency reads. Keep IDs stable. Do not replace semantic names with undocumented opcodes. Effects, array indices, overflow and grants remain explicit.

Compact and JSON examples must reconstruct identical IR. After authoring changes regenerate JSON then explicitly convert to compact; inspect the diff before overwriting hand edits.

Run the full unittest suite for compiler changes and input-only playthrough for gameplay. Representation-only changes must preserve compiled bytes. Never report bytes as tokens or prepared deployment as live. Do not select a license without the owner.
