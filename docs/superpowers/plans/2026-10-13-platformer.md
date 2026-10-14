# PACT Platformer Implementation Plan

> For agentic workers: use superpowers:executing-plans; user requested continuous execution.

**Goal:** Deliver an original playable scrolling platformer whose simulation is PACT compiled to Wasm.
**Architecture:** Extend the graph frontend with numeric state, bounded control flow and functions. Emit generic Wasm instructions; render exported memory with a browser host. Embed artifacts into one HTML.
**Tech Stack:** Python standard library, WebAssembly, Canvas/WebAudio, Node and Playwright for verification.
**Spec:** docs/superpowers/specs/2026-10-13-platformer.md.

## Global Constraints
- Keep bootstrap backwards compatible. No downloaded runtime/game dependencies.
- No hidden platformer opcode or simulation logic in JavaScript renderer.
- Stateful kernel has checked indexed access, no recursion and bounded repeats.
- Assets live in PACT source and compiled memory.

## Review Focus
- Stateful expression reuse must read current values rather than cache stale data.
- Imported/written state and shared effects must not enlarge function authority.
- Bad array indexes and invalid tiles fail explicitly.
- Gameplay must be finishable by inputs, not only test-state injection.
- Deliverable must work from file:// without external files.

## Tasks
- [x] Kernel: write missing-behavior tests; observe red; implement analyzer, reference VM and numeric Wasm emitter; run tests.
- [x] Game: generate PACT modules and pixel assets; write mechanics/contract tests; observe red and implement; compare VM and Wasm.
- [x] Host: build self-contained HTML, keyboard/touch/audio/rendering; test actual browser, complete game, verify death/restart and capture screenshot.
- [x] Review/ship: fresh independent review; fix important findings with regression tests; rerun checks; package/save HTML and complete sources.
