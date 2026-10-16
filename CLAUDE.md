# BuildingBees: rules for coding agents

Goal of this repo right now: win the Google Cloud AI Builder Cup (due 18 Oct 2026, Gemini on Cloud Run) and the Nebius x NVIDIA hackathon (due 30 Oct 2026, Nemotron). Judges read the README, the code and the live demo, so keep all three clean.

- Read `docs/ARCHITECTURE.md` before changing prompts, the board or the question rules.
- Comment all new code: a docstring on every function (what and why), a one-line comment on any non-obvious line. Write so another human or agent can follow it cold.
- Keep `README.md` and `docs/ARCHITECTURE.md` current when behaviour changes.
- Tests: `.venv/bin/python -m pytest -q` must pass; new behaviour gets a test using the fake engines (no real model calls in tests).
- Prompt changes: run `.venv/bin/python -m scripts.eval_questions gemini` (or `nvidia`) and put the numbers in the commit message.
- Never use em dashes. Never commit `.env` or keys. Zero spend: free tiers only.
- The Google track must run on Gemini; the NVIDIA track on Nemotron. Do not mix them in a demo.
