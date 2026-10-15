# Órbita: a future to cultivate

[Explore Órbita](../orbita.html) · [PACT source](../examples/orbita.pact) · [Demos & Examples](../demos.html)

Órbita is a human-facing interface experiment over an authored PACT kernel. Six speculative possibilities form a spatial constellation. Attention is represented by six seeds, with up to three per possibility. Investing or withdrawing attention changes the editorial narrative. These are fictional possibilities, not predictions or generated advice.

## Design and implemented scope

The experience replaces a sequence of screens with a persistent field of possibilities, a focus panel and reversible decisions. Explore keeps the constellation stable; Acercar brings the selected possibility to the top of an enlarged world; Entrelazar emphasizes links between cultivated possibilities. A list provides a conventional alternative to the spatial view. The layout adapts to narrow viewports and respects reduced motion.

The visual direction uses warm paper, ink, restrained terracotta, editorial serif headings and native SVG orbital drawings. It uses no external fonts, images, CDN dependencies or connected model. “Novel” describes the design intent; no claim of historical uniqueness is made.

## Runtime boundary

| PACT / compiled WebAssembly | Browser presentation |
| --- | --- |
| Selected possibility and current lens | HTML controls, SVG geometry and CSS layout |
| Six-seed budget and 0–3 attention levels | Spanish editorial copy and narrative interpolation |
| Valid action checks before parameterized writes | Keyboard/pointer events mapped to exported functions |
| Snapshot history, undo, redo and branch truncation | Reading compiler-described memory; no direct state writes |
| Reset and bounded 32-snapshot history | Dialogs, list alternative and status announcements |

Source representation is `pact 0.4`; numeric semantics are `pact.module/0.4.0`. The compiler executes six declared cases against actual Wasm during the site build, one per public action. This remains an application over the existing language; it adds no language syntax or UI framework.

## History and limits

Only attention allocations are historical. Selecting an idea or switching lenses does not add a decision. Undo followed by a new allocation discards the old future. On overflow the oldest snapshot is discarded, retaining 32 compositions. Reset clears focus, lens, allocations and history. Reload starts a new session; nothing is sent to a server or persisted.

## Verification

`tests/test_orbita.py` checks focus, lenses, budget, per-idea bounds, withdrawal at zero, undo/redo, branching, rolling history, reset, rejection before writes and actual build evidence. A deterministic mixed sequence compares the reference interpreter with real WebAssembly after more than 300 calls and checks allocation invariants at each reference step.

The Chromium workflow exercises selecting, investing, changing lens, undo/redo, branching, list navigation, dialogs, resetting and responsive layout. These finite checks do not establish universal correctness, real-device certification or model productivity. Órbita is not one of the generated GPT benchmark candidates.
