# Reversible source data compression — compact 0.3

This optional frontend compresses initial cell arrays and repeated sprite symbol dictionaries. It reconstructs exactly the existing numeric IR. Node IDs, cell order, array values, revision hash, state layout, atlas RGBA and compiled Wasm remain unchanged. It reduces source context, not runtime memory or execution work.

```sh
python3 -m pact convert examples/alien-harvest.pact --to compact-data -o build/game.data.pact
python3 -m pact build examples/alien-harvest.data.pact -o build/game.wasm --html build/game.html
python3 -m pact patch examples/alien-harvest.data.pact --patch examples/patches/jump.patch.json --dry-run
```

Compact0.2 remains readable and the default canonical output. `dumps(document, compressed=True)` or CLI `--to compact-data` emits `pact 0.3`. Existing plain sections remain valid. Compressed sections are permitted only at module top level under0.3. The frontend rejects duplicate plain/compressed versions of a section regardless of order.

## Initial arrays

```text
cells.packed [{"id":"level.tiles","mutable":false,"runs":[[16,0],[8,1]]}]
```

Each record has id, exact boolean mutable and exactly one of values or runs. A run is [positive_count, signed_i32_value]. There are no implicit palette numbers or magic opcode meanings. The example encodes sixteen zeros followed by eight ones; the normal module declaration gives values their meaning.

All records are validated before expansion: at most128 cells,4096 values per cell and16384 values total. Booleans are rejected as counts/numbers; duplicate IDs, bad fields and invalid values reject. Encoder chooses RLE only for a strictly smaller full canonical JSON record. Plain arrays are retained otherwise; adjacent equal decoder runs are allowed, and reserialization normalizes them.

## Shared symbols

`assets.shared` contains palettes, symbol_tables and tiles. Tables contain ordinary symbol-to-color-name/null dictionaries. Each tile preserves id, palette and pixels; it uses either symbols inline or an integer symbol_table reference. A boolean is not a reference.

Only identical mappings are grouped, regardless of palette IDs. Different dictionaries remain distinct. Each shared table holds at most64 symbols; at most128 tables/tiles are accepted. Larger existing valid inline maps remain inline, preserving compatibility. Palette membership and pixel semantics still pass the normal asset validator. No inferred colors or palette defaults.

Sharing is selected only when the complete encoded asset record shrinks, including table declarations/references. Frontend checks whole section cost too, including longer section names. This is deterministic byte selection, not guaranteed minimum token count or globally optimal compression.

## Measured game source

| Representation | UTF8 bytes | o200k_base tokens | cl100k_base tokens |
| --- | ---: | ---: | ---: |
| Minified JSON | 88,379 | 35,903 | 35,876 |
| Compact0.2 | 51,244 | 24,851 | 24,840 |
| Compact0.3 data | 43,543 | 18,328 | 18,298 |

Tokenizer: optional tiktoken0.12.0. Commands: `python3 -m benchmarks.data_compression --encoding o200k_base` (or cl100k_base), after installing benchmarks requirements. Reports under benchmarks/results/data-*.json include exact input hashes, equal IR/revision/Wasm evidence and scope. Tokenizer encodings do not assign a particular model. Counts exclude tool framing, prompts, repairs and model outputs; no real agent-task trials were run.

The game atlas metadata alone changes from4899 to2839 bytes, with one shared table for16 tiles. Function source dominates the remaining size. Inline expression literals and runtime bulk resets remain pending: they need separate ID/semantics designs and equivalence tests. Existing traditional-language comparisons are frozen small programs and remain unchanged.

Reviewer note: deterministic greedy selection can miss jointly profitable map groups (one reviewed example733 vs724 bytes). This is a deferred efficiency optimization; decoded data remains exact and larger encoded sections fall back to plain.
