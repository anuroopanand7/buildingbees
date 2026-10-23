# Context talent

How BuildingBees (and the agents that build it) keep the right information in front of a model at the right time:
what goes into a prompt, in what order, what is stored outside it, and what is dropped. It belongs to the platform
and to every bee: each bee's prompt is compiled by it. Source of the rules: `docs/CONTEXT.md`.

| Skill | What it does | Status |
|---|---|---|
| [session-guard](session-guard/SKILL.md) | Stops long sessions drifting and survives compaction: health signals, re-read the rule files, recite active rules, write a handoff | Adopted (MIT, wshobson/agents) |
| [context-compiler](context-compiler/SKILL.md) | The 12 rules for building any prompt: shared stable prefix, slices by graph, locked decisions at the tail, evict applied rounds, check every reply | Design, to build after 30 Oct |
| [knowledge-base](knowledge-base/SKILL.md) | Team knowledge (exact lookup) and product knowledge (scrubbed patterns across boards), retrieved on demand | Design, to build after 30 Oct |
