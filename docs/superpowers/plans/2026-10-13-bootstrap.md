# PACT Bootstrap Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task.

**Goal:** Compile and execute an agent-first graph that prints `hola mundo, from an alien language`.

**Architecture:** A strict graph analyzer lowers into a bounded static execution plan. A Python Wasm emitter compiles the plan. An independent Node profile checker verifies the artifact before providing stdout.

**Tech Stack:** Python standard library, Node WebAssembly, no package downloads.

**Spec:** `docs/superpowers/specs/2026-10-13-bootstrap.md`.

## Global Constraints

- Four operations only; source graph and diagnostics are structured JSON.
- Limits: source 1 MiB, 256 nodes, 64 arguments, 16,384 UTF-8 output bytes.
- No guest disk/network access, implicit capability grant, loops or hidden effects.
- Tests execute actual artifacts; no mock Wasm engine.
- No claim of general verification, game support or universal platform support.

## Review Focus

- Malformed nested nodes: structured failure rather than traceback.
- Shared/cyclic graph: no hidden duplicate output or unbounded traversal.
- Unicode and empty strings: byte lengths, not character counts.
- Manifest tampering: reject before any output.
- Node ordering and permissions: reproducible build and deny by default.

## Task 1: Graph analyzer

Files: `pact/diagnostics.py`, `pact/graph.py`, `examples/hello.pact.json`, `tests/test_graph.py`.

Interface: `analyze(document: dict) -> dict`; `load_document(path) -> dict`; `PactError` carries a JSON diagnostic.

- [x] Write tests for exact plan emissions, malformed graphs, shared effects, contracts, order independence, Unicode and size bounds.
- [x] Run `python3 -m unittest tests.test_graph -v`; see missing behavior fail.
- [x] Implement schema, references, DFS/type inference, static evaluation, evidence and deterministic plan.
- [x] Run the same command; all tests pass. Commit task.

## Task 2: Wasm compiler and host

Files: `pact/wasm.py`, `pact/__main__.py`, `host/profile.mjs`, `host/run.mjs`, `tests/test_execution.py`.

Interfaces: `compile_plan(plan: dict) -> bytes`; host accepts wasm, manifest, explicit `--allow stdout`, optional output budget.

- [x] Write real Node tests for execution, interpreter parity, missing grants, module/hash tampering and Unicode byte limits.
- [x] Run `python3 -m unittest tests.test_execution -v`; see missing behavior fail.
- [x] Implement deterministic Wasm emitter, CLI, independent artifact profile checker and bounded stdout host.
- [x] Run the complete suite; all tests pass. Commit task.

## Task 3: Delivery and review

Files: `README.md`, `docs/verification.md`, generated `build/hello.wasm`, manifest and output transcript.

- [x] Build hello through the public CLI and run the independent host.
- [x] Run all tests and review source/artifacts against the spec.
- [x] Apply important findings with regression tests; record actual limitations.
- [x] Package source, docs, tests and actual artifacts in a ZIP; save deliverable.
