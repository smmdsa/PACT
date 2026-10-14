# Compact frontend verification — 2026-10-14

- 82 unittest cases passed on Linux, Python 3.12, Node 24.
- Complete greeting and game roundtrips preserve parsed documents exactly.
- Both produce byte-identical Wasm compared to JSON.
- CLI conversion, greeting execution, malformed boundaries, duplicate keys/IDs and quoted literal handling are covered.
- Fresh independent review found colon-containing valid IDs and Unicode separators could break roundtrips. Regressions failed before the fixes and passed afterward. Parser now uses the existing identifier grammar and splits physical LF only.
- Site build compiled 28,940-byte game Wasm and executed its declared tests.
- First remote CI run exposed a missing greeting manifest in the site builder. The builder now uses the normal CLI to produce both Wasm and its required validation manifest. A real host integration regression failed before this correction and passed afterward.
- Input-only playthrough won at tick 1,216 with three gems, guardian health zero, checkpoint active and two lives.
- Compact UTF-8 sizes: greeting 314 vs minified JSON 422 bytes; platformer 51,244 vs 88,379 bytes. No tokenizer measurements or productivity experiment yet.

Deferred minor: operand parsing repeatedly slices the remaining line, giving quadratic work for pathological long lists. Overall source is limited to 1 MiB and semantic argument bounds reject oversized lists; a cursor or earlier bounds would improve parser hardening.

No real-browser visual/compatibility QA in this iteration. No independently verified support for arbitrary third-party numeric Wasm. Pages workflow preparation is separate from repository activation and a successful remote deployment.

Update: the parser slicing and bounded benchmark-read resource findings were resolved in the transactions/comparison stage; see docs/resource-bounds.md. Earlier verification entries describe their historical state.
