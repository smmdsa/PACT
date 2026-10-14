# PACT bootstrap 0.0.1

Scope authorized by the user: general basic structure and an executable alien-language hello world. This is an initial hypothesis for agent usability, not a claim about model internals. The platform game and numeric types remain subsequent work.

Source is a closed JSON graph with stable IDs; no conventional textual parser. Root keys are `format`, `responsibility`, `entry`, `effects`, `nodes`, `contracts`. Format is `pact.graph/0.0.1`. Node operations are `utf8.literal`, `utf8.concat`, `stdout.emit`, `effect.sequence`. Literals carry `value`; all other nodes carry `args`. Literal/concat return Utf8; emit/sequence return Unit. Concatenation and sequence need at least one argument. Entry returns Unit. Pure nodes may be shared; effectful nodes may be executed only once. No unreachable nodes, cycles, unknown fields, duplicate IDs/JSON keys, invalid UTF-8, unresolved references or undeclared/unused effects.

Each contract is `{id, op: stdout.exact, value}`. At least one contract is required. All contracts must match the computed output. Contract IDs are unique. This is exact evaluation of a static, input-free program, not a general proof system or the proposed user-test policy.

Limits: source 1 MiB; 256 nodes; 64 arguments per node; any individual or concatenated text and cumulative output 16,384 UTF-8 bytes. IDs/responsibility are ASCII identifiers of 1–64 characters, beginning with a letter; remaining characters are letters, digits, `_ . : -`.

`analyze(document)` returns a deterministic plan with format `pact.plan/0.0.1`, responsibility, required capabilities, source SHA-256 of canonical JSON, ordered emissions, inferred node types sorted by ID, and contract evidence labeled `evaluated`. Node declaration order has no execution significance. Arguments specify evaluation/emission order. JSON numeric values are not part of this kernel.

`compile_plan(plan)` emits a WebAssembly module, importing only `pact.emit_utf8(i32,i32)`, exporting `memory` (exactly one 64-KiB page, fixed maximum) and `main()`. Text is stored in active data segments; `main` consists only of constant pointer/length pairs and calls. The output includes a manifest with plan and module SHA-256. No start section, loops, allocation, network or filesystem guest imports.

The Node host independently constructs the permitted bytecode from manifest emissions and requires exact byte equality before instantiating. This is a narrow static-output profile checker, not a general Wasm sandbox. The manifest hash detects mismatches, not authorship. The host requires an explicit stdout capability before executing. It validates the entire manifest, byte counts, contract evidence and hashes; no output is emitted before these checks pass. Output limits, memory bounds and UTF-8 decoding are enforced during host calls. A caller chooses the artifact paths; the guest cannot read arbitrary files.

CLI commands: `python3 -m pact check SOURCE`, `python3 -m pact interpret SOURCE --allow stdout`, `python3 -m pact build SOURCE -o OUTPUT`. Build creates `.wasm` and sibling `.manifest.json`. Machine-readable diagnostic objects go to stderr on failure. Default host output budget is 16,384 bytes and can be reduced using `--max-output N`. Source/manifest/wasm bounds are checked before reading complete inputs.

Python 3.10+ and Node 20+; no downloaded dependencies. Only Linux/Python 3.12/Node 24 are exercised in this environment. Windows/macOS portability is a design expectation, not validated support. Browser host is deferred.

Acceptance: exact hello output, interpreter/backend parity, deterministic bytecode for shuffled node declarations, Unicode/empty/large text behavior, rejection of structural errors, effect escalation and shared effects, contract mismatch, unknown capability, incorrect or malicious bytecode, tampered manifest, budget overrun. Tests exercise real Python code and Node WebAssembly.
