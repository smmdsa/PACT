# Source locations

PACT's compact-source queries return physical positions without adding metadata to the semantic IR. Revisions, node IDs and compiled bytes remain unchanged.

```sh
python3 -m pact locate examples/alien-harvest.inline.pact --function player.move --node n0000
python3 -m pact locate examples/alien-harvest.inline.pact --function player.move
```

`--function` and `--node` are optional. A function query includes its declaration and node definitions; a node query may return matching definitions in multiple functions. Supply both for a qualified selection. Unknown selections reject. Text graphs support node queries with `function: null`; a function query on a text graph rejects.

The response has format `pact.source-map/0.1.0`, `context_only: true`, `buildable: false`, `source_path` for file queries, a hash of the exact UTF-8 source bytes, and a separate semantic revision. Use the source hash to detect edits before applying coordinates. Different formatting, comments or line endings change the source hash even when the semantic revision stays the same. File queries read one bounded binary snapshot, preserving CRLF.

Each position records `kind`, `function`, `id`, `line`, `column`, and exclusive `end_column`. Coordinates start at one and count Unicode code points. A tab counts as one character, not an expanded display width. Lines are separated only by LF: Unicode separators inside strings do not add physical lines. Normal nodes point to their ID; function declarations point to the function ID; inline constants point to the complete `ID=INTEGER` operand token. This is a definition map, not a complete AST/source range or reference index.

## Rejections

Compact parsing errors add a coarse `source_location` containing the physical line and column one. Semantic errors with a unique named declaration add its definition span. When a diagnostic's unqualified ID appears in multiple scopes, `source_candidates` lists possible definitions instead of guessing one. Errors without a named declaration omit a semantic location. Contract metadata is not mapped; IDs colliding with that namespace omit locations to avoid attributing a contract error to a node. Existing rejection codes, node IDs and structured fixes remain available.

These locations describe the original compact snapshot only. JSON physical maps, generated Wasm offsets, runtime trap replay and source-aware patch editing remain planned. Query output validates the entire source; it does not accept a partial or invalid program. Location lookup never executes source as host code.
