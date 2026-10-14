# Portability validation

PACT compiles its numeric modules to WebAssembly and its compiler uses Python's standard library. These choices reduce platform dependencies; actual system and host behavior still needs verification.

The dedicated portability workflow runs Python 3.12, Node 24, the full unit suite, checked greeting/game builds, documentation, the input-only victory, qualified source lookup and revision-checked patches on Ubuntu 24.04, Windows Server 2022 and macOS 15. Each system publishes its game artifact, manifest, playthrough and source-location response. Python UTF-8 mode is explicit; repository text files use LF to preserve frozen source hashes.

The first matrix run passed Linux and macOS, and exposed Windows CRLF/executable-name assumptions. Fixes retain strict manifest validation and canonical UTF-8/LF tool output. All-system verification is pending the corrected matrix run; Linux-only local success is insufficient. Inspect the [workflow runs](https://github.com/smmdsa/PACT/actions/workflows/portability.yml) for actual outcomes. Browser engines, interactive rendering, mobile controls, audio and native distribution remain outside this matrix.

The local runtime report is historical evidence for one Linux machine. Cross-platform tests compare correctness, not performance rankings. Optional C benchmark dependencies and timers must work on each runner where C is available; missing dependencies are explicit skips rather than compatibility evidence.

On Windows, the traditional-language comparison normalizes text-mode stdout CRLF to LF when comparing logical frozen traces. The report records raw transport byte counts/hashes alongside that explicit normalization; standalone carriage returns are preserved. Source-token inputs remain the exact untouched source bytes. C artifacts use an explicit .exe suffix for both execution and binary provenance.
