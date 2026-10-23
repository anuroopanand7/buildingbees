# Talents

A bee has talents, and a **talent is a collection of skills** (each skill is a folder with a `SKILL.md`, the same
shape as Claude skills). Which bee owns which talent is `TALENTS` in `src/adapters/spec_prompts.py`: that list decides
which bee asks which question, and this folder holds the skills behind it. Rules for how the platform itself works
(prompt building, memory, session hygiene) are not talents; they live in [`engine/`](../engine/README.md).

```
talents/
  <bee>/                 north, kala, pixel, bolt, poke, shield, scout
    <talent>/            the talent's name in TALENTS, as a folder (failure-paths)
      <skill>/SKILL.md   or SKILL.md directly when the talent has one skill
```

Every `SKILL.md` starts with a header the prompt code can read:

```yaml
---
name: failure-exits
description: when to use it, in one sentence
owner_bee: poke
talent: failure_paths
version: 1
source: where it came from (repo, or "ours")
license: MIT, Apache-2.0 or ours
max_tokens: 150        # the body must stay under this
---
```

Rules (from the 23 Oct 2026 research with Argon):
1. Copy prose only. Never copy scripts, hooks or anything that runs; read the whole file; no hidden text, `.env` or URLs.
2. MIT or Apache 2.0 only, with the source and copyright line in `THIRD_PARTY_NOTICES.md`; mark what we changed.
3. Rewrite for planning before code: ask instead of guessing, plain words for founders.
4. A skill body is 150 to 250 tokens, and a call carries at most two skills, so a cheaper model (Nemotron Super) keeps them.
5. Skills are compiled into the prompts at build time after review; nothing is loaded while a person uses the product.
6. Test each one on the fixed test boards before and after; remove it if contradictions or tokens go up, or failure-path coverage does not improve.

| Bee | Talent | Skill | Status |
|---|---|---|---|
| Poke | failure paths | [failure-exits](poke/failure-paths/SKILL.md) | In use (enforced in code) |
| Shield | local rules | [india-dpdp-gst](shield/local-rules/india-dpdp-gst/SKILL.md) | **In use**: `src/core/skills.py` adds it to every prompt of a board that looks Indian. A/B on Nemotron, Pune tuition idea: the Compliance Bee goes from asking only about data retention to also asking if under-18s use the app and if the centre is GST registered |
| North | scope shaping | [no-tech-in-requirements](north/scope-shaping/no-tech-in-requirements/SKILL.md) | Written, not wired (our prompts already keep tech out of the PRD; test before wiring) |
| Pixel | screen states | [four-states](pixel/screen-states/four-states/SKILL.md) | Written, not wired (states are already asked where real) |
| Bolt | data modelling | [who-can-do-what](bolt/data-modelling/who-can-do-what/SKILL.md) | Written, not wired (the schema doc already has an access line per table) |

The last three were drafted by DeepSeek through OpenCode on 23 Oct 2026 (it follows the format well but writes about 30% too long, with filler bullets), then rewritten and checked by Claude.

Next, by rank: Poke `3 exits` upgrade, North `brainstorm-socratic-cap`, Kala `design-tokens`, Shield `stride-threat-model`, Poke `gherkin-given-when-then`, Pixel `wcag-accessibility-gate`.
