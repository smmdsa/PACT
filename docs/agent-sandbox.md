# Isolated PACT counter adapter

The first execution adapter targets only the frozen PACT `counter-four` task. It runs the closed-schema PACT reference interpreter in a disposable Docker container, produces the external trace format and feeds that observation to the independent trace grader. Python, JavaScript and C candidate execution adapters remain pending.

```sh
docker build -f benchmarks/sandbox/Dockerfile -t pact-counter-verifier .
docker image inspect --format '{{.Id}}' pact-counter-verifier
python3 -m benchmarks.agent_sandbox archived-candidate.pact --image sha256:IMAGE_ID_FROM_INSPECT
```

The image argument must be a complete immutable local image ID. Tags, registry references and automatic pulls are rejected. Building the trusted image can use the network; candidate execution cannot. The Dockerfile's base tag is not a reproducible-build lock: archive the resulting image and receipt's image ID to rerun that exact runtime. The image is an operator-trusted executable dependency, not candidate-controlled input.

## Execution boundary

Linux and an accessible Docker Engine are required. Missing backend, unsupported platform, mutable image identifier or weakened inspected configuration rejects; there is no host-execution fallback. The runner creates a named container, inspects its effective configuration, sends only the bounded candidate snapshot and frozen call arguments through stdin, runs the worker, and forcibly removes the container in a `finally` block. A cleanup failure prevents a success receipt.

Requested constraints are network `none`, read-only root filesystem, UID/GID 65534, all capabilities dropped, no-new-privileges, 128 MiB memory with no extra swap, one CPU, 32 processes, CPU/file/descriptor limits and a 16 MiB temporary filesystem. No host mounts, Docker socket, credentials or host environment variables are passed into the container. Automatic image volumes reject. The worker stages candidate data in its bounded temporary filesystem. The worker is fixed inside the trusted image; candidate source is never a shell command or evaluated as Python. It accepts exported `advance(index, amount) -> unit` and a two-element counter. Reference evaluation has a 100,000-node budget for the sequential calls and a fresh budget for the reset observation.

Each candidate read is bounded to 1 MiB. Worker execution has a 15-second wall-clock limit; Docker control operations have separate 10-second timeouts. Worker JSON and diagnostics are structurally small (ten cases plus reset, diagnostic text capped at 512 characters); captured output also has a 1 MiB acceptance limit. Timeout/runtime failure observations retain raw captured output in the receipt. Infrastructure errors reject rather than inventing a successful execution.

Docker's configured restrictions depend on the host kernel and daemon. This adapter is not a VM, independent bytecode verifier, authenticated evaluator or proof against kernel/container escapes. Configuration inspection and finite CI fixtures do not establish universal containment. Use a disposable worker host without credentials for model trials. The [Docker run reference](https://docs.docker.com/engine/containers/run/) documents the requested resource and privilege controls; candidate bytes are transferred through the attached stdin stream.

## Receipts and scope

`pact.agent-sandbox-receipt/0.2` contains the immutable image ID, generated external trace, grader report, restricted source-policy report and raw stdout/stderr encoded as base64. Version 0.2 adds the policy requirement to CLI success; historical 0.1 receipts contain behavioral grading only and are not reclassified automatically. Executor `log_sha256` hashes compact sorted-key JSON of that two-field log object. Source bytes are hashed before copying. The receipt reports that isolation configuration was checked, while `candidate_pass` remains null and `model_trial` remains false. The embedded grade also retains `execution_authenticated: false`; image and log identities are not signatures.

Exit 0 means both the observed trace and the restricted canonical counter-four IR policy match; exit 2 means a behavioral or source-policy failure and exit 1 means invalid input or infrastructure rejection. Receipts include a separate static `policy` report. It permits only the frozen counter IR with repeat count 4 and the independent expected test value; every other semantic field must remain unchanged. Compact/JSON formatting can differ without changing IR. The policy can reject other correct rewrites, does not measure textual diff size and is not a general source-policy verifier. Candidate functions are not run by the policy checker; embedded tests are not independently executed as declarations here. The worker compiles/validates source semantics with the existing analyzer and runs the reference interpreter; this adapter does not run Wasm. No provider is called and no benchmark leaderboard is produced.

The dedicated CI workflow builds the image, exercises authored baseline/edited/malformed fixtures and a behaviorally matching candidate rejected by the source policy in actual containers and archives their receipts. These are integration fixtures, not model results. Local environments without Docker can verify configuration and fail-closed behavior but cannot claim executed isolation. Broader language adapters, hostile-resource probes, source-policy verification and real provider trials remain pending.
