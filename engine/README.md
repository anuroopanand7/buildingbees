# Engine skills

Rules for how BuildingBees itself works, shared by every bee: building prompts, memory, guarding long sessions. They
are not a bee's talent, so they do not live in `talents/` (Argon's review, 23 Oct 2026: "context is a cross-cutting
platform execution engine"). The code they describe is in `src/`; this folder holds the written rules.

| Folder | What | Used by |
|---|---|---|
| [context](context/README.md) | Prompt compiler rules, knowledge base, session guard | The prompt code in `src/`; coding agents working on this repo |
