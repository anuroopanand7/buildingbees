# Context talent

How BuildingBees (and the agents that build it) keep the right information in front of a model at the right time:
what goes into a prompt, in what order, what is stored outside it, and what is dropped. It is part of the engine, not a bee's talent: every bee's prompt is compiled by it. Source of the rules: `docs/CONTEXT.md`.

| Skill | What it does | Status |
|---|---|---|
| [session-guard](session-guard/SKILL.md) | For coding agents working on this repo (not used in product prompts): stops long sessions drifting and survives compaction by re-reading the rule files and writing a handoff | Adopted (MIT, wshobson/agents) |
| [context-compiler](context-compiler/SKILL.md) | The 12 rules for building any prompt: shared stable prefix, slices by graph, locked decisions at the tail, evict applied rounds, check every reply | Design, to build after 30 Oct |
| [knowledge-base](knowledge-base/SKILL.md) | Team knowledge (exact lookup) and product knowledge (scrubbed patterns across boards), retrieved on demand | Design, to build after 30 Oct |
