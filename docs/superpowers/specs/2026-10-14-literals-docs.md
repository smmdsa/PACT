# Literal source and readable public documentation

User authorized continued roadmap work and replacing raw Markdown display. Two independent tasks with unchanged executable IR and explicit documentation status.

## Literals

Optional compact frontend0.4 preserves every constant/literal node ID. `n = -42` lowers to i32.const; `v = "text"` lowers to utf8.literal. Only exact signed-i32 integers and JSON strings, no bool/float/null/arrays/object, no implicit argument nodes or hidden IDs. Recognize only under0.4; all0.2/0.3 syntax stays readable/defaultserializationunchanged. `dumps(document,compressed=False,literals=False)`; literals=True emits0.4, permits existing0.3 compressed sections when compressed=True. CLI --to compact-agent enables literals and compression together; compact-data remains0.3, compact remains0.2. Compare sameIR/revision/Wasm and existingpatchcompatibility; keep separate example .agent.pact. Runtime bulk-reset semantics remain pending and explicitly distinct from this source shorthand.

## Markdown

Use a tested established Markdown parser at build time, optionally pinned docs dependency, not compiler runtime dependency. Render headings/paragraphs/lists/tables/code/links into static HTML. Disable rawHTML; reject unsafe protocols via parser and resolver. Heading IDs deterministic and unique. Rewrite local Markdown paths to actual published pages; downloadable reports/examples linked to copied static files. Unknown repo paths resolve to GitHub canonical file URL. Build output no external JS/CDN requirement. Provide table ofcontents metadata.

Public docs layout: readable maxwidth, sidebar navigation/TOC, responsive tables, horizontally scrollable code, distinct inlinecode, accessiblefocusstates. Progress page reads committed CHANGELOG.md and roadmap and links verification evidence. Home shows most recent implemented source mode, real measured tokens, compatibility and pendingwork. Keep unfavorable traditional comparisons prominent.

## Validation and publication

Tests first forliteral parsing, legacyformatrejection, escapedstrings/surrogates/ranges, exactroundtrip and CLI, safeMarkdownURL/rawHTML/headings/tableandrelativepathoutput. Fullsuite andinput-onlygamevictory, both realtokenizers andfreshreview. CI installs optional doc dependencies before site tests; compiler commands do not import Markdown. Publish with expected GitHubhead andverifylive HTML structure/newcontent. Report visualQA limitations honestly if browser unavailable.
