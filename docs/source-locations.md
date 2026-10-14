# Source locations

PACT's compact and JSON source queries return physical positions without adding metadata to the semantic IR. Revisions, node IDs and compiled bytes remain unchanged.

```sh
python3 -m pact locate examples/alien-harvest.inline.pact --function player.move --node n0000
python3 -m pact locate examples/alien-harvest.inline.pact --function player.move
python3 -m pact locate examples/alien-harvest.pact.json --function player.move --node n0000
```

`--function` and `--node` are optional. A function query includes its declaration and node definitions; a node query may return matching definitions in multiple functions. Supply both for a qualified selection. Unknown selections reject. Text graphs support node queries with `function: null`; a function query on a text graph rejects.

The response has format `pact.source-map/0.1.0`, `context_only: true`, `buildable: false`, `source_path` for file queries, a hash of the exact UTF-8 source bytes, and a separate semantic revision. Use the source hash to detect edits before applying coordinates. Different formatting, comments or line endings change the source hash even when the semantic revision stays the same. File queries read one bounded binary snapshot, preserving CRLF.

Each position records `kind`, `function`, `id`, `line`, `column`, and exclusive `end_column`. Coordinates start at one and count Unicode code points. A tab counts as one character, not an expanded display width. Lines are separated only by LF: Unicode separators inside strings do not add physical lines. Normal nodes point to their ID; function declarations point to the function ID; inline constants point to the complete `ID=INTEGER` operand token. This is a definition map, not a complete AST/source range or reference index.

For JSON, spans cover the complete string value of a definition's `id`, including quotes and any escapes. Returned IDs are decoded: `"\\u007a"` selects node `z`, while its span still covers the original eight-character token. Object field order, indentation and minification do not affect identity. Only root graph nodes, module functions and their nodes are indexed; references, tests, cells, contracts and lookalikes in strings are excluded. Positions follow physical source order even when a function's ID occurs after its nodes.

JSON queries reject duplicate decoded keys, malformed JSON and semantically invalid programs before returning positions. The scanner visits only known definition containers and skips unrelated values. Reads remain limited to one 1 MiB snapshot; no host code, model output or runtime candidate is executed.

## Rejections

Compact parsing errors add a coarse `source_location` containing the physical line and column one. Semantic errors with a unique named declaration add its definition span. When a diagnostic's unqualified ID appears in multiple scopes, `source_candidates` lists possible definitions instead of guessing one. Errors without a named declaration omit a semantic location. Contract metadata is not mapped; IDs colliding with that namespace omit locations to avoid attributing a contract error to a node. Existing rejection codes, node IDs and structured fixes remain available.

JSON semantic rejections now attach definition spans in `locate` and CLI `check`, `build`, `interpret`, `symbols`, `inspect`, `convert`, explicit `migrate` and source validation for `patch`. Attachment uses the same bounded original snapshot as validation, preserving escapes and CRLF. Raw `load_document` callers retain parse-only behavior unless they opt into `validate_source=True` or explicit `migrate_to`. Explicit migration validates through the existing module migrator and attaches errors against the original bounded snapshot; unknown formats retain `FORMAT_UNSUPPORTED`, and the default target remains module 0.2. Target-only errors without a definition ID retain their structured fix without a fabricated span. Failed CLI migrations do not write outputs. Patch-operation/candidate errors do not attach original-source spans. Malformed JSON and invalid definition containers retain their rejection without fabricated spans. Reference replay attaches qualified positions to runtime diagnostics; see [replay](replay.md). Wasm replay returns generic traps without physical node attribution. Generated Wasm offsets and source-aware patch editing remain planned. Query output validates the entire source; it does not accept a partial or invalid program. Location lookup never executes source as host code.
