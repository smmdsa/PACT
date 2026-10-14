# Revision-checked transactions

`pact.transactions.apply_patch(document, patch)` constructs a detached numeric-module candidate from existing nodes, constants and tests. It validates the entire original module, checks its semantic revision, applies the operations to a deep copy and validates the entire candidate. It returns the candidate dictionary. Failures raise `PactError`; neither input is modified.

This API runs the numeric type/effect/reference/cycle/budget and test-schema validator. It does **not** execute declared tests. A structurally valid constant change can make an existing expected result fail at execution. The CLI compiles the candidate and executes its declared tests against actual WebAssembly before returning a successful receipt or publishing source.

## Patch format

A patch is a closed-schema JSON record:

```json
{
  "format": "pact.patch/0.1.0",
  "expected_revision_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "operations": [
    {"op": "set_constant", "name": "amount", "value": 8}
  ]
}
```

The displayed hash is illustrative: obtain the actual source revision from `pact symbols SOURCE`, `pact inspect SOURCE --function ID` or `pact.revision.revision(document)`. There must be 1–256 operations. Every operation must contain exactly the fields shown below; replacements must satisfy the module's existing closed schema.

| Operation | Fields | Target |
| --- | --- | --- |
| `replace_node` | `op`, `function`, `id`, `node` | Existing node `id` within existing function `function` |
| `set_constant` | `op`, `name`, `value` | Existing signed i32 constant `name` |
| `replace_test` | `op`, `id`, `test` | Existing declared test `id` |

A node or test replacement must preserve the targeted ID. No operation creates or removes targets, changes function signatures or adds cells, assets, exports or host capabilities. Changes to operations and test contents remain subject to complete module validation. Repeating the same target in a single patch is rejected even when replacements are identical. Equal node IDs in different functions are distinct targets. Operations retain declaration order and do not reorder arrays.

A stale digest raises `PATCH_STALE`; absent targets raise `PATCH_TARGET_MISSING`; changed replacement IDs raise `PATCH_ID_CHANGED`; duplicate targets raise `PATCH_TARGET_DUPLICATE`. Invalid format, operation names, digest syntax or operation count raise `PATCH_INVALID`. Closed-schema, identifier and numeric-module errors retain the validator's existing diagnostic codes.

## Review and publication

```sh
python3 -m pact patch examples/alien-harvest.pact --patch change.json --dry-run
python3 -m pact patch examples/alien-harvest.pact --patch change.json -o build/alien-harvest-updated.pact --to compact
```

Dry-run validates the candidate, compiles it and executes its declared Wasm tests, then prints a reviewable receipt without creating output files. Normal publication requires a distinct, new output path; source and existing output files cannot be overwritten. `--to compact` and `--to json` select representation. Normal publication stages bytes in the destination directory and atomically links them into an absent destination, cleaning up the staged file afterward. Source and patch reads are bounded and reject duplicate JSON keys.

The receipt identifies the source snapshot that was read. This operation does not implement an in-place, cross-process compare-and-swap: another process may change the original source after it is read. Keep the receipt and review the candidate through the repository's ordinary expected-head publication checks.

## Content identity and authority

`revision(document)` uses SHA256 of UTF-8 JSON with sorted object keys, compact separators and `ensure_ascii=False`. Every array preserves its order, including function declarations, cells, nodes and operands. Whitespace and object key order in source representations do not affect this semantic revision. The helper assumes callers have validated their supported document profile; inspection and transactions do so before using it.

The helper preserves the existing inspection revision exactly. It differs from compiler plan hashes that normalize some declaration arrays. Compare patch revisions with inspection's `semantic_revision_sha256`, not a build plan's `source_sha256`.

A revision identifies content, without authenticating its author or approving its intent. It is not a signature, authorization token or proof that executable tests are complete. Transactions introduce no guest authority, evaluation of host-language source or new execution semantics. Source versions remain compact `0.2` and numeric module `0.1.0`/`0.2.0` (loading preserves the declared version and revision); text graph transactions are unsupported.

JSON publication uses a .json candidate filename; a .pact suffix with --to json is rejected before writing. Both dry-run and publication check the serialized source limit. Atomic publication requires hard-link support on the output filesystem; an unsupported filesystem produces an IO error without overwriting existing paths.

Module migration is explicit (`pact migrate` or `migrate_module`). It changes the semantic revision, so prepare patches against the migrated document when adding 0.2.0 operations. Representation conversion, including compact 0.4 inline literals, preserves the source version and existing patch revisions.
