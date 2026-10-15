# Deep research prompts for Gemini (BuildingBees)

Paste one prompt at a time into Gemini Deep Research (Pro). When a report is done, export it (Google Doc or copy the text) and drop it in `docs/research/` with the number in the file name, for example `01-pm-question-bank.md`. I will turn each one into product changes.

Order of value: 1, 2, 3 first (they change what the bees ask). 4 and 5 shape the UI. 6 helps the demo video.

---

## 1. How product managers ask questions at each stage (the bees' question bank)

```
I am building an AI product manager that interviews a founder about a product idea before anything is designed or built. I need a research-backed question bank.

Research how experienced product managers ask questions at each stage of a product's life, both to their own team (design, engineering, QA, data) and to stakeholders (founders, executives, sales, support, legal, customers). Use sources such as product management books and courses (for example Marty Cagan, Teresa Torres, Lenny Rachitsky, Shreyas Doshi, Intercom, Basecamp Shape Up, Amazon working backwards), public PRD and spec templates from well-known companies, and practitioner posts.

Stages: idea and discovery; problem definition and scope; user flows and requirements; design; technical design and build; testing and quality; launch; after launch (measuring and iterating).

For each stage give:
1. The 10 to 15 most important questions, written the way a PM would actually say them out loud.
2. Who each question is for (team or stakeholder, and which role).
3. Why it matters: what goes wrong in real projects when it is not asked.
4. What a vague or evasive answer to it sounds like, and the sharper follow-up question a good PM asks next.
5. Which of these areas it belongs to: product and scope, user experience and design, frontend and screen states, backend and data and integrations, testing and edge cases, privacy and legal and compliance.

End with: the 25 questions that most often prevent rework or production incidents, ranked, with one sentence each on why.

Format: a table per stage, then the ranked list. Cite sources inline.
```

## 2. The decisions specs leave out

```
Research what decisions are most often missing or left implicit in product requirement documents, user stories and one-line product ideas, and later cause rework, bugs, security or privacy incidents, or missed launches.

Look at engineering post-mortems, studies on requirements engineering and requirement defects, QA and edge-case checklists, non-functional requirement lists, accessibility and privacy compliance guides, and practitioner writing on "what the spec forgot".

Give:
1. A taxonomy of commonly missing decisions (for example: empty, loading and error states; failure and retry behaviour; timeouts; concurrency such as two people booking the same slot; permissions and roles; data retention and consent; notifications; payments and refunds; limits and abuse; offline; internationalisation; accessibility; analytics and success metrics).
2. For each category: 3 to 5 concrete example questions that would surface it, and a short real-world example of it going wrong if one exists.
3. Which categories matter most for a typical consumer app versus an internal business tool.
4. How to tell, from a short product description, which categories are most likely relevant (simple signals or keywords).

Format: tables, then a short checklist. Cite sources.
```

## 3. Competitor analysis: AI tools that turn ideas into specs, flows or screens

```
Do a competitor analysis of AI tools that turn a product idea or prompt into product artefacts: user flows, diagrams, wireframes, screens, PRDs or working prototypes.

Include at least: Google Stitch, Figma Make (and Figma AI), v0 by Vercel, Lovable, Bolt.new, Uizard, Visily, Relume, Whimsical AI, Miro AI, FigJam AI, Archify (archify.si), ChatPRD, Notion AI for PRDs, Eraser.io, tldraw make-real, and any newer 2026 entrants with traction.

For each tool:
1. What it produces, from what input, and who it is for.
2. Whether it asks the user clarifying questions before generating, and how (none, one-shot form, chat, structured interview). This matters most to us.
3. How the user edits or refines the output afterwards.
4. Canvas or board experience: infinite canvas, flows, connectors, how AI changes appear on the canvas.
5. Pricing and free tier.
6. Traction signals (users, funding, reviews) and the most common complaints in reviews, Reddit, X and Product Hunt.

Then:
- A comparison table across all tools.
- The gaps nobody fills well, especially "the tool guesses instead of asking".
- Positioning advice for a product whose core idea is "Other tools guess. We ask": a team of AI product roles (product, design, frontend, backend, testing, compliance) that interviews the founder, draws user flows first, then screens, and outputs a brief of decisions and open questions.

Cite sources.
```

## 4. How to ask good questions and catch vague answers

```
Research question design and elicitation techniques used in product discovery, requirements engineering, user research and consulting, and how to apply them in an AI interviewer that asks a founder about their product idea.

Cover: Socratic questioning, the five whys, jobs to be done interviews, The Mom Test, assumption mapping, pre-mortems, laddering, requirements elicitation research, and how good interviewers detect and handle vague, evasive, contradictory or "it depends" answers.

Give:
1. Principles for writing one clear question at a time (length, wording, offering suggested answers, avoiding leading questions).
2. A catalogue of vague-answer patterns (for example "whatever is normal", "everyone", "later", "make it good", restating the question) and the best follow-up for each.
3. How to order questions so the most decision-critical ones come first, and when to stop asking.
4. How to keep the person engaged and not interrogated: tone, pacing, showing progress, giving defaults.
5. Examples of excellent question sequences for a simple consumer app idea.

Format: principles, a table of vague patterns and follow-ups, then examples. Cite sources.
```

## 5. Best-in-class infinite canvas UX

```
Research the user experience patterns of the best infinite-canvas and whiteboard tools in 2025 and 2026: Figma, FigJam, Excalidraw, tldraw, Miro, Whimsical, Google Stitch, Eraser, and Apple Freeform.

Focus on:
1. Layout of the controls around the canvas: toolbars, side rails, floating panels, what is icon-only and when labels are shown, tooltip behaviour.
2. Navigation: pan, zoom, fit to screen, minimaps, keyboard shortcuts, trackpad and touch gestures.
3. How AI features appear on the canvas: prompt boxes, AI-generated nodes appearing, showing what changed, undo.
4. Motion: how new elements enter, how connectors are drawn, transition timings and easing.
5. First-run onboarding for people who have never used a canvas tool.
6. Accessibility of canvas apps (keyboard use, screen readers).
7. Mobile and tablet behaviour.

Give concrete, implementable specs where you can find them (sizes, timings, placements) and name the source. End with the top 15 patterns a new canvas product should copy and 5 it should avoid.
```

## 6. What wins AI hackathons and makes a strong 3 minute demo

```
Research what winning entries in large AI hackathons look like, especially Google Cloud and Gemini hackathons, Devpost hackathons sponsored by NVIDIA or cloud providers, and similar 2024 to 2026 events. Look at winner galleries, judges' write-ups and judging criteria.

Give:
1. Patterns that separate winners from the rest (problem framing, technical depth, use of the sponsor's technology, polish, demo quality).
2. The structure of strong 3 minute demo videos: the first 15 seconds, how much is problem versus product, how technology is shown, the ending.
3. Common mistakes that sink otherwise good entries.
4. How judges weigh "uses the sponsor's AI deeply" versus "nice UI".
5. A checklist for a submission package: description, video, deck, repo README, live demo.

Cite examples of specific winning projects.
```
