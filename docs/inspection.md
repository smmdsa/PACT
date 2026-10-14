# Selective numeric-module inspection

Use `python3 -m pact symbols SOURCE` to discover functions and `python3 -m pact inspect SOURCE --function ID` to retrieve one function's context. Compact and JSON source reconstruct the same module IR before inspection (loading preserves the declared version and revision). The compiler validates the entire source, including functions and assets absent from the response. Numeric modules `pact.module/0.1.0` and `pact.module/0.2.0` are supported; text graph `pact.graph/0.0.1` inspection is explicitly unsupported.

Python callers use `pact.inspection.inspect_function(document, function_id)` and `pact.inspection.symbols(document)`. Both return ordinary JSON-compatible dictionaries and raise `PactError` for rejected input. An unknown selected function produces `FUNCTION_MISSING`; text graphs produce `INSPECTION_UNSUPPORTED`. Invalid modules retain the existing analyzer's diagnostics.

## Function context

`inspect_function` returns `format: "pact.inspection/0.1.0"`, `source_format`, `context_only: true`, `buildable: false`, and `semantic_revision_sha256`, followed by these fields:

| Field | Contents |
| --- | --- |
| `selected_function` | Complete original function record, preserving IDs, operations, ordered parameters and operands, and entry |
| `direct_callees` | Sorted IDs directly called by the selected function |
| `transitive_callees` | Sorted IDs reached through one or more calls, including direct callees |
| `direct_callers` | Sorted IDs directly calling the selected function |
| `transitive_callers` | Sorted IDs reaching the selected function through one or more calls, including direct callers |
| `dependency_functions` | Signatures of every transitive callee: `id`, `params`, `locals`, `result`, `writes`; bodies omitted |
| `constants` | Referenced constant names and values from the selected function and all transitive callees |
| `cells.read`, `cells.write` | Sorted metadata for cells loaded/stored by the selected function and transitive callees: `id`, `type: "i32"`, `count`, `mutable` |
| `test_summaries` | Sorted `id`/`function` pairs for declared tests targeting the selected function or any transitive caller |
| `omitted` | Explicitly identifies `dependency_function_bodies`, `cell_initial_values`, `assets`, `test_case_bodies` |

A cell may occur in both read and write lists. A function with no callers, callees, constants, cells or applicable tests returns empty collections. Dependencies are syntactic call-graph closure, including calls in branches that may never execute for a particular input. Test summaries identify existing cases; they contain neither case bodies nor claims that those tests passed. Tests of callees are not included merely because the selected function calls them.

Inspect each helper separately when its body is needed. The returned context is intentionally not an executable or buildable module. No cell initialization arrays, map data, tile pixels, palette data, or test `set`/`expect` arrays are emitted. Individual literals explicitly written inside the selected function and referenced numeric constants remain visible.

## Discovery

`symbols` returns `format: "pact.symbols/0.1.0"` and the same provenance and context markers. Its `functions` list is sorted by ID. Each item includes the signature fields above, `exported`, direct/transitive callee and caller IDs, and sorted `constants`, `read_cells`, `write_cells` IDs. Footprints include transitive callees. It omits all function bodies, constant values, cell initialization, assets and test case bodies.

## Revision and determinism

`semantic_revision_sha256` is SHA256 of the entire validated document serialized as UTF-8 JSON with sorted dictionary keys, no insignificant whitespace, and unescaped Unicode. It includes data omitted from the response, so changing an unrelated cell or asset still changes the revision. JSON formatting and dictionary insertion order do not affect it; equal reconstructed compact/JSON documents share a revision.

Every array's order is retained in this hash, including parameter lists, operands, declarations and tests. Thus this is formatting-insensitive canonical document identity, **not** identity invariant under arbitrary IR reordering or proof of behavioral equivalence. Reordering declarations may change the revision even when compilation produces identical bytes. This field is distinct from the analyzer's `source_sha256`, which normalizes some declaration arrays.

Reference lists and summaries are sorted, while the selected function's source arrays are preserved. Output dictionaries use deterministic key insertion order even when input dictionary order varies. Returned records are detached from the source and can be modified without changing the original document.

Call relationships and footprints cannot establish semantic purpose, single responsibility, or total impact. Shared state, host presentation and data changes can connect functions without a call edge. The test selection is a conservative call-graph aid, not complete change-impact analysis. The revision detects stale context; revision-checked candidate patches are now implemented (see transactions.md), while in-place filesystem compare-and-swap remains unsupported.
