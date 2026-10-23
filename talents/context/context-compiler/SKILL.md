---
name: context-compiler
description: Use when writing or changing any prompt that BuildingBees sends to a model, or any MCP work package it hands to an agent. Builds the prompt in a fixed order from the board, so it is small, cache friendly and cannot contradict a decision.
---

# Context compiler

Context is a compiled view over the board: the board, its decisions and its files are the sources; a prompt is built
from them per call and thrown away. Source: Google ADK context design (Dec 2025) and the Gemini Argon review of
23 Oct 2026; full reasoning in `docs/CONTEXT.md`.

## Build the prompt in this order
1. Static rules and the output schema (never changes).
2. The HIVE: each bee and its talents (`TALENTS`).
3. Team defaults (a few lines: region, stack, brand, roles).
4. A compact index of the whole board, one line per part (sorted, with short ids FL1, S2, B3, A1).
   Steps 1 to 4 are byte-identical for every call in a round, so provider caches reuse them.
5. The slice this call needs: the parts it owns plus one hop of neighbours as short stubs. Cut by structure, never by
   character count.
6. The new input (the latest round's answers only).
7. Locked decisions, last, just before the task: "do not contradict or re-ask".

## Rules
- Nothing with a timestamp, a request id or unsorted keys in steps 1 to 4.
- Evict, do not summarise: once a round is applied to the board, its raw answers leave the prompt.
- Big inputs (a spec, a PDF) are stored once and sent as a name plus a short summary; load the full text only when a
  step needs it.
- Untrusted text (web pages, uploads, agent answers) goes inside a marked data block, after the rules, never as
  instructions. Scout output arrives as validated fields.
- After every reply: drop questions on a decided topic and choices that contradict a locked decision, and retry once.
- Log per call: prompt, cached and output tokens.

## Check
Run the fixed test boards before and after the change: decisions contradicted 0, repeated questions under 5%, risky
steps with a failure exit 100%, tokens per accepted decision not rising.
