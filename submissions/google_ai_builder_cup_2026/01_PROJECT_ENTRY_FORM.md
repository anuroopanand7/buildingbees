# Google Cloud AI Builder Cup 2026: entry form draft

Everything here describes the prototype as it runs today.

## Project overview

- **Project name:** BuildingBees
- **Team:** BuildingBees (leader: Perli Anuroop Anand)
- **Track:** Future of Work & Enterprise Productivity
- **One line:** Other tools guess what you meant. BuildingBees asks.
- **Who it is for:** product teams, founders without a product manager, and anyone about to hand an idea to engineers or to an AI coding agent.
- **Live prototype:** https://buildingbees-853213660594.asia-south1.run.app
- **Code:** https://github.com/anuroopanand7/buildingbees (MIT licence)
- **Google technology:** Gemini API (structured output, native PDF input), Google Cloud Run, Cloud Build.

## Abstract (about 150 words)

AI can now turn one sentence into screens, diagrams or code. The catch is that one sentence leaves most decisions out, so the tool guesses, and teams discover those guesses in production.

BuildingBees works the way a good product team does. You say what you want to build. It draws the user flows first, with no screens. Then six bees, each owning one aspect of the product (scope, design, frontend, backend, edge cases, compliance), ask what the idea leaves out, one question at a time. Every answer is read by Gemini: a vague answer gets a sharper follow-up, a clear one redraws the board in front of you. Only when the flows are agreed are the screens drawn, with wireframes, buttons and the APIs behind them, and the bees ask again.

The result is a brief that records every decision and marks everything still undecided, ready to hand to engineers or a coding agent.

## The problem

1. One-prompt tools have to guess everything the prompt leaves out, and they guess confidently.
2. Product specs describe what a user wants, not what happens when something fails.
3. The questions that prevent rework (who exactly, what if it times out, are we allowed to store this) are asked late, or never.

## How it works

1. **Idea in.** Two lines, a PRD, or a PDF.
2. **Flows first.** Gemini returns users and step-by-step flows as structured data. No screens yet.
3. **The bees ask.** Each question belongs to one bee and points at one step of a flow.
4. **Every answer is read.** Vague answers get a follow-up. Clear answers rewrite the board: steps change, a new flow appears if the user asked for one, and the bee says what it did.
5. **Screens.** The agreed flows and decisions become screens with wireframes, buttons and API calls. The bees ask again, screen by screen.
6. **The Brief.** One document with every flow, screen and decision, plus what is still open. Undecided fields are printed as NOT DECIDED.

A screen is "ready to build" only when it has no open blocking question and no missing detail.

## Google technology in use

| Technology | Where |
|---|---|
| Gemini API, structured output (`response_schema`) | Flows, questions, screens, and the per-answer reaction that updates the board |
| Gemini native PDF input | Uploading a spec as a PDF |
| Automatic model fail-over | A second Gemini model takes over when the first is overloaded or slow |
| Google Cloud Run | Hosts the prototype, scaled to zero when idle |
| Cloud Build | Builds the container on deploy |

## What is real today, and what is not

| Real and tested | Not built |
|---|---|
| Flows-first mapping, six bees, follow-ups on vague answers, live board updates, screens with wireframes, readiness, changing an answer, the Brief (copy, download, print, agent link), 20 automated tests, live on Cloud Run | Accounts, shared editing, durable storage (boards live in memory; the browser restores them), integrations with ticketing tools |

The six bees are roles inside one model call, not six separate agents.

## Why it can scale

The questions a product team needs answered are the same in Hyderabad, Singapore and Sydney. BuildingBees needs no setup, works from two lines of text, and produces a brief any engineer or coding agent can build from.

## Team and eligibility

- Team of 2 to 4 (team formation closes 14 Oct 2026).
- Working professionals, JAPAC, 21+.
