# Contributing with agents

PACT is developed for agents that discuss expected outcomes with people, then inspect and modify explicit executable structures. Agent-first does not mean assuming a specific model thinks in undocumented opcodes. Efficiency and reliability must be measured.

## A focused contribution

1. Read AGENTS.md, syntax, security and the roadmap. Confirm what is implemented.
2. Choose one bounded outcome and affected files. If collaborating, assign nonoverlapping owners and a separate reviewer.
3. Use `pact symbols` to find functions and `pact inspect --function ID` to retrieve context. Query helpers as needed; omitted code is not permission to assume behavior.
4. Preserve IDs, explicit effects, indices and arithmetic semantics. Discuss changes to language semantics in a versioned specification.
5. Reproduce the relevant failure before fixing it; verify actual behavior independently of the agent's claims.
6. Run the full suite, compile examples and use the input-only playthrough for gameplay changes.
7. Submit a focused change with expected outcome, evidence and remaining uncertainty.

Inspection responses are context, not executable modules. Revision hashes identify the source version; they are not signatures or an implemented transaction API. Test summaries show relevance, not sufficient evidence of correctness. Read or run the actual cases before asserting coverage.

## Useful next contributions

| Outcome | Scope | Required evidence |
| --- | --- | --- |
| Measure agent edits | Benchmark task protocol and isolated runner | Multiple real model trials; counts include tools, retries and failed attempts |
| Make long operand parsing linear | Compact parser | Regression preserving rejection behavior and bounded-work measurements |
| Improve cross-platform confidence | CI and browser fixtures | Actual Windows/macOS/browser runs, not platform compatibility claims by inspection |
| Propose revision-checked patches | Specification first | Stale-source rejection, atomic failure and semantic-equivalence examples |

The repository provides coordination guidance, not a service that summons external agents or grants them credentials. Each contributor operates through their own authorized tools. The owner still needs to choose licensing and community contribution terms.
