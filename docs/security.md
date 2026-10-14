# Security and guarantees

Compact source reconstructs the same closed-schema IR as JSON and passes the same semantic validation. Host-language source is never evaluated.

## Numeric module

- Explicit i32/unit types and exact transitive write declarations.
- Fixed arrays, checked indices, immutable state protection.
- No recursion, guest imports, eval, reflection or memory growth.
- Fixed 128 KiB Wasm memory; state at most 64 KiB, atlas within total memory.
- At most 128 functions, 2,048 nodes per function, combined evaluation depth 128.
- Literal repeats 0–256; aggregate conservative expansion budget 500,000.
- Explicit wrapping arithmetic and Wasm signed division/remainder traps.
- Declared tests execute against actual Wasm before publishing build outputs.

Module 0.3 optionally requires a declared executable case for every export; builds run the cases. This is structural presence plus case execution, not proof of relevant assertions or adequate coverage. See [export evidence](export-evidence.md).

These constraints do not prove naming, single responsibility, universal correctness or intent. The numeric host consumes compiler-produced artifacts and is not an independent verifier of arbitrary third-party Wasm. The embedding host can modify exported memory.

## Text graph

Stdout requires an explicit source effect and a host `--allow stdout` grant. A narrower independent Wasm profile checker and exact-output contract are provided for this profile.

## Trust

Hashes identify content, not authors. Tests cover cases, not all possible inputs. Altered bytecode, compiler and host are outside the guarantees. Future filesystem/network/process capabilities must have scoped declarations and explicit host grants, with denial tests. Signed packages, nominal units and in-place filesystem compare-and-swap are planned, not implemented. Revision-checked candidate construction and no-clobber CLI publication are implemented; see transactions.md.
