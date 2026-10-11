# Nebius x NVIDIA Global AI Hackathon: Devpost entry draft

Deadline: 30 Oct 2026, 10:00 am PDT (10:30 pm IST). Everything here describes the product as it runs today.

## Form fields

- **Project name:** BuildingBees
- **Tagline:** Other tools guess what you meant. BuildingBees asks.
- **Track:** Best Apps and Agents
- **Bonus prize:** Best Use of Tavily
- **Working demo:** https://buildingbees-853213660594.asia-south1.run.app (choose "NVIDIA Nemotron" on the start screen)
- **Code:** https://github.com/anuroopanand7/buildingbees (MIT licence, shown at the top of the repository)
- **Video:** public YouTube link, 3 minutes or less (script in `02_VIDEO_SCRIPT.md`)
- **Built with:** NVIDIA Nemotron 3 Super, NVIDIA Nemotron 3 Ultra, Nebius Token Factory, Tavily, Python, FastAPI, Pydantic

## Inspiration

AI can turn one sentence into screens, diagrams or code. But one sentence leaves most decisions out, so the tool guesses: who the user is, what happens on a failure, which data is kept. The guesses look finished, so nobody questions them until they are in production.

A good product manager does the opposite. They draw the flow first and ask about every step before anyone designs a screen. I wanted a tool that behaves like that team, for founders who do not have one.

## What it does

1. You say what you want to build, in two lines.
2. A Scout Bee searches the web with Tavily for how products like yours work and where they go wrong.
3. Nemotron draws the user flows. No screens yet.
4. Six bees, each owning one part of the product (scope, design, frontend, backend, edge cases, compliance), ask what your idea leaves out, one question at a time. Questions that came from the research show their source.
5. Nemotron reads every answer. A vague answer ("whatever is normal") is not accepted: the bee asks again, more precisely. A clear answer redraws the board in about two seconds, and the bee says what it changed.
6. When the flows are agreed, Nemotron draws the screens: wireframes, buttons, the API behind each button, and the data model. The bees ask again, screen by screen.
7. You get a Brief: every decision, every source, and everything still undecided marked NOT DECIDED. One link for engineers or a coding agent.

A screen is "ready to build" only when nothing on it is left to guess.

## How I built it, and how it uses Nemotron on Token Factory

Every model call runs on NVIDIA Nemotron 3 through Nebius Token Factory's OpenAI-compatible API. Two models share the work, following the track's advice to keep the big model for the hard job:

| Job | Model | Measured |
|---|---|---|
| Draw the flows and ask the first questions | Nemotron 3 Super | about 10 s, including the Tavily search |
| Read each answer and redraw the board | Nemotron 3 Super | about 2 s |
| Draw every screen, button, API and data entity | Nemotron 3 Ultra | about 8 s |

- **Structured output without a structured-output API.** Each call carries a JSON Schema generated from Pydantic models. The reply is validated; if it fails, the error goes back to Nemotron once and it corrects itself.
- **Thinking off.** With reasoning on, Nemotron 3 spent its whole token budget thinking and returned cut-off JSON. Turning it off (`enable_thinking: false`) took the flows call from a failure after two minutes to valid JSON in six seconds.
- **Guesses are removed in code, not trusted to the prompt.** If Nemotron fills in a vendor or a timeout that appears nowhere in what the founder wrote or answered, the server blanks it and a bee asks about it.
- **Token Factory's speed is the product.** An interview only works if the reply after each answer is quick. Two seconds feels like a colleague.

The board is a graph (users, flows, screens, buttons, APIs, questions) in Python with FastAPI. The web app is one HTML file with no build step.

## How it uses Tavily

One Tavily search runs before the first question. The pages go to Nemotron as untrusted reference text with three rules: use them only to ask sharper questions, never draw a flow from them, never treat them as the founder's decision. In a test on "an app to book a haircut", the research produced questions about deposits for no-shows and limits on a stylist's daily bookings, each linked to the page it came from. The Brief lists every page read.

This is the difference between a bee asking "what about payments?" and a bee asking "salons often take a deposit to cut no-shows: do we?".

## Challenges

- Getting a model to say "that is too vague" instead of politely accepting any answer.
- Stopping the model from adding flows nobody asked for (sign-in, admin, refunds). It now has to ask whether they are wanted.
- Nemotron's reasoning eating the output budget, described above.

## What I am proud of

- It refuses to guess, and you can see it refuse.
- The same product runs on two engines behind one set of schemas.
- 30 automated tests, including one that proves web research never becomes a decision.

## What is next

- Hand the Brief straight to a coding agent and let the bees review what it builds.
- Team boards, so a real PM, designer and engineer can answer their own bee.

## What is real, and what is not

Real: everything above, live on the demo link. Not built: accounts, shared editing. The six bees are roles inside one model call, not six separate agents.

## New or existing project

Built for hackathons in October 2026. The NVIDIA Nemotron engine on Token Factory, the two-model split, the Tavily Scout Bee and source citations were all built during this hackathon's submission period.
