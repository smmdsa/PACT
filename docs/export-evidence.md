# Executable cases for public functions

Numeric module `pact.module/0.3.0` adds an opt-in structural evidence policy: every exported function must have at least one declared test targeting it. The operation set and runtime behavior stay the same as module 0.2. Module 0.4 inherits this policy and adds [checked conditions](checked-assertions.md). Legacy 0.1/0.2 modules keep their previous validation rules, including the ability to have no declared tests.

```sh
python -m pact check examples/counter.tested.pact
python -m pact build examples/counter.tested.pact -o build/counter.tested.wasm
python -m pact migrate examples/counter.tested-legacy.pact --to pact.module/0.3.0 -o build/migrated.pact
```

A missing export case rejects with `EXPORT_EVIDENCE_MISSING`. Its structured `add_export_tests` hint lists missing functions in sorted order; it does not fabricate expected values. The hint is guidance, not a supported pact.patch operation. Cases still obey existing validation: unique IDs, exported target, valid arguments, bounded set/expect arrays and a nonempty expected state or result. Helpers are exercised through callers and do not need direct public cases.

## Declaration versus execution

`check` and selective inspection establish that valid cases are declared for each export. Their `declared_export_tests` map lists test IDs and is not an execution receipt. `build` compiles real Wasm, executes all cases in the existing bounded Node test runner and rejects wrong expectations before writing artifacts. A successful 0.3 manifest has the same export map plus the existing per-case `tested` evidence. Legacy inspection/manifest shapes remain unchanged.

The example counter starts at 3, adds its declared amount 7 and expects 10. Changing the expected value to 999 still passes structural checking but fails the actual build with `TEST_FAILED`. This distinction is deliberate: neither a function name nor the existence of a case proves its intended outcome.

## Explicit migration

Ordinary reading and source-format conversion preserve the numeric version. API `migrate_module(document, target_format=...)` or CLI `migrate --to` permits 0.1→0.2, 0.1→0.3, 0.2→0.3, and forward migration from any earlier version to 0.4. Defaults remain 0.1→0.2 for compatibility. No-op and downgrade requests reject. Missing declared cases reject migration to 0.3; existing files remain untouched because validation happens before publication.

Successful migration changes only the format and semantic revision and compiles to identical Wasm. Regenerate revision-checked patches only after reviewing that deliberate version change. The separate 0.3 example does not replace frozen game/benchmark sources.

## What this policy cannot establish

A weak or unrelated state assertion can satisfy the structural rule. One case per export does not prove relevant assertions, branch/boundary coverage, single responsibility, truthful naming, absence of bugs or correctness for all inputs. Runtime tests are compiler-produced evidence, not authenticated proof. Nominal units, pre/postconditions, mutation testing and stronger evidence-quality measures remain planned.
