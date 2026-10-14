# Task ownership and acceptance

L1 agent: pact/compact.py, tests/test_literals.py. Literal sugar preservesIDs/IR/Wasm/revision; default0.2 unchanged, earlierheadersrejectbareliterals.
M1 agent: tools/markdown_docs.py, tests/test_markdown_docs.py, docs/site-requirements.txt. Established pinnedbuildparser, safeHTML, linkrewrites, uniqueheadingIDs, output+toc API render_markdown(text,source_path,page_map)->(html,toc); toc list{id,title,level}. Compilerdependency-free.
Root: CLI, build_site.py layout/navigation/progress, CHANGELOG/README/ROADMAP/AGENTS/docs, benchmarks/newliteralreport, separateagentexample,CI/siteQA. Actualtokenmeasurements andcompletebuildpass.
Freshreviewer: independentread-onlycheckbothdomainsafterintegration. Fiximportantfindingswithregressions. Agentsnevercommit/publishorediteachotherfiles.

## User steering: broader evaluation

User requested runtime performance and cross-language same-prompt LLM benchmark. P1 runtime agent owns benchmarks/runtime_performance.py,benchmarks/runtime/*,tests/test_runtime_performance.py,raw local report,docs/runtime-performance.md. Acceptance: actual freshprocess samples validated by independent state/checksum oracle; no timingassertions or universalrank claims. E1 trial agent owns benchmarks/agent_trials.py, frozen contexts/prompt/oracle, tests/test_agent_trials.py,docs/agent-evaluation.md. Acceptance: identical prompt hashes, failed-trial accounting, externalprovenance validation, no realtrialfabrication/modelcalls/untrustedexecution.

Default runtime run:100,000 calls,samples5,warmup10,000 and all20 states verified. Trial protocol:20 shuffled trials permodel (5/language), structurallyvalidated externalrecordsonly; actualexternalrunner/sandbox/modeltrials remain pending.
