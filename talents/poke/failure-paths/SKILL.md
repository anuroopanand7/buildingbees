---
name: failure-exits
description: Use when a flow has a step where money moves, a slot is taken, a file is uploaded or an order is placed. Every such step needs a "what if it fails" path, and the Test Bee asks what happens there instead of guessing.
owner_bee: poke
talent: failure_paths
version: 1
source: ours (talent-skills research, 23 Oct 2026; idea "3-exit node")
license: ours
max_tokens: 220
---

# Failure exits

- A step whose title says pay, checkout, book, reserve, upload or order can fail for reasons the person cannot control.
- Such a step must have a split with a "No" path. If the flow has no split of its own, add one empty "No" path on the
  first such step: `clean_branches()` in `src/core/ingest.py` does this.
- Never fill an empty path with a guess. The Test Bee asks: what happens on the "No" path after "<step> went through?"
  with options: let them try again, show a message and stop, someone follows up.
- Standard handling (a failed payment shows why and lets them try another card) may be drawn without asking; a product
  choice (the slot was taken: next slot or a waiting list?) is asked.

Check: on the fixed test boards, every payment, booking and upload step has a failure exit (100%), and the questions
per idea do not rise above 12.
