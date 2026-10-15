# Same-prompt agent evaluation protocol

The formal evaluation path supplies trial material and a recorder, **not a completed provider benchmark**. An exploratory subagent pilot is archived separately below. The recorder calls no model API and compiles or executes no candidate. Source-token measurements in the traditional comparison are a different metric from successful editing, debugging, latency, or total task cost.

```sh
python -m benchmarks.agent_trials prepare --language pact --plan-seed 17 > pact-trial-pack.json
python -m benchmarks.agent_trials prepare --language python --plan-seed 17 > python-trial-pack.json
python -m benchmarks.agent_trials prepare --language javascript --plan-seed 17 > javascript-trial-pack.json
python -m benchmarks.agent_trials prepare --language c --plan-seed 17 > c-trial-pack.json
python -m benchmarks.agent_trials record external-trials.json > validated-trials.json
python -m benchmarks.agent_trials summarize validated-trials.json
python -m unittest tests.test_agent_trials -v
```

`prepare` emits one JSON pack to stdout. `record` reads a JSON array and emits the validated array; it does not append a database or run a verifier. `summarize` accepts the same array. Use `-` as the input path to read stdin. Invalid input produces a diagnostic on stderr and exit code 1. An empty input array is allowed and yields no result groups.

## Frozen task and contexts

The common instruction is the exact UTF-8 content, including the final newline, of `benchmarks/agent_trials/prompt.txt`. It is identical across all four languages. Send it as the same user instruction, with the separate language-specific source as the only baseline context. Preserve the same message structure/system prompt across languages and archive its bytes. The JSON pack also includes verifier-only oracle material: **do not send the entire pack to the model**. In particular do not reveal the expected traces, trial order, or previous outputs.

| Language | Named full-source baseline | Source format |
| --- | --- | --- |
| PACT | `benchmarks/agent_trials/counter.pact` | Compact `pact.module/0.1.0` source |
| Python | `benchmarks/agent_trials/counter.py` | Python source |
| JavaScript | `benchmarks/agent_trials/counter.mjs` | ES module source |
| C | `benchmarks/agent_trials/counter.c` | C11 source |

Each prompt, context, and oracle has its own SHA-256 and byte count in the pack. These are frozen copies rather than live references to other benchmarks. The task changes three signed-i32 wrapping updates to four, preserves the two initial values and interface, and retains bounds rejection without mutation. PACT also has an embedded expected test that must be updated. This is a deliberately small, chosen editing task; it does not establish general language quality or eliminate selection bias. Expand and pre-register the task set before claiming a representative comparison.

`cases.json` freezes a sequential trace and an isolated reset case for the embedded test. Expected values are derived from `((old + 4*amount + 2^31) mod 2^32) - 2^31` for index 0 or 1; invalid indices retain both cells. Inputs are signed-i32 integers. The arithmetic derivation is checked in the recorder's test suite independently of baseline execution. The trace is finite coverage, not proof for every input. Equivalent output traces also do not imply equivalent security policies: PACT declares checked writes and a test, while the other baselines expose language-specific errors/return codes and do not implement the same capability/contract system.

## Conducting the experiment externally

1. Pre-register the frozen revision, complete task set, model identifier and immutable provider model version, settings (temperature, top-p, reasoning effort, tools, and unsupported settings explicitly), total output/time budgets, candidate parsing policy, and a plan seed. Use identical budgets/settings and system instructions for all languages.
2. Run **five fresh trials per language** per model version. Each starts from the unchanged baseline in a fresh conversation, with no repair loop or previous attempt context. Use the same recorded per-attempt generation seed across languages where the provider supports it. If a provider cannot honor a seed, record that limitation in `settings`; the integer seed is the experiment's requested seed, not a claim of deterministic generation.
3. Follow the pack's seeded, shuffled 20-entry `trial_order`. Record attempts 1–5, actual order indices and the plan seed. Persist the emitted order as the authoritative plan; regeneration uses Python's `random` implementation, so pin Python for exact cross-version reproduction.
4. Measure end-to-end model request latency in milliseconds using a monotonic clock and count **actual provider-reported** input/output tokens, including any provider-accounted tool or reasoning usage. Archive raw provider responses. Do not substitute local source token estimates for billed usage. Record timeouts/errors as failed trials and retain their measured usage; if the provider does not expose usage, do not invent values to satisfy this recorder.
5. Archive the exact returned candidate bytes and response metadata. The external runner must record that the context and prompt hashes were actually sent. The recorder checks correspondence to frozen hashes, but cannot authenticate that assertion or the provider usage.
6. Send each candidate to an **independent external verifier in a disposable sandbox** with no network, credentials or host mounts and explicit process/CPU/memory/output/time limits. A configured sandbox provider is required. The recorder does not provide this sandbox or automated grading; do not run generated source with the traditional benchmark's local subprocess runner.

The external verifier should pin its revision and toolchains; compile/parse under the appropriate language; independently invoke the exported interface; reset state; normalize success/bounds outcomes; compare all frozen states; check the PACT embedded test and preserved declarations; and review that the minimal edit did not alter interfaces, initial values, dependencies, or bounds checks. It should reject candidate attempts to edit drivers/oracles or weaken policies. Use signed-i32 arguments, not language-specific coercions. Record every failed compilation, timeout, malformed answer and trace mismatch. Add hidden/pre-registered generated edge cases for larger studies, with independent mathematical expectations. Never let candidate-authored tests or expectations decide a pass. Freeze exact verifier commands and log bytes, recording SHA-256 provenance for both passing and failing trials.

## Initial isolated executor

The [Docker PACT/Python/JavaScript/C counter adapters](agent-sandbox.md) run the PACT reference interpreter, Python, JavaScript or C candidate in a disposable container and feed observations to the trace grader. They require a trusted immutable local image ID and have no host-execution fallback. These are not full source-policy verifiers or real model trial runners; the original recorder format/flags remain unchanged.

## Optional external trace grading

A separate [trace grader](agent-trace-grading.md) now compares externally supplied observations against the pinned, independently derived counter oracle and exact archived candidate bytes. It executes no candidate code. Its `behavior_pass` is a finite trace match, while `candidate_pass` remains null; sandbox execution and source-policy checks still belong to the external verifier. Recorder formats and flags remain unchanged.

## External record contract

Each JSON-array entry requires exactly these top-level fields; missing or unknown fields are rejected:

| Field | Required value |
| --- | --- |
| `task`, `language` | `counter-four`; one of `pact`, `python`, `javascript`, `c` |
| `model`, `model_version` | Nonempty provider/model and pinned version strings |
| `attempt`, `order_index`, `trial_plan_seed` | Integer 1–5, integer 1–20 matching the emitted order, nonnegative integer plan seed |
| `pass` | Boolean provided by the independent external verifier |
| `latency_ms` | Finite nonnegative number |
| `input_tokens`, `output_tokens` | Nonnegative integers from provider usage |
| `provider_usage` | Object containing matching integer `input_tokens`/`output_tokens`; extra finite JSON provider metadata allowed |
| `settings` | Nonempty object of finite JSON values, explicitly describing request settings and limitations |
| `seed` | Nonnegative integer requested generation seed |
| `budget` | Exactly positive integer `max_output_tokens` and `max_latency_ms` |
| `prompt_sha256`, `context_sha256` | Lowercase 64-digit SHA-256 matching frozen material |
| `candidate_sha256` | Lowercase SHA-256 of the exact archived candidate bytes |
| `verifier` | Exactly nonempty `command`, nonempty pinned `revision`, and lowercase SHA-256 `log_sha256` |

Successful records exceeding their declared output-token or latency budget are rejected; exact-limit successes are allowed. Failed over-budget trials remain valid and their full measured tokens and latency remain in totals. `budget_exceeded_trials` counts trials exceeding either limit once per trial. Booleans are rejected in numeric fields. NaN/infinity and negative measurements are rejected. Duplicate `(task, language, model, model_version, attempt)` records are rejected. The recorder requires provenance on every result, but verifies its shape, not whether logs/candidates exist or the stated command was executed. Trial records are therefore external assertions, not authenticated or automatically graded evidence. Test fixtures are synthetic validation data, not measured model results; no trial results ship with the protocol.

Summary groups are keyed by task/language/model/version. For each task/model/version, mixing settings, budgets or plan seeds is rejected across all languages and attempts. Each summary group includes its exact `settings`, `budget` and `trial_plan_seed`. Requested generation seeds must match for the same attempt number across languages; they may differ between attempts. This checks the requested seed pairing even when the provider cannot honor seeds, and does not establish deterministic model execution. `success_rate` is successful trials divided by all trials. `tokens_per_successful_task` is **all input and output tokens, including failed trials, divided by successful trials**; it is `null` when there are no successes. Totals and failed-trial counts always remain visible. An incomplete group is explicitly marked `complete_five_trial_group: false`; do not present it as the pre-registered five-trial experiment. The recorder cannot detect omitted failures, altered provider metadata, unreported retries, or discarded candidates. Preserve the raw audit trail.

## Broader benchmark plan

Pre-register tasks, expected outcomes and reporting rules across the following dimensions, with equivalent behavioral tasks where feasible. Report policy/security dimensions separately when language features differ.

| Dimension | Grading and measurements |
| --- | --- |
| Correct edits | Independent traces, compile validity, minimal diff, forbidden policy/interface changes; first-attempt success rate and total tokens per success |
| Diagnostics/debugging | Injected syntax/type/bounds failures; correct cause and repair; diagnostic bytes/tokens, repair attempts and time |
| Context retrieval | Full-source vs symbol-selected context under a frozen retrieval policy; correctness, omitted required facts, total retrieval plus request tokens |
| Stale concurrent patches | Two patches against the same frozen revision; detect stale base and conflict without silently dropping a change |
| Capability/bounds rejection | Forbidden writes/imports, invalid indices and excessive resource bounds; separately grade static rejection and runtime containment |
| Reproducibility | Pin revision, toolchain, prompt/context hashes, provider version/settings/seeds; repeat across machines and report variation |
| Runtime/build costs | Controlled hardware, warmup/repetitions, runtime latency, peak memory, compile time and artifact size; separate host/runtime dependencies |

The official [MultiPL-E repository](https://github.com/nuprl/MultiPL-E) describes translation of unit-test-driven code-generation benchmarks, including HumanEval and MBPP, to multiple languages. It is useful for multilingual synthesis design; PACT would need a validated language translation and execution adapter.

The official [SWE-bench repository](https://github.com/SWE-bench/SWE-bench) evaluates resolution of real repository issues. It is useful for larger editing/debugging tasks; a tiny standalone counter edit is not a SWE-bench score.

The official [LiveCodeBench repository](https://github.com/LiveCodeBench/LiveCodeBench) provides code-evaluation scenarios with time-separated problem collection aimed at contamination concerns. It is useful for broader task selection and temporal splits. This repository has not integrated any of these datasets and makes no claim that their existing harnesses support PACT. Dataset licensing, task translation, independent grading, sandbox integration and provenance would need to be resolved before reporting adapted results. Official repositories were checked on 2026-10-14.

## Exploratory GPT subagent pilot — 2026-10-15

The repository now archives real coordinator-visible responses from sessions requested as `gpt-6.1-sol` and `gpt-6-astra`, each at medium reasoning effort. Each model received the same counter-four instruction and the matching frozen source for PACT, Python, JavaScript and C. Sessions used `fork_turns: none` and were instructed to use no tools or external context. No oracle, expected edited output or other model response was included in the submitted task message. Hidden platform/system context and provider routing are not attested by this archive.

| Requested model alias | Valid responses | Static edit policy | Provider usage / immutable version |
| --- | --- | --- | --- |
| `gpt-6.1-sol` | One per language, 4 total | All four match | Unavailable |
| `gpt-6-astra` | One per language, 4 total | All four match | Unavailable |

For each language, both returned the same final source text. Both updated the PACT embedded expectation as well as its repeat count. This simple task did not distinguish the models. Static edit matches alone do not establish runtime correctness: the dedicated Docker workflow re-evaluates each archived trial with the independent behavioral grader and publishes individual receipts plus a summary artifact. Behavioral failures are retained as results rather than causing a trial to disappear. Infrastructure or identity failures still reject.

The archive is `benchmarks/subagent_pilots/2026-10-15-counter/`: input prefix, submitted task messages, final response text, extracted candidates, hashes, requested settings and session task identifiers are retained. Identical response contents are stored once per language and referenced by both trial records. The only source extraction is appending one LF to the coordinator-visible final text. This rule was documented during archiving, not pre-registered. It is not an archive of raw provider payloads or private reasoning. No response body was repaired.

There were nine launches. One Astra JavaScript attempt received a coordinator transcription error: its second initial value was `-2147473647` instead of the frozen `-2147483647`. The model preserved the value it was given. That input and response remain archived as `COORDINATOR_BASELINE_COPY_ERROR`; the attempt is excluded from the eight comparable trials and was replaced with a fresh session containing the correct baseline. It is not counted as a model failure or hidden retry.

This is `pact.subagent-pilot/0.1`, not the formal trial-recorder format: model aliases are requested selections, immutable backend versions and provider usage are unavailable, generation latency is not measured, launch order was not randomized and there is only one valid attempt per model/language. Success on one trivial task supports no ranking, cost comparison or claim that PACT improves model productivity. The four source policies also remain asymmetric. Full candidate approval stays null. Provider integration, broader task sets, pre-registration, repeated paired trials and the E2/E3 verification gates remain unfinished.

To repeat only execution verification, using the archived responses rather than generating new ones:

```sh
python3 -m tools.check_subagent_pilot sha256:IMMUTABLE_LOCAL_IMAGE_ID
```

A more complex [Metroidvania pilot](metroidvania-pilot.md) now generates human-playable HTML/JavaScript games from the same brief with both GPT aliases. It has independent Docker browser observations and original public artifacts; it remains separate from formal PACT-versus-traditional-language evaluation.
