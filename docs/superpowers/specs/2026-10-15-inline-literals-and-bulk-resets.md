# Explicit-ID inline literals, bulk state resets and structured diagnostic fixes

Implement the `Next` roadmap stage (`Inline literals and bulk resets`) and structured diagnostic fixes without breaking stable node IDs, explicit effect declarations (`writes`), existing `pact 0.2`/`0.3` source fixtures, or deterministic WebAssembly compilation.

## 1. Explicit-ID inline literals (`pact 0.4` compact frontend)

In `pact 0.2` and `pact 0.3`, every integer literal operand in `alien-harvest` requires a standalone `nXXXX = i32.const VALUE` line (527 out of 1,218 total nodes in `examples/alien-harvest.pact.json`, 100% of which are single-use and immediately precede their consumer node). Naively inlining unlabelled numbers would either erase node IDs or require synthetic IDs, violating `AGENTS.md` ("Keep IDs stable. No implicit indices, hidden constants").

`pact 0.4` (`dumps(document, inline=True)` and CLI `--to compact-inline`) introduces explicit-ID inline integer literals using the `NODE_ID=INT` token syntax inside `args` operand lists:

```pact
n0002 = set input.left n0000=0 n0001=0
```

- Because `=` is outside `IDENTIFIER` (`[A-Za-z][A-Za-z0-9_.:\-]{0,63}`), `NODE_ID=INT` is unambiguous with colon identifiers (`node:0`), strings, JSON arrays, and negative numbers.
- During `loads()`, each `NODE_ID=INT` token in a function node's `args` list validates `NODE_ID` and signed 32-bit `INT`, emits `{"id": NODE_ID, "op": "i32.const", "value": INT}` immediately before the consumer node in `function["nodes"]`, and substitutes `NODE_ID` into `node["args"]`.
- During `dumps(document, inline=True)`, any contiguous suffix of single-use (`refcount == 1`) `i32.const` nodes immediately preceding a consumer node in the exact left-to-right order of `consumer["args"]` is formatted inline as `ID=VALUE`. Shared `i32.const` nodes (`refcount > 1`) remain standalone lines.
- `loads(dumps(document, inline=True))` on a `pact.module/0.2.0` document reconstructs the exact same IR, canonical `revision(document)` SHA-256 hash, and compiled WebAssembly bytes.
- Baseline `pact 0.2` (`examples/alien-harvest.pact`, 51,244 bytes) and `pact 0.3` (`examples/alien-harvest.data.pact`, 43,543 bytes) remain untouched; `examples/alien-harvest.inline.pact` (`pact 0.4`) reduces the game source to 34,057 UTF-8 bytes and 797 lines (-527 lines).

## 2. Checked runtime bulk resets (`state.reset` / `reset`) — `pact.module/0.2.0`

`state.reset` changes accepted module semantics, so it ships as a new numeric module version `pact.module/0.2.0` instead of extending `pact.module/0.1.0` in place. `pact.module/0.1.0` validation is preserved exactly: `analyze_module` accepts both format versions, and a 0.1.0 document using `state.reset` is rejected (`OP_UNKNOWN`) exactly as before. The 0.2.0 grammar adds `state.reset` (compact alias `reset`) in `pact/module.py`, `pact/compact.py`, `pact/reference.py`, `pact/module_wasm.py`, `pact/inspection.py`:

```pact
n0000 = reset ["input.left","input.right","game.phase"]
```

- Schema: closed record `{"id": ID, "op": "state.reset", "cells": [CELL_ID, ...]}` with 1..128 unique mutable state cell IDs.
- Rejects unknown cells (`STATE_MISSING`), immutable cells (`STATE_IMMUTABLE`), duplicate cells in the same operation (`ID_DUPLICATE`), and undeclared function writes (`WRITE_MISMATCH`).
- Returns `unit` (subject to single-consumer `EFFECT_SHARED` verification) and accounts `sum(layout[c]["count"] for c in node["cells"])` toward `MAX_WORK` and `COMPILER_BUDGET`.
- Executes identically in `Machine` (`pact/reference.py`) and compiled WebAssembly (`pact/module_wasm.py`). Replacing the 373-node `game.init` sequence in Alien Harvest with a single `state.reset` node reduces `game.init` from 373 nodes to 1 node and shrinks the compiled `.wasm` binary by 3,097 bytes (from 28,940 to 25,843 bytes) while producing identical state across gameplay and playthrough checks.

### Migration path

`pact.module.migrate_module(document)` (CLI: `python3 -m pact migrate SOURCE -o OUTPUT`) migrates a validated `pact.module/0.1.0` document to `pact.module/0.2.0`. The migration changes only the format version and adds no `state.reset` nodes, so the migrated document compiles to byte-identical WebAssembly; its canonical semantic revision changes because the format version is semantic content, and revision-checked patches against a 0.1.0 source must be regenerated after migration. `pact.compact.loads` migrates 0.1.0 compact/JSON input in memory, so existing sources remain readable; `pact 0.4` inline literals require a 0.2.0 document and are rejected under 0.1.0. The Alien Harvest example sources are migrated to `pact.module/0.2.0` and `examples/patches/jump.patch.json` carries the migrated source revision; `examples/patches/counter-amount.patch.json` demonstrates patching a migrated 0.1.0 module.

## 3. Actionable diagnostic fixes (`pact/diagnostics.py`)

Extend `PactError` with an optional `fix` dictionary on `error.diagnostic` for deterministic single-turn agent repair:
- `WRITE_MISMATCH`: `{"op": "set_writes", "function": fn_id, "declared_writes": [...], "expected_writes": [...]}`
- `NODE_UNREACHABLE`: `{"op": "remove_unreachable", "function": fn_id, "unreachable_nodes": [...]}`
