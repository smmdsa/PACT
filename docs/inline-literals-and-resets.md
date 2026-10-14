# Explicit-ID inline literals (`pact 0.4`), bulk state resets (`state.reset`) and actionable diagnostics

## 1. Reversible inline integer literals — `pact 0.4`

In `pact 0.2` and `pact 0.3`, every constant operand in a numeric module function requires a separate `i32.const` node line. Across `examples/alien-harvest.pact`, 527 of the 1,218 total AST nodes (43.3%) are single-use `i32.const` nodes that immediately precede their consumer node.

`pact 0.4` (`dumps(document, inline=True)` or CLI `--to compact-inline`) allows single-use `i32.const` operands in `args` lists to be written inline while preserving their explicit node IDs via `NODE_ID=INT`:

```pact
n0002 = set input.left n0000=0 n0001=0
```

```sh
python3 -m pact convert examples/alien-harvest.pact --to compact-inline -o build/alien-harvest.inline.pact
python3 -m pact build examples/alien-harvest.inline.pact -o build/game.wasm
python3 -m pact patch examples/alien-harvest.inline.pact --patch examples/patches/jump.patch.json --dry-run
```

### Invariants preserved

- **Exact IR and revision identity**: `loads()` expands `n0000=0` into `{"id": "n0000", "op": "i32.const", "value": 0}` immediately before the consumer node in `function["nodes"]` and places `"n0000"` in `node["args"]`. The decoded `pact.module/0.1.0` document, canonical `revision(document)` SHA-256 hash, `pact inspect` output, `pact patch` targets, and compiled WebAssembly bytes are 100% identical to `pact 0.2` and `pact 0.3`.
- **Shared constants remain explicit**: Any `i32.const` node referenced more than once (`refcount > 1`) remains a standalone line.
- **Strict validation**: Inline literals are rejected in `pact 0.2`/`0.3`, in top-level text graphs, in fixed non-`args` fields, when `NODE_ID` duplicates any node ID in the function, or when `INT` is not a canonical signed 32-bit integer (`-2147483648..2147483647`).

### Measured game source (`examples/alien-harvest`)

| Representation | Header | Lines | UTF-8 bytes | IR / Revision / Wasm |
| --- | --- | ---: | ---: | --- |
| Minified JSON (`alien-harvest.pact.json`) | JSON | 1 | 88,379 | Baseline |
| Compact 0.2 (`alien-harvest.pact`) | `pact 0.2` | 1,324 | 51,244 | Identical |
| Compact 0.3 data (`alien-harvest.data.pact`) | `pact 0.3` | 1,324 | 43,543 | Identical |
| Compact 0.4 inline (`alien-harvest.inline.pact`) | `pact 0.4` | 797 | 34,057 | Identical |

*(Note: Exact UTF-8 byte counts and SHA-256 digests are verified in the offline test environment; optional `tiktoken` token counts can be generated in environments with cached `tiktoken 0.12.0` resources.)*

## 2. Checked runtime bulk state resets (`state.reset` / `reset`)

Numeric modules support resetting 1..128 mutable state cells to their declared initial values in a single checked operation:

```pact
n0000 = reset ["input.left","input.right","game.phase"]
```

- **Explicit effect checking**: Every cell listed in `cells` is added to the function's observed write set and checked against `fn["writes"]` (`WRITE_MISMATCH`), cell existence (`STATE_MISSING`), mutability (`STATE_IMMUTABLE`), uniqueness (`ID_DUPLICATE`), and single-consumer unit sequencing (`EFFECT_SHARED`).
- **Bounded work accounting**: Contributes `sum(layout[cell]["count"] for cell in node["cells"])` to `MAX_WORK` and `COMPILER_BUDGET`.
- **Reference VM & Wasm equivalence**: Both `Machine` (`pact/reference.py`) and `compile_module` (`pact/module_wasm.py`) reset the listed cells to their initial values. Replacing the 373-node `game.init` in Alien Harvest with a single `reset` node reduces `game.init` from 373 nodes to 1 node and reduces the compiled WebAssembly binary from 28,940 bytes to 25,843 bytes (-3,097 bytes) with identical runtime state.

## 3. Structured diagnostic fixes (`pact/diagnostics.py`)

When `analyze_module` rejects a module for a deterministic mismatch, `PactError.diagnostic` includes a structured `fix` object so agents can repair the module without extra inspection turns:

- `WRITE_MISMATCH`: `{"op": "set_writes", "function": fn_id, "declared_writes": [...], "expected_writes": [...]}`
- `NODE_UNREACHABLE`: `{"op": "remove_unreachable", "function": fn_id, "unreachable_nodes": [...]}`
