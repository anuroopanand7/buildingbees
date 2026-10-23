# Talents

A bee has talents, and a **talent is a collection of skills** (each skill is a folder with a `SKILL.md`, the same
shape as Claude skills). The talents of each bee are listed in `src/adapters/spec_prompts.py` (`TALENTS`): that list
decides which bee asks which question. This folder holds the skills behind them.

```
talents/
  <talent>/
    README.md          what the talent is, who uses it, which skills it holds
    <skill>/SKILL.md   one skill: when to use it, the rules, how to check it
```

Rules for adding a skill (from the 23 Oct 2026 skills research):
1. Copy prose only. Never copy scripts, hooks or anything that runs.
2. Read the whole file first: no hidden text (zero-width characters, HTML comments, base64), no `.env`, no URLs to fetch.
3. Keep the licence: MIT or Apache 2.0 only, with the source and copyright line in `THIRD_PARTY_NOTICES.md`; mark what we changed.
4. Rewrite it for planning before code: ask instead of guessing, plain words for founders.
5. Skills are compiled into the repo after review; nothing is loaded while a person is using the product.

| Talent | Skills | Status |
|---|---|---|
| [context](context/README.md) | session-guard, context-compiler, knowledge-base | session-guard in use; the other two are design rules, built after 30 Oct |
