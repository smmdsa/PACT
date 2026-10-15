# Security and guarantees

Compact source reconstructs the same closed-schema IR as JSON and passes the same semantic validation. The PACT toolchain does not evaluate host-language source as a PACT program. The separate benchmark Python adapter intentionally executes Python only inside its configured Docker container and has no host-execution fallback; see [isolated adapters](agent-sandbox.md).

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

Module 0.4 adds explicit guard/assert runtime conditions. A false guard traps before its body; traps do not roll back earlier writes. Legacy build hosts retain generic traps; replay can attribute selected trap sites when an actual Node frame exactly matches the hash-bound compiler map. Missing/unmatched frames stay generic. See [checked conditions](checked-assertions.md) and [replay](replay.md).

These constraints do not prove naming, single responsibility, universal correctness or intent. The numeric host consumes compiler-produced artifacts and is not an independent verifier of arbitrary third-party Wasm. The embedding host can modify exported memory.

## Text graph

Stdout requires an explicit source effect and a host `--allow stdout` grant. A narrower independent Wasm profile checker and exact-output contract are provided for this profile.

## Trust

Hashes identify content, not authors. Tests cover cases, not all possible inputs. Altered bytecode, compiler and host are outside the guarantees. Future filesystem/network/process capabilities must have scoped declarations and explicit host grants, with denial tests. Signed packages and in-place filesystem compare-and-swap are planned, not implemented. Revision-checked candidate construction and no-clobber CLI publication are implemented; see transactions.md.

## Negative-case acceptance

Module 0.5 expected-trap cases require the reference diagnostic and exact hash-bound Wasm site to match the declared code/function/node. Both engines check post-trap state; earlier writes persist. A missing engine position or a different failure rejects. The reference suite shares a 1,000,000-node budget and Node retains its 15-second deadline. These are finite compiler-produced observations, not authenticated or independent proof. [Schema and evidence](expected-traps.md).

## Static nominal contracts

Module 0.6 checks nominal units on arithmetic, state/local stores, calls/results and flow boundaries before execution. Indices, predicates and repeat counters are dimensionless. Unit metadata and source revisions bind the declarations; compiled Wasm still uses untagged i32 values. Host calls and test inputs acquire the declared signature’s units, so an embedding host can violate physical meaning without runtime detection. This is static type acceptance, not unit authentication, derived-unit algebra, coverage or proof. [Rules and limits](nominal-units.md).
