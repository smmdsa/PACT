# Stable-ID literal definitions — source0.4

```text
zero = 0
jump = -1536
greeting = "hola mundo"
```

Under the pact0.4 header these definitions lower to existing i32.const or utf8.literal nodes. They keep explicit IDs and introduce no hidden argument nodes, numeric conversions or execution semantics. A literal is exactly a signed-i32 integer or a JSON string; floats, booleans, null, objects and arrays reject. A numeric module still rejects string nodes, and a text graph still rejects numeric nodes through normal type validation.

```sh
python3 -m pact convert examples/alien-harvest.pact --to compact-agent -o build/game.agent.pact
python3 -m pact patch examples/alien-harvest.agent.pact --patch examples/patches/jump.patch.json --dry-run
```

`dumps(document, literals=True)` emits0.4; compressed=True combines0.3 packed data with the shorter literal definitions. CLI compact-agent enables both. compact-data remains0.3; default compact remains0.2. Earlier headers reject bare literal definitions. Exact IR, revision, IDs and compiled bytes remain the same. Strings use normal JSON escaping; Unicode separators inside quoted strings are not source line breaks.

PACT 0.4 also supports [explicit-ID inline arguments and module 0.2 bulk resets](inline-literals-and-resets.md), contributed by Gemini. These two literal spellings coexist without changing existing IDs or module revisions.

| Game source | Bytes | o200k_base tokens |
| --- | ---: | ---: |
| Compact0.2 | 51,244 | 24,851 |
| Data0.3 | 43,543 | 18,328 |
| Literals + data0.4 | 38,273 | 16,747 |

Run `python3 -m benchmarks.data_compression --include-literals --encoding o200k_base` with optional benchmark dependencies; both encoding reports and hashes are [published](../benchmarks/results/literals-o200k_base.json). This measures identical source representations, not agent task success.
