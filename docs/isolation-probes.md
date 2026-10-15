# Finite Docker isolation probes

The E3 suite exercises the actual Linux/Docker counter runtime image with the same immutable-image selection, user, network, mounts, CPU/memory/PID limits and bounded capture as candidate execution. It uses authored attack fixtures, not model responses. No resource attack runs on the outer host.

```sh
python3 -m tools.check_agent_isolation sha256:IMMUTABLE_LOCAL_IMAGE_ID
```

The dedicated CI builds the trusted image, executes the probes and retains every per-probe observation plus `build/sandbox-checks/isolation/summary.json`. The summary binds the image and probe source hash. A failing observation fails CI; it is not replaced by an invented pass.

| Probe | Observation required | Control or bound |
| --- | --- | --- |
| Root/host filesystem and noexec | Root write denied, random host sentinel absent, direct execution under `/tmp` denied | The same file is readable as a script by `/bin/sh`, explicitly showing that noexec does not forbid interpreted code |
| External network | Documentation-only destination `192.0.2.1:80` has no route; only loopback interface exists | A local TCP exchange succeeds, so a broken socket implementation is not mistaken for network isolation |
| File size | `EFBIG` at the configured 1 MiB size | At most eight bounded writes |
| Temporary space | `ENOSPC` on the 16 MiB tmpfs | At most 40 files, each no larger than 1 MiB |
| Processes | `fork` returns `EAGAIN` below 32 children | At most 64 attempts; spawned children are killed and reaped |
| CPU | A child is killed after roughly 10 CPU seconds | `wait4` records CPU usage and signal; parent remains available to report it |
| Memory | Docker records `OOMKilled`, exit 137 and stopped state | Allocation attempts stop at 512 MiB; configured container memory is 128 MiB |
| Output | Capture reaches its limit and stops execution | Combined stored stdout/stderr stays at or below 1 MiB |
| Wall time | The bounded capture times out | A fixed 60-second sleep is interrupted by the existing 15-second host deadline |
| Cleanup error | Removing an absent verifier container returns an actual daemon error | Separately, every created probe container must be forcibly removed and absent from a filtered Docker listing |

The CPU probe uses the normal 15-second outer wall deadline. CPU time and wall time differ: a heavily loaded runner can produce a genuine failed observation rather than a CPU-limit receipt. Such results remain failures requiring inspection, not silent acceptance.

## Receipts and failure preservation

Receipt `pact.agent-sandbox-receipt/0.8` adds `cleanup_verified` after successful removal and an absence check. A cleanup error still prevents a successful candidate receipt. Configuration verification now additionally checks requested CPU/file/descriptor ulimits, tmpfs size/options and absence of added capabilities.

Probe records retain bounded raw logs, available Docker state, runtime flags and container identity even when post-run inspection or cleanup fails. `cleanup_verified:false` prevents a probe pass. Unit tests inject cleanup errors to verify failure preservation without launching attacks. These synthetic tests are not executed isolation evidence.

## Scope

These probes establish finite observations on a particular CI image/kernel/daemon. They do not demonstrate resistance to kernel exploits, every syscall, all namespaces, cross-container side channels, hostile daemon behavior or credentialed deployment environments. Network evidence covers the inspected `none` profile and one no-route attempt, not every possible exfiltration channel. Host-sentinel absence covers one deliberately unmounted path. Container image files remain readable according to normal permissions.

The absent-container cleanup probe demonstrates real backend error propagation; it does not simulate losing the daemon during removal of a live hostile container. A daemon outage may require operator cleanup. Configuration inspection, successful finite probes and forced removal are not universal containment proof or authenticated evaluation. Model-trial results and original candidate bytes remain separate and unchanged.
