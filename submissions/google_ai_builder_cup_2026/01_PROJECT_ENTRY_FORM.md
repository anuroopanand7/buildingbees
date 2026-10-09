# Google Cloud AI Builder Cup 2026: Entry Form Draft

Everything below describes what the prototype actually does today. Anything planned is marked as planned.

## Project overview

- **Project name:** BuildingBees
- **Team:** BuildingBees (leader: Perli Anuroop Anand)
- **Tagline:** An AI product manager that asks the questions before any code gets written.
- **Target users:** product managers, founders without a PM, engineering leads, and teams that hand specs to AI coding agents.
- **AI model:** Google Gemini via the Gemini API (`google-genai` SDK), with structured JSON output and native PDF input.
- **Hosting:** Google Cloud Run (planned for the submission build).
- **Code:** https://github.com/anuroopanand7/buildingbees (MIT licence)

## Abstract (about 150 words)

AI has made writing code cheap. Deciding exactly what to build is still slow and vague, and whatever a spec leaves out, coding agents guess.

BuildingBees takes a normal product spec (pasted text or a PDF) and uses Gemini to turn it into a typed, zoomable map: users, flows, screens, buttons (CTAs) and the APIs each button calls. A Socratic Question Engine, also powered by Gemini, then reads every node and asks about what the spec leaves out: failure paths, timeouts, retries, empty and error states. Blocking questions stop a screen from being marked "ready to build" until a human answers them. The rule is simple: assumption is not approval.

Each answer is written back into the spec, and a live readiness score shows which parts of the product are safe to hand to engineers or AI agents.

## The problem

1. PRDs describe what a user wants, not how the product behaves when things fail.
2. Design files show layout, not logic: no timeouts, retries or error routes.
3. When an AI coding agent meets a gap in the spec, it guesses, confidently.

## How it works

1. **Choose the engine.** The app makes you pick an engine before you start (Gemini for this entry).
2. **Bring a spec.** Paste a PRD or upload a PDF. Gemini returns a structured graph using a strict response schema.
3. **Zoom in.** Click any node to focus the board on its path, from the user down to the API.
4. **Answer the questions.** Each node shows its open questions, with suggested answers to pick from. Answers are saved into the spec.
5. **Readiness.** Each screen gets a readiness score. One open blocking question in its branch keeps it at 0%.
6. **Ask again.** "Ask Gemini what this node is missing" runs a fresh pass on a single node.

## Google technology used

| Technology | Where |
|---|---|
| Gemini API, structured output (`response_schema`) | Spec to typed graph; question generation |
| Gemini native PDF input | Uploading a PRD as a PDF |
| Google Cloud Run | Hosting the demo (planned before submission) |

## What is real today vs planned

| Real and tested | Planned |
|---|---|
| Spec to graph with Gemini, question engine, readiness score, answer write-back, web app, MCP server for coding agents, 10 automated tests | Cloud Run deployment, multi-user collaboration, export to Jira and Linear |

## Team and eligibility

- Team of 2 (forming before 11 Oct).
- Working professionals, JAPAC, 21+.
