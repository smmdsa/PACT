# Compact source 0.2

A reversible frontend over the existing checked IR. UTF-8, `.pact`, at most 1 MiB. JSON metadata remains for structured assets and contracts.

```text
pact 0.2
SECTION JSON_VALUE
NODE_ID = OP OPERANDS
fn FUNCTION_ID
params JSON_ARRAY
locals JSON_ARRAY
result JSON_STRING
writes JSON_ARRAY
NODE_ID = OP OPERANDS
return ENTRY_NODE_ID
end
```

Top-level nodes belong to a text graph; functions belong to a numeric module. Explicit `format` selects `pact.graph/0.0.1`, `pact.module/0.1.0` or `pact.module/0.2.0` / `pact.module/0.3.0` / `pact.module/0.4.0` / `pact.module/0.5.0` / `pact.module/0.6.0` (loading preserves the declared module version; `state.reset` requires a supported numeric format from 0.2.0 onward). All original closed-schema sections remain. Every section occupies one physical line. JSON strings encode newlines as escapes. Blank lines and indentation are insignificant.

Whole-line `#` comments are optional and discarded by conversion. Inline comments are unsupported; `#` in quoted text is ordinary text. Rationale belongs in documentation until versioned metadata is designed.

Operands are separated by spaces. Identifiers may be bare or quoted. String literals must be quoted. `refs...` means ordered node IDs without brackets or commas; `[]` represents an empty reference list. There are no implicit indices, constants or scope expansion.

| Operation | Operands |
| --- | --- |
| `utf8.literal`, `i32.const` | value |
| `const.load`, `local.get` | name |
| `local.set` | name refs... |
| `get` / `state.load` | cell refs... |
| `set` / `state.store` | cell refs... |
| `flow.repeat` | literal-count counter-local refs... |
| `call` | target-function refs... |
| Other supported operations | refs... |

Aliases: `add.wrap`, `sub.wrap`, `mul.wrap`, `seq`, `if` expand to their corresponding `i32.*_wrap`, `flow.sequence`, `flow.if` operations. `get`/`set` always address state; locals require `local.get`/`local.set`.

This function excerpt requires its enclosing module to declare the cells:

```text
fn move.horizontal
params []
locals []
result "unit"
writes ["player.x"]
zero = i32.const 0
n0 = get player.x zero
n1 = get player.vx zero
n2 = add.wrap n0 n1
n3 = set player.x zero n2
return n3
end
```

Node order is not execution order. References and the entry node define execution. Numeric nodes evaluate at use; shared state loads do not freeze earlier values. Unit effects need explicit execution edges. `return` selects the entry expression/action, not an imperative early exit.

Duplicate keys/IDs, invalid operations, bad operands and malformed boundaries are rejected. Translation runs the existing type/effect/cycle/budget validator. Conversion preserves IDs, operand ordering and all semantic fields, but not formatting/comments.

Implicit scopes remain planned. Inline literals and checked runtime bulk resets are specified in [inline literals and resets](inline-literals-and-resets.md); the `state.reset` semantics ship as `pact.module/0.2.0` with an explicit 0.1.0 migration. Inline literal syntax supports all supported numeric module versions and preserves IR identity. RLE maps are covered by [data compression](data-compression.md), and revision-checked patches by [transactions](transactions.md). Source headers select representations; declared numeric formats select supported execution semantics.

## Optional data frontend0.3

The `pact 0.3` header adds bounded `cells.packed` and `assets.shared` sections; all normal operations and IDs remain. See [data compression](data-compression.md). Default canonical output remains 0.2. Scopes remain a separate pending proposal.

## Literal syntax 0.4

The `pact 0.4` header supports two reversible forms:

- [Stable-ID literal definitions](literals.md), such as `zero = 0` and `greeting = "hola mundo"`, lower to `i32.const` and `utf8.literal`. Use `--to compact-agent`.
- [Explicit-ID inline argument literals](inline-literals-and-resets.md), such as `n0002 = set input.left n0000=0 n0001=0`, reconstruct ordinary `i32.const` nodes immediately before their consumer. Use `--to compact-inline`.

Both forms preserve IR, semantic revisions, compiled bytes and the declared module version. Numeric literals support all supported numeric module versions; text graphs accept string literal definitions under their existing type rules. Checked runtime `state.reset` is an operation in `pact.module/0.2.0`, and requires explicit migration from 0.1.0 rather than a source-header change.

[Evaluation protocol](agent-evaluation.md) · [Runtime measurements](runtime-performance.md) · [Progress](../CHANGELOG.md).

## Optional public-function evidence

Numeric module 0.3 retains 0.2 operations and requires at least one declared case per export. Source headers remain independent; migrate explicitly with `--to pact.module/0.3.0`. Check verifies declarations, while build executes the cases. See [export evidence and limits](export-evidence.md).

## Explicit checked flow

Module 0.4 adds `assert predicate` (unit) and `guard predicate body` (body type), with zero/nonzero i32 truth. They are regular version-gated nodes under existing source headers. Execution ordering is explicit; no automatic rollback. See [checked conditions](checked-assertions.md).

## Expected-trap declarations

Module 0.5 inherits 0.4 operations and adds optional closed `trap` metadata to test cases: code/function/node, with no result field and optional post-trap state assertions. Builds require matching reference and exact Wasm failures. Source headers do not select this behavior. See [expected traps](expected-traps.md).

## Nominal unit contracts

Module 0.6 inherits 0.5 cases and accepts optional closed top-level `units` metadata with declared names and cell/constant/function bindings. Static inference checks nominal units while runtime values remain i32. The section is preserved under all supported source headers; older numeric schemas reject it. See [nominal units](nominal-units.md).
