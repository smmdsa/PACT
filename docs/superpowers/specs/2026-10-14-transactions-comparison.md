# Transactions and traditional-language comparison

User authorized next roadmap stages, explicit traditional-language token comparisons and parallel tasks with traceable goals. Preserve source/IR execution versions and the dependency-free compiler.

## Transaction core

Pure API apply_patch(document, patch)->candidate validates numeric module, checks the existing inspection canonical revision and applies a bounded closed-schema patch to a deep copy. Patch format pact.patch/0.1.0 with expected_revision_sha256 and operations (1..256). Operations: replace_node(function,id,node), set_constant(name,value), replace_test(id,test). Reject missing targets, changed stable IDs, duplicates targeting the same item, unknown fields/operations and stale revisions. Validate full candidate before returning; original remains unchanged on every failure. Public revision helper shares exact existing canonicalization with inspection.

CLI `pact patch SOURCE --patch PATCH [--dry-run] [-o NEW_FILE] [--to compact|json]` executes candidate declared Wasm tests before output. Dry-run emits reviewable revision/change/evidence summary and creates no files. Normal output requires a NEW distinct path; existing files and source path cannot be overwritten. Publish through a same-directory staged file and atomic no-clobber link, cleanup on failure. Explicitly not an in-place cross-process compare-and-swap. Source is read as a snapshot; its revision is carried in the receipt. Git publication retains expected-head guard. Source/patch size limits and duplicate key checks apply. No additional guest authority, eval or hidden semantics.

## Comparison

Compare greeting and bounded i32 wrapping-counter kernels in PACT/Python/JavaScript/C where compiler available. Freeze source files and expected observable traces, run each implementation, count exact sources with both pinned encodings and SHA256. Separate source-language/driver/validation-policy overhead; behavioral equivalence does not mean equivalent capabilities or security contracts. Do not translate the entire game just to create an oversized comparison. Publish all results including cases where PACT costs more tokens. No model-task productivity claims. Independently verify traces against frozen expected values, not only against PACT.

## Resource hardening

Replace repeated remainder slicing in compact operand parsing with cursor-based scanning, preserving grammar/diagnostics. Benchmark reads only source-limit+1 bytes before rejection. Measure pathological list scaling without brittle timing assertions; regression-test bounds and lexical cases.

## Acceptance

Every task has failing tests before implementation, isolated file ownership and executed acceptance evidence. Root integrates CLI/CI/site/docs and a fresh independent reviewer checks the combined diff. Full suite, examples, input-only playthrough, tokenizer reports and external-language execution run before publication. Roadmap records concrete done/partial states, not promises.
