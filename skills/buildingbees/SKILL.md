---
name: buildingbees
description: Plan a product before building it, with the person deciding and no guesses. Use when someone wants to build an app or feature from a rough idea, when a spec has gaps, or before a coding agent starts on something new. Drives the BuildingBees MCP server: your own model drafts the user flows, screens and plan; the person answers the open questions; the board shows it all as it happens.
---

# BuildingBees: plan with the person, then build

BuildingBees turns an idea into user flows, screens and a build plan, and keeps a list of every decision still open.
The rule that matters: **you never decide a product question for the person.** You draft; they decide.

## Setup (once)

```bash
claude mcp add buildingbees -- python3 scripts/mcp_server.py
```

## The loop

1. **Start.** Call `start_board` with the idea in the person's words. Share the board link it returns so they can watch.
2. **Draft.** Each tool may return a TASK: a prompt and a JSON Schema. Answer it with your own model, as ONE JSON
   object that fits the schema, and send it with `submit_answer`. If it does not fit, you get the reason: fix and resend.
3. **Ask.** Call `open_questions`. Ask the person each one, in plain words, with the suggested options. Record their
   answer with `answer_question`. If they do not know, say so and leave it open; do not pick for them.
4. **Update.** Call `run_bees` with `update` and answer the task. Repeat steps 3 and 4 until `plan_check` has no blockers.
5. **Screens, then plan.** `run_bees` with `screens`, then with `plan`, answering each task.
6. **Build from it.** `get_plan` gives the Brief with stable ids (F1 features, FL1 flows, S1 screens, B1 buttons,
   A1 APIs). Build in its order. Anything marked NOT DECIDED: ask, or `add_note` on that part of the board.

## Good drafts

- Plain words a founder understands; short UPPER_SNAKE ids.
- Questions only about real product decisions (who, what, what happens when it fails), never about standard details
  like password rules or page layouts.
- Every failure path gets a branch: payment fails, a person says no, the network drops.
