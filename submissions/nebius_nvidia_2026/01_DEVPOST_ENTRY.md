# Devpost entry: Nebius x NVIDIA hackathon (rewritten 27 Oct 2026)

**Deadline: 30 Oct 2026, 10:30 pm IST.** Track: Best Apps and Agents. Bonus: Best Use of Tavily.
Needs: a working demo URL, a public YouTube video of 3 minutes or less showing Token Factory and Nemotron, a public repo with a licence, this text.
Judged equally on technological implementation, design, potential impact and quality of idea.

**Demo URL (Nemotron only, no login):** https://buildingbees-nemotron-853213660594.asia-south1.run.app
**Repo:** https://github.com/anuroopanand7/buildingbees
**Video:** https://youtu.be/gzDuGUC0sPQ

---

## Project name
BuildingBees

## Tagline (one line)
Other tools guess. BuildingBees asks: six AI bees on NVIDIA Nemotron interview your team and write the docs a coding agent builds from.

## Inspiration
I work as a consultant. For one of my clients, I suggested we build the whole product with an AI agent. I learned quickly that agents only go straight when the plan has no gaps. Otherwise they assume things and guess.

So for 7 days I ran a little ritual. Codex drew the user flows on a Figma board and left questions for every role. My team commented during the day, and every evening I fed their inputs back and redrew everything. After a week the plan was so clear that an agent could build it without guessing.

Why do vibe coded products have bugs? Because the plan leaves gaps and the agent fills them with guesses. BuildingBees is that 7 day ritual on one board, in a few hours.

## What it does
You describe an idea in plain words (or upload a sketch photo), alone or with your team. Six AI bees plus a Scout interview you:

- **North** (product), **Kala** (design), **Pixel** (frontend), **Bolt** (backend), **Poke** (testing), **Shield** (compliance).
- **Scout** reads the web first with Tavily, so the questions are about real rules and real failures.

They draw user flows, then screens, buttons and APIs. They ask only what a human must decide, and write the docs a coding agent builds from.

**Questions**
- Two tiers: "Only you can decide these" and "The bees can pick these" (press Decide for me). Standard topics are never asked.
- Everyone can comment on any card. The board only changes when you press Update the board, once per round.
- Before every round and before screens, a snapshot is saved, so you can go back to an earlier point.

**For developers, built from the board with no extra model call**
- **Build prompt per screen:** paste into Cursor or Claude Code. It lists the decisions and the open questions marked "do not guess".
- **API contract panel** with example JSON, a **live mock API** at `/mock/<board>/<path>` (edit and save the mock data) and an **OpenAPI 3.0 export**.
- **TESTS.md** test plan: happy path per flow, failure scenarios, undecided gaps.
- **Database diagram** in the schema doc, and an **SVG download** of each screen.
- **Play the flow:** click through the screens like a working app, with a "What if it fails?" button.
- **What can go wrong** (key C): failure screens outlined, buttons with no failure screen dashed.
- Staff and admin screens used at a desk are tagged desktop and drawn wide.
- **Suggest an API field change:** it becomes a Backend question and is applied when approved.
- Keyboard shortcuts: P, C, N, 1, 2, 3.

**Team and agents**
- **Share with team:** a solo board becomes a team board (owner key and role links). Each teammate answers only their bee's questions.
- 6 docs plus `AGENTS.md` and a zip. **Bring your own AI over MCP:** a coding agent like Claude Code can drive the board.

**Why not just ask Claude?** A chat gives you one PRD to paste. BuildingBees keeps a shared board where each gap goes to the person who owns it, every decision is logged with who made it and when, and the coding agent gets one screen at a time with the decisions attached.

**Who it is for:** product teams and software agencies scoping fixed-price client work, and solo founders (strong for India).

## How we built it
**Models on Nebius Token Factory, routed by job**
- **Nemotron 3.5 Super VL** draws the flows from text or a sketch photo. It won our A/B test.
- **Nemotron 3 Super** reads each round of answers.
- **Nemotron 3 Ultra** draws the screens, the plan and the tech docs.
- Fallbacks between them, with a 45 s timeout on Ultra and a 60 s backup.

**Native structured output.** Every call uses Token Factory's `response_format` `json_schema` (guided decoding), then Pydantic validation with one repair retry. Thinking is turned off, because Nemotron otherwise spends the token budget reasoning. The engine pill on the board shows each call's model, seconds, tokens, prefix-cache hits and cost.

**Cost control.** A daily spend guard ($1.50) is kept in Firestore.

**Talents.** Each bee has talents, and a skill is wired into prompts only if an A/B test shows it moves a number. Shield's India pack (DPDP consent and GST) is added automatically for Indian ideas. Three other drafted skills showed no gain and stay off.

**Rest of the stack**
- Tavily for Scout: one search per new board, shown as sources, never counted as a decision.
- FastAPI on Google Cloud Run (scales to zero), Firestore for boards, a single-page canvas UI in plain JavaScript.
- Guardrails in Python: vendors, timeouts and limits nobody stated are removed and turned into questions.
- An MCP server (`scripts/mcp_server.py`) for coding agents.
- 80 automated tests on fake engines, so no model calls in CI.

## Challenges we ran into
- Our first version asked one tester 70+ questions. He called it "a never-ending Google form". We rebuilt the question rules. On Nemotron, 4 fixed ideas now give 12.0 questions per idea, with 0 on standard topics and 0 near-duplicates (`scripts/eval_questions.py`).
- With thinking on, Nemotron spent all its tokens reasoning and the JSON got cut off. Thinking off plus native schema output made every reply clean.
- One model was not best at everything. We ran A/B tests and routed by job: Super VL for flows, Super for rounds, Ultra for screens and docs.
- Redrawing after every answer felt chaotic. We moved to rounds: everyone gives input, the board redraws once.

## Accomplishments that we're proud of
- Live timings measured 27 Oct: the map takes about 10 s of model time (about 35 s on a cold start with web research), a round update 4 s, screens 11 to 16 s, docs about 15 s, the plan about 8 s.
- Real testers filed 21 reports on the in-app feedback board, and a teammate's two written reviews became most of the developer features listed above.
- A non-technical founder (Sravani, CustomDenimFit) planned her product with it and found decisions she had never thought about.
- Built from 9 Oct 2026, inside the submission period.

## What we learned
The plan matters more than the code. When the team puts its effort into planning, agents build better, with far fewer bugs. And a skill or model is worth wiring in only if a measured test says so.

## What's next for BuildingBees
- Plug in the team's git repo, so the plan starts from the real architecture.
- More country packs for Shield, after the India pack.
- Experts give a few focused hours a day for a week of planning, get paid properly, and agents build from what they decided.

## Built with
nvidia-nemotron, nebius-token-factory, tavily, python, fastapi, pydantic, google-cloud-run, firestore, javascript, mcp
