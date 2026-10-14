# Agent tooling baseline

User authorized the next roadmap work and parallel contributors, preserving agent-first explicit semantics. Build selective inspection plus a reproducible tokenizer baseline; do not change execution semantics.

## Inspection

Validated numeric modules expose inspect(document, function_id) returning versioned JSON with canonical semantic revision SHA256, selected function, direct/transitive callees, direct/transitive callers, referenced constants, read/write cells with type/count/mutability metadata, declared tests targeting selected function and each transitively affected caller. Do not emit full cell values or assets; declare this is context, not a buildable module. Preserve the function and stable IDs. Summary command lists functions and footprints for discovery. Output is deterministic and references are sorted. Text graph inspection is explicitly unsupported in this iteration. Missing function and invalid sources produce PactError diagnostics. CLI: `pact inspect SOURCE --function ID` and `pact symbols SOURCE`. Agent reads only tool output; the compiler still validates the whole bounded source. No promises that this proves responsibility or total semantic impact beyond call graph.

## Token baseline

Use an optional pinned tokenizer dependency only in benchmarks, never compiler runtime. Count exact compact and minified JSON inputs with named encoding/version; include hashes and bytes. Fail clearly if tokenizer/resources unavailable, no byte-based token estimates. Compare representations of equal validated IR. Document that counts exclude prompts/tool framing and do not demonstrate agent task success. A task protocol defines editable examples and independent executable acceptance criteria; no model results or fabricated retries.

## Publication

Add contribution guidance for independent agents, claims/verification policy and nonoverlapping task ownership. Update actual roadmap states, site docs and CI, then publish tested source to smmdsa/PACT and verify deployment. No external autonomous agent outreach or credentials embedded.
