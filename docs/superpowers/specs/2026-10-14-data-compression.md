# Reversible compressed data frontend

Implement compact frontend 0.3 without changing graph/module execution semantics or IDs. Keep compact 0.2 readable and canonical output default. Add optional `dumps(document, compressed=True)` and CLI convert `--to compact-data`; patch `--to compact-data` similarly emits new compressed candidate. Text graph compressed mode may use 0.3 header with unchanged sections, but no compressed module-only fields.

## Cells

`cells.packed` replaces `cells`. Each cell preserves id/mutable and exactly one of values or runs; runs are [positive_count, signed_i32_value] pairs. Encoder chooses runs only when complete canonical JSON record is strictly shorter in UTF8 bytes. Decoder validates all run counts, values, cell IDs, duplicates, aggregate state budget and per-cell count BEFORE expanding. Total state at most16384 i32 values. Never accept bool as count/value/mutable numeric. No arbitrary compression buffers or code evaluation. Preserve cell order, array order and exact values.

## Atlas

`assets.shared` replaces `assets`: {palettes, symbol_tables, tiles}. Symbol tables are an ordered list of raw symbol->color-name/null dictionaries. Each tile keeps id,palette,pixels and either inline symbols or integer symbol_table reference. Share only identical mappings where full encoded record cost including the table declaration is beneficial; preserve different per-tile mappings and order, no inferred palette defaults. At most128 tables/tiles; validate shape, references and bounded symbol tables before reconstruction; existing asset validator remains authoritative for palette names, colors, pixels and atlas bounds.

## Frontend

Recognize headers pact0.2 and pact0.3. Compressed sections only permitted under0.3 and only at module top level, duplicate plain/packed sections rejected regardless order. Decode to exactly existing IR then run existing validator. No new fields reach compiler. Default dumps remains byte-identical0.2; compressed mode produces0.3 and explicitly chosen packed/shared sections when beneficial. Roundtrip preserves revision hash and compiled bytes; old example/patch remains compatible. Generated compressed game is a separate example, not overwrite baseline fixture/hash results.

## Measurement and scope

Record bytes and actual both tokenizer counts for minified JSON, compact0.2 and compressed0.3 of equal validated IR. Hash sources and Wasm; no claims of general efficiency or agent productivity. Game victory input-only replay remains identical. This stage delivers RLE initial data and shared symbol tables; inline literals and runtime bulk resets remain a separate pending feature because they require separate ID/semantics design.
