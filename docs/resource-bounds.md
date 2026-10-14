# Resource bounds

PACT source files remain limited to 1 MiB of UTF-8 bytes. The compiler remains dependency-free; tokenization uses the existing optional benchmark dependency.

`benchmarks.token_counts.measure_pair` reads each source once, requesting at most `MAX_SOURCE_BYTES + 1` bytes. An oversized source rejects with the existing `SOURCE_LIMIT` diagnostic, `Source exceeds 1 MiB.`, before parsing that source or tokenizing either representation. Compact validation, byte counts, hashes and token counts use the same captured bytes. JSON parsing and validation use one captured snapshot; the counted JSON representation is the documented minification of that parsed document. A concurrent file change cannot cause validation of one read and counting of another read. This is a read snapshot, not an atomic snapshot across both files.

Compact operand parsing advances a cursor over the original string. JSON operands use `JSONDecoder.raw_decode(text, cursor)`, and bare operands copy only their own token. Whitespace retains Python's existing Unicode whitespace behavior. JSON strings retain embedded Unicode separators. Quoted references, colon identifiers, JSON boundaries, duplicate keys and separation diagnostics retain their previous grammar. On malformed JSON, a single remaining suffix is copied to preserve operand-relative error locations; parsing immediately rejects.

## Observed operand-list scaling

Measured on 2026-10-14 with Python 3.12.14 in the development Linux container. Each row is the median of five `_values` calls over a preconstructed single-line source. Lists contain repeated `node:0` or `"node:0"` operands. These exercise lexical parsing, not semantic graph validation. All sizes are below the source limit.

| Operands | Bare source bytes | Bare before, ms | Bare after, ms | Quoted source bytes | Quoted before, ms | Quoted after, ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4,000 | 27,999 | 3.802 | 3.064 | 35,999 | 6.456 | 1.453 |
| 8,000 | 55,999 | 9.508 | 6.182 | 71,999 | 25.891 | 2.948 |
| 16,000 | 111,999 | 29.328 | 12.817 | 143,999 | 87.858 | 5.860 |
| 32,000 | 223,999 | 100.106 | 24.552 | 287,999 | 327.454 | 11.786 |

An eightfold operand increase took 26.3×/50.7× as long before the change for bare/quoted operands, and 8.0×/8.1× afterward. These are diagnostic observations, not timing guarantees or a bound on all JSON decoder workloads. Unit tests assert bounded consumption, absence of long suffix copying on successful list parsing, snapshots and lexical behavior; they have no elapsed-time assertions.

Reproduce the post-change measurement:

```sh
python3 - <<'PY'
from pact.compact import _values
from statistics import median
from time import perf_counter
for token in ('node:0', '"node:0"'):
    for count in (4000, 8000, 16000, 32000):
        source = ' '.join([token] * count)
        samples = []
        for _ in range(5):
            start = perf_counter()
            _values(source)
            samples.append(perf_counter() - start)
        print(token, count, len(source), median(samples) * 1000)
PY
```

## Verification

`python3 -m unittest tests.test_resource_bounds tests.test_token_counts tests.test_compact -v` checks exact snapshots, CRLF and UTF-8 counts, oversized real-file consumption, malformed lexical boundaries, quoted references, Unicode separators and exact example IR/Wasm reconstruction. The resource tests first reproduced unbounded compact reads and successful-parser suffix copying before implementation. A diagnostic regression also reproduced the cursor implementation's changed JSON error offset before correction.

Both pinned token encodings were rerun against `benchmarks/results/{o200k_base,cl100k_base}.json`. The two example result arrays matched exactly, including all source byte counts, token counts and SHA256 hashes. No example or frozen token report changed.

`python3 -m unittest discover` passed all 138 tests at this task checkpoint. Combined integration checks and a final full-suite run remain the integration owner's acceptance gate.
