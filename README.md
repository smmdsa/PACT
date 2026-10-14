# PACT

Experimental agent-first programming: explicit dataflow, checked effects, stable node IDs and deterministic WebAssembly compilation.

Compact frontend **0.2** translates to text graph **0.0.1** or numeric module **0.1.0**. JSON remains an interchange format. Source representation token counts are measured; agent productivity and total task efficiency remain untested.

[Documentation and game](https://smmdsa.github.io/PACT/) · [Syntax](docs/syntax.md) · [Security](docs/security.md) · [Roadmap](ROADMAP.md)

## Hello from an alien language

See [the complete compact source](examples/hello.pact).

```sh
python3 -m pact check examples/hello.pact
python3 -m pact build examples/hello.pact -o build/hello.wasm
node host/run.mjs build/hello.wasm --allow stdout
```

Output: `hola mundo, from an alien language` followed by a newline.

Requires Python 3.10+ and Node 20+, without third-party packages. On Windows use `python` if appropriate. Compilation is verified on Linux; native Windows/macOS CI is planned. Generated HTML uses browser WebAssembly without a server or runtime installation.

## Alien Harvest

An original retro platformer: jumping, ladders, enemies, throwable vegetables, checkpoint, lives, crystals and a boss. Gameplay uses 14 PACT functions and 1,218 nodes. Sixteen 8×8 tiles and a named palette compile into an internal RGBA atlas.

```sh
python3 -m pact build examples/alien-harvest.pact -o build/alien-harvest.wasm --html build/Alien-Harvest-PACT.html
```

Open the resulting HTML. Arrows/WASD move or climb; Space jumps; X/J picks up or throws; Enter starts; P pauses. Touch buttons are included. Collect three crystals, defeat the guardian and reach the door.

JavaScript handles input/rendering/audio/tick scheduling; gameplay is in PACT. `tools/make_game.py` is an optional authoring tool, not executed by the compiler or game. Regenerating overwrites JSON edits; convert again explicitly.

## Reversible conversion

```sh
python3 -m pact convert examples/alien-harvest.pact.json -o examples/alien-harvest.pact --to compact
python3 -m pact convert examples/alien-harvest.pact -o build/alien-harvest.json --to json
```

Both formats pass the same validator. Tests check exact IR reconstruction and byte-identical Wasm. Game: **51,244 bytes** of compact source versus **88,379 bytes** of minified JSON, **42.0% fewer bytes**. These are not token counts; see [benchmarks](benchmarks/README.md).

## Selective agent context

```sh
python3 -m pact symbols examples/alien-harvest.pact
python3 -m pact inspect examples/alien-harvest.pact --function player.move
```

Responses are deterministic JSON with a source revision, selected body, helper signatures, call relationships, referenced constants, cell metadata and test summaries. Initial cell arrays, assets, helper bodies and test-case bodies are omitted explicitly. Inspect helpers separately when their behavior matters. Call relationships are not a complete dependency analysis through shared state. See [inspection](docs/inspection.md) and [agent contributions](docs/agent-contributions.md).

Optional real-token measurements use `benchmarks/requirements.txt` and `python3 -m benchmarks.token_counts`. They measure source representations with named encodings, not model productivity. The independent compiler remains dependency-free. With `o200k_base`, the game uses 24,851 compact-source tokens versus 35,903 minified-JSON tokens (30.8% fewer). The `player.move` inspection returns 6,229 tokens, with omissions stated explicitly; additional reads may be needed. See frozen reports in `benchmarks/results/`.

## Revision-checked edits

```sh
python3 -m pact patch examples/alien-harvest.pact --patch examples/patches/jump.patch.json --dry-run
python3 -m pact patch examples/alien-harvest.pact --patch examples/patches/jump.patch.json -o build/higher-jump.pact
```

This example updates jump strength and the grounded-jump test together. Stale revisions, invalid candidates and failed executable tests reject the update. Publication creates a new candidate atomically and never overwrites the source or existing files. This is not an in-place filesystem compare-and-swap. The patch is tied to the checked-in source revision; regenerate its expected revision only after reviewing source changes. See [transactions](docs/transactions.md).

## Traditional-language comparison

Two frozen executable kernels were verified in PACT, Python, JavaScript and C. With `o200k_base`:

| Source | PACT | Python | JavaScript | C |
| --- | ---: | ---: | ---: | ---: |
| Greeting | 78 | 10 | 11 | 27 |
| Bounded wrapping counter | 163 | 74 | 76 | 138 |

PACT uses more source tokens in all these small comparisons. It includes policy declarations and tests that the other versions do not implement; behavioral equality on the frozen traces is not security equivalence. Drivers are counted separately in the reports. This does not measure agent task efficiency or the complete game. See [methodology and all results](docs/traditional-comparison.md).

## Verification and site

```sh
python3 -m unittest discover -v
python3 -m tools.build_site
node tools/playthrough.mjs site-output/game.wasm site-output/game.manifest.json build/playthrough.json
```

The automated player wins using inputs without modifying gameplay state. Tests compare the reference VM with actual Wasm. Browser layout, mobile behavior and audible audio need real-browser QA; native Canvas checks do not replace it.

The Pages workflow tests, compiles and runs the playthrough before publishing. Enable **Settings → Pages → Source → GitHub Actions**. The public site is live; deployment status is verified in GitHub Actions.

| Path | Purpose |
| --- | --- |
| `pact/` | Compiler, validators, frontend, reference VM |
| `examples/` | Compact sources and equivalent JSON |
| `host/`, `web/` | Capability host and browser presentation |
| `tests/` | Safety, execution, conversion, gameplay regressions |
| `docs/` | Specification, security and verification history |
| `benchmarks/` | Byte measurements and future token protocol |
| `tools/` | Authoring, input-only player and site builder |

No full SDK, package manager, debugger or nominal units yet. A `stdlib/` will be added when actual standard modules exist.

## License

The owner has not selected an open-source license. Public availability alone does not grant unrestricted redistribution rights. Choosing a license is an owner decision.
