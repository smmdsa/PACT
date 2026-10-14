# Contributing

Read ROADMAP.md and docs/syntax.md. Keep changes focused. Add regression tests for parser/validator/execution changes; compare the reference VM to actual Wasm for semantic changes. Preserve stable IDs and explicit effects.

Run `python3 -m unittest discover -v` and `python3 -m tools.build_site`. Gameplay changes require the input-only playthrough. State evidence and unavailable checks explicitly.

Before community code contributions, the owner should select a license and contribution terms. No license is chosen automatically.
