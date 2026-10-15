# Nominal unit contracts

Opt-in numeric module `pact.module/0.6.0` strengthens signatures and state contracts with static units. A counter measured in `pixel` cannot add an amount measured in `tick`. The compiler rejects the mismatch before tests or publication. Values still execute as ordinary i32 numbers with unchanged wrapping, effects and trap behavior.

```sh
python3 -m pact check examples/counter.units.pact
python3 -m pact inspect examples/counter.units.pact --function step
python3 -m pact build examples/counter.units.pact -o build/counter.units.wasm
python3 -m pact migrate examples/counter.traps.pact --to pact.module/0.6.0 -o build/migrated.units.pact
```

The [authored example](../examples/counter.units.pact) labels both its counter and increment as pixels. It executes a success and an expected post-write assertion failure on reference and actual Wasm. Its predicate and array index remain dimensionless. Changing the increment's annotation to `tick` rejects at the qualified addition node with `UNIT_MISMATCH`.

## Explicit declarations

The optional top-level `units` section has exactly four fields:

```json
{"names":["pixel","tick"],"cells":{"counter":"pixel"},"constants":{"amount":"pixel"},"functions":{}}
```

Names are nominal: `pixel` and `centimeter` are distinct even if an author knows a conversion. Up to 128 unique identifier names are allowed; `i32` and `unit` are reserved. Missing numeric annotations mean dimensionless `i32`. Missing `units` means all numeric values are dimensionless. `unit` retains its existing effect-only meaning.

For a function with i32 parameters `x`/`y` and an i32 result, a complete annotation record is:

```json
{"params":{"x":"pixel","y":"pixel"},"locals":{},"literals":{},"result":"pixel"}
```

Place it under `units.functions.FUNCTION_ID`. Slots and literal nodes must exist. `literals` may annotate only `i32.const` nodes; it cannot relabel an arbitrary expression. Effect-only functions require `result:"unit"`. All declaration records are closed; unknown names, bindings and wrong result kinds reject.

## Operations and boundaries

| Operation | Unit rule |
| --- | --- |
| Add, subtract, remainder | Both operands identical; preserve that unit |
| Compare | Both operands identical; produce dimensionless i32 |
| Multiply | At least one operand dimensionless; preserve the other unit |
| Divide | Divide by a dimensionless scalar to preserve the numerator's unit, or divide identical units to obtain a dimensionless ratio |
| Bitwise and/or | Dimensionless operands only |
| Zero check | Any numeric unit; dimensionless result |
| State/local stores | Stored value must match the declared binding; array indices dimensionless |
| Calls and returns | Arguments/results must match the callee and enclosing signatures |
| Branches and conditions | Branch units match; predicates and repeat counters dimensionless |

Reset retains typed initial values. Earlier writes and lazy guard behavior follow the existing runtime rules. Products of two unitful values, inverse/derived units and automatic scaling are unsupported and reject. Runtime pre/postconditions still use explicit guard/assert nodes and [expected-trap cases](expected-traps.md).

## Evidence, migration and limits

`check`, plans and build manifests expose `pact.unit-contracts/0.1.0` metadata. Inspection returns relevant cells, constants, selected literal annotations and dependency signatures; helper literal maps stay explicitly omitted. The unit-name list is filtered to these visible bindings, including in symbols output. Symbols returns unit signatures without literal maps. Legacy output shapes remain unchanged.

Compact/JSON conversion preserves annotations, qualified IDs and numeric version. Explicit forward migration to 0.6 changes only format/revision, adds no annotations and preserves compiled bytes. Default migration stays 0.2. Earlier schemas reject `units`; module 0.6 inherits all 0.5 dual-engine case and expected-trap requirements. Source headers remain independent.

Unit annotations affect static acceptance and source identity, not runtime bytes. Initial numbers, zero-initialized locals, host arguments and test numbers acquire their declared binding/signature's unit. The host still supplies untagged i32 values and must honor the ABI; these contracts do not authenticate physical quantities. They do not prove author intent, physical equations, coverage, refinement types or compiler correctness. See the [versioned specification](superpowers/specs/2026-10-15-nominal-units.md).
