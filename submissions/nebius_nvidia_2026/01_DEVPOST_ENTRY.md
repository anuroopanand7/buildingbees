# Devpost entry: Nebius x NVIDIA hackathon (rewritten 20 Oct 2026)

**Deadline: 30 Oct 2026, 10:30 pm IST.** Track: Best Apps and Agents. Bonus: Best Use of Tavily.
Needs: a working demo URL, a public YouTube video of 3 minutes or less showing Token Factory and Nemotron, a public repo with a licence, this text.
Judged equally on technological implementation, design, potential impact and quality of idea.

**Demo URL (Nemotron only):** https://buildingbees-nemotron-853213660594.asia-south1.run.app
**Repo:** https://github.com/anuroopanand7/buildingbees
**Video:** (add the YouTube link)

---

## Project name
BuildingBees

## Tagline (one line)
Agentic product planning on NVIDIA Nemotron: a team and AI bees plan the product with no gaps, so agents can build it without guessing.

## Inspiration
I work as a consultant. For one of my clients, I suggested we build the whole product with an AI agent. I learned quickly that agents only go straight when the plan has no gaps. Otherwise they assume stuff and hallucinate.

So for 7 days I ran a little ritual. Codex drew the user flows on a Figma board and left questions for every role. My team commented during the day, and every evening I fed their inputs back and redrew everything. After a week the plan was so clear that an agent could build it without guessing.

Why do vibe coded products have bugs? Because there are so many gaps left in the plan that the agent fills them with guesses. BuildingBees is that 7 day ritual on one board, in a few hours.

## What it does
- You say your idea in plain words, alone or with your team.
- Nemotron draws the user flows first, with every split where things can go wrong, plus a feature list (F1, F2) and short ids for every flow, screen and API.
- Six bees (product, design, frontend, backend, testing, compliance) ask only what your team actually has to decide, in rounds of up to 6 questions. A Scout Bee reads the web first with Tavily, so the questions are about real rules and real failures.
- Everyone can comment on any card, like Figma comments. The board only changes when you press Update the board, and it redraws once per round.
- When people disagree, the bees don't pick a side. They flag the misalignment for the product owner.
- Then it draws the screens as specs (elements, buttons, the API behind each), runs a plan check, and writes the full plan: user stories with Given, When, Then tests, a feature list, a build order and every decision with who made it.
- You can share the plan as one web page, download it, or give it to a coding agent through our MCP server.

## How we built it
- **NVIDIA Nemotron 3 Ultra (550B) on Nebius Token Factory** does all the reasoning: drawing flows and features, reading every round of answers and notes, flagging misalignments, drawing screens and writing the plan. We call Token Factory's OpenAI-compatible API with JSON schema output and thinking switched off (`/no_think`), and validate every reply against a Pydantic schema before it touches the board.
- **Tavily** powers the Scout Bee: one search per new board, shown as sources, never counted as a decision.
- FastAPI on Google Cloud Run (scales to zero), Firestore for boards and tester feedback, a single-page canvas UI in plain JavaScript.
- Guardrails in Python: vendors, timeouts and limits nobody stated are removed and turned into questions; standard details become visible defaults; a plan check blocks until nothing important is left to guess.
- An MCP server (`scripts/mcp_server.py`) so Claude Code, Cursor or Codex can read the plan and leave notes for the bees.
- 54 automated tests, all on fake engines, so no model calls in CI.

## Challenges we ran into
- Our first version asked one tester 70+ questions. He called it "a never-ending Google form". We rebuilt the question rules so the bees only ask what the team must decide; it is about 9 per idea now.
- With thinking on, Nemotron spent all its tokens reasoning and the JSON got cut off. Turning thinking off and asking for schema output made every reply clean.
- Redrawing after every answer felt chaotic. We moved to rounds: everyone gives input, the board redraws once.

## Accomplishments that we're proud of
- On Nemotron 3 Ultra a full plan takes well under a minute end to end (measured 20 Oct: map 14.5 to 16.5 s, a round 3.5 s, 8 screens 18.5 s, the full plan 11 s).
- Real testers on the in-app feedback board filed 21 reports; every one was fixed and redeployed.
- A non-technical founder (Sravani, CustomDenimFit) planned her product with it and found decisions she had never thought about.

## What we learned
The plan matters more than the code. When the team puts its effort into planning, agents build better, with far fewer bugs.

## What's next for BuildingBees
- Bring your own AI: run the bees on the team's own Claude, Codex, Antigravity or NVIDIA coding agents.
- Plug in the team's git repo, so the plan starts from the real architecture.
- Superintelligence as a service for product owners: experts give a few focused hours a day for a week of planning, get paid properly, and agents build from what they decided.

## Built with
nvidia-nemotron, nebius-token-factory, tavily, python, fastapi, pydantic, google-cloud-run, firestore, javascript, mcp
