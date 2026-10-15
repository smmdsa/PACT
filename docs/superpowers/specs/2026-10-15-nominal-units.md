# Nominal unit contracts — module 0.6

L2 strengthens the existing numeric contracts with static nominal units across state, constants, locals, function arguments/results and expressions. The outcome is rejection of incompatible units before execution. Runtime i32 representation, overflow, effects, checked conditions and traps remain unchanged. This does not prove physical meaning or author intent.

## Version and declarations

Opt-in `pact.module/0.6.0` inherits all module 0.5 operations, declared-case rules and dual-engine expected-trap tests. Optional top-level `units` has exactly `names`, `cells`, `constants`, `functions`. Absence means all numeric values are dimensionless. Earlier schemas reject the section. Source headers remain 0.2/0.3/0.4; ordinary conversion preserves metadata and version. Default migration remains 0.2; explicit forward migration to 0.6 changes only format/revision and preserves runtime bytes without inventing annotations.

`names` is a unique list of at most 128 ordinary identifiers, excluding reserved `i32` and `unit`. Units are nominal: two distinct names are incompatible even if an author considers them physically equivalent. `i32` means dimensionless; `unit` retains its existing effect-only meaning.

`cells` and `constants` map existing IDs to a declared name or `i32`. Unspecified numeric bindings default to `i32`. `functions` maps existing function IDs to closed records with exactly `params`, `locals`, `literals`, `result`. The first two map existing slot names to numeric units; `literals` maps existing i32.const node IDs to numeric units. It cannot relabel an arbitrary expression. `result` must be a numeric unit for an i32 function or `unit` for an effect-only function. Unspecified function records default to dimensionless numeric signatures and no literal annotations. Unknown IDs/names, wrong kinds, invalid records and extra keys reject before inference. Existing module/source bounds apply; annotation maps cannot introduce more bindings than existing declarations.

Example metadata:

```json
{"names":["pixel","tick"],"cells":{"counter":"pixel"},"constants":{"amount":"pixel"},"functions":{"sum":{"params":{"x":"pixel","y":"pixel"},"locals":{},"literals":{},"result":"pixel"}}}
```

Initial cell integers, zero-initialized locals, constant values, public host arguments and declared test numbers acquire the unit of their declared binding/signature; there is no runtime boxing. The embedding host must honor that contract. Literal annotations explicitly assign a unit to that literal's integer value. There is no implicit unit conversion or arbitrary-expression cast.

## Inference rules

| Operations | Required operands | Result |
| --- | --- | --- |
| const/local/state load | Binding's unit; state index dimensionless | Binding's unit |
| local/state store | Value matches binding; state index dimensionless | unit |
| add/sub/rem | Both identical numeric units | Same unit |
| mul | At least one operand dimensionless | Other operand's unit |
| div | Denominator dimensionless, or both units identical | Numerator's unit, or dimensionless ratio respectively |
| eq/ne/lt/gt/le/ge | Both identical numeric units | Dimensionless |
| and/or | Both dimensionless | Dimensionless |
| eqz | Any numeric unit | Dimensionless |
| if | Dimensionless predicate; identical branch units | Branch unit |
| guard | Dimensionless predicate | Body unit |
| assert | Dimensionless predicate | unit |
| sequence/repeat | Existing unit actions; repeat counter dimensionless | unit |
| call | Each argument matches target signature | Target result unit |
| reset | Existing mutable cells and unchanged initial values | unit |

The entry expression must match the declared function result unit. Existing scalar type/effect/arity/cycle/depth/budget checks still run first. Products of two unitful values, inverse units, derived dimensions and automatic scaling are unsupported; users can construct explicit helpers with supported signatures, but cannot erase units through a cast. Shared numeric nodes remain evaluation-at-use, not snapshots. Static unit errors use UNIT_MISMATCH with qualified function/node; declaration errors use schema/identifier or UNIT_INVALID diagnostics.

## Observable contracts and scope

Module 0.6 plans/manifests add `unit_contracts` in `pact.unit-contracts/0.1.0`: sorted names plus expanded cell/constant units and per-function params/locals/result with explicit literal bindings. Source revisions include annotations; compiled bytes do not. Selective inspection includes units relevant to selected/dependency signatures, referenced constants/cells and selected literals, while helper literal annotations stay explicitly omitted. Symbols exposes signatures, not literal annotation maps. Legacy output shapes stay unchanged.

Tests/build/replay use the same checked document, so incompatible modules reject before execution/publication. Numeric tests and Wasm host calls carry bare i32 values according to the declared ABI, not independently tagged quantities. Runtime pre/postconditions still use existing guard/assert nodes and expected-trap cases. This closes static nominal-unit/signature contracts for L2; dependent/refinement types, derived-unit algebra, automatic contract inference, host-unit authentication and coverage proofs remain outside scope.

## Verification

Positive and negative tests must cover every inference family, call/helper boundaries, branch/result mismatches, unitful indices/predicates/counters, malformed metadata, explicit typed literals, reset/state retention, shared IDs, legacy rejection, forward migration/binary identity, all source representations, selective metadata and CLI atomic patch rejection. Execute authored reference/Wasm examples and the full suite; require independent review and OS/browser/Docker CI before merging.
