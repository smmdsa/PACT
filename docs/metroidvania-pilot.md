# Two GPTs, one Metroidvania brief

[Play both original games](../benchmarks/metroidvania_pilot/index.html) · [Shared generation prompt](../benchmarks/metroidvania_pilot/prompt.txt)

This exploratory test requests a complete miniature Metroidvania from two GPT model aliases: `gpt-6.1-sol` and `gpt-6-astra`, both at medium reasoning effort. Each gets a fresh session, the same task text, one generation and no repair round. Both write a single self-contained HTML/JavaScript artifact. This compares game generation in the same language; it does not compare PACT with JavaScript or measure total agent cost.

The contract was written before generation: five connected rooms, ordinary jump, boots that unlock a second air jump and an east passage, a key in a lower room, a pit, enemies, a checkpoint, backtracking, a boss and a final exit. Keyboard controls and a deterministic test API must share the same simulation. Canvas dimensions, physics, room links, item positions and boss conditions are fixed so a verifier can attempt the same route in both games. Visual presentation remains the models' choice.

| Area | Finite verification |
| --- | --- |
| Startup and controls | Required state shape, deterministic reset/input trace, real keyboard movement, movement speed and jump |
| Ability progression | Second air jump and east passage reject before boots, then unlock after west pickup |
| Combat and health | Contact damage with an invulnerability window; attacks reduce boss health |
| Exploration | Vertical exit, pit crossing, key pickup and return through earlier rooms using inputs only |
| Final gate | Sanctum rejects before key; victory requires boss defeat and reaching the final exit |
| Lifecycle | Death respawns at the hub with retained boots/visited rooms; full restart clears progression |

The independent verifier was implemented by a third session that read the contract and did not inspect either game. The coordinator reviewed the harness, added contact-damage and stronger respawn observations, and preserved the candidate files without edits. These checks are not exhaustive: the game controls its test API and can forge observations, and finite successful traces do not establish all gameplay or visual-quality requirements. Screenshots are retained for review; they are not an automatic art-quality score.

## Execution and evidence

Generated HTML runs only in a dedicated Chromium Docker worker during automated evaluation. No local trusted game/performance driver executes it. The image builds Playwright from the existing exact lockfile and installs Debian Chromium; its actual runtime versions and immutable image ID are recorded. The image's mutable base/package sources do not provide reproducible rebuilds.

Execution requests network `none`, read-only root, UID/GID 65534, all capabilities dropped, no-new-privileges, no host mounts, 768 MiB RAM without extra swap, one CPU, 128 processes, CPU/file/descriptor limits and a 64 MiB noexec temporary filesystem. Selected effective settings are inspected. The host captures at most 1 MiB combined stdout/stderr, imposes a 60-second wall limit, and forcibly removes the container. Missing Docker, mutable image IDs or weakened inspected configuration reject without a host fallback. Chromium uses `--no-sandbox` inside this outer container; this is an explicit additional limitation, not independent browser-sandbox evidence or a VM-level containment claim.

The worker blocks non-file requests, service workers and popups, records bounded page errors, and returns individual checks plus at most two screenshots. Candidate bytes, image ID and logs remain bound by hashes. Infrastructure failures and failed observations remain visible. There is no full `candidate_pass` approval. The dedicated workflow retains per-model receipts, raw logs, screenshots and a summary artifact. An unfavorable game result is data; it does not fail CI merely because the model missed a requirement.

```sh
docker build -f benchmarks/metroidvania_pilot/Dockerfile -t pact-metroid-verifier .
docker image inspect --format '{{.Id}}' pact-metroid-verifier
python3 -m tools.check_metroid_pilot sha256:IMMUTABLE_LOCAL_IMAGE_ID
```

## Archive and limits

`benchmarks/metroidvania_pilot/manifest.json` records the common prompt hash, requested model settings, original candidate hashes and session task IDs. Both agents were instructed to use only `apply_patch` to write their artifact and not inspect the repo, other outputs or tests. The submitted task text was identical; each destination was derived from its task name. No coordinator source repairs are applied to the generated games. The public comparison shell displays them in a sandboxed iframe, with each original HTML available to download.

Model aliases are requested selections rather than immutable provider-version attestations. Provider token usage, generation latency, hidden reasoning and full platform/system context are unavailable. One attempt per model on one specified game cannot establish a model ranking, general game-development quality or a PACT advantage. The earlier [counter pilot](agent-evaluation.md) is a separate, much simpler experiment. Formal repeated trials, provider provenance, broader policies and adversarial containment evidence remain unfinished.
