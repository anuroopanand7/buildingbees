# Deck outline, 12 slides (17 Oct 2026)

From Gemini's outline, with every number checked against what we can show. Build it on the organisers' template.

1. **Title.** (Built 17 Oct as `deck.html` in the organisers' template slide order; PDF in this folder, source in `founder skills/buildingbees/source/2026-10-17-ai-builder-cup-deck/`.)
    BuildingBees: agentic product planning on Google Gemini and Cloud Run. "Other tools guess. We ask." Screenshot of the canvas with the stage bar and engine pill. Live URL, GitHub.
2. **Problem.** One-prompt tools (v0, Lovable, Stitch) jump to screens and guess the business logic. Requirement omissions are a large share of defects and cost far more to fix after release [use only figures with a source we can cite]. Agencies on fixed-price work pay for the guesses out of their margin.
3. **Solution.** Six AI bees (product, design, frontend, backend, testing, compliance) interview the founder or team first. Flows with decision splits, undecided paths shown, not guessed. Standard details become visible defaults; deferred items become "out of scope for v1".
4. **Demo.** Four stages: Idea, Flows, Screens, Brief. Annotated screenshots: vague answer and follow-up; Decide for me; screens with APIs; the Brief with who answered, defaults, out of scope, sign-off.
5. **Gemini usage.** Structured output validated against Pydantic schemas in three loops (draw flows, react to each answer, draw screens). A five-model Gemini fallback chain because each model has its own quota. Gemini vision maps a photo of a whiteboard sketch. Guards in Python strip values nobody stated.
6. **Architecture.** Browser canvas, FastAPI on Cloud Run, Gemini adapter, graph engine and Brief writer, Firestore (boards, feedback), Firebase sign-in, Tavily for the Scout Bee. Quality check script runs sample ideas after every prompt change.
7. **Market.** Beachhead: software agencies and dev shops of 20 to 150 people, especially Indian agencies on fixed-price work for overseas clients. Next: in-house B2B SaaS product teams. Why we win: roadmap tools record, canvases are blank, PRD writers do not draw flows or route questions by role.
8. **Traction.** Engineer tester (Anirudh Ponna): 70+ questions on an early version, now 9 on the same idea. Founder tester (Sravani Marpu) scoped her CustomDenimFit idea; her request (several answers at once) shipped the next day. In-app feedback board: 5 reports on 16 Oct, all fixed on 17 Oct.
9. **Business model.** Free solo tier; agency plan per creator per month (about Rs 1,999 or $39, invoice or UPI); enterprise with compliance question banks [pricing is a plan, not tested].
10. **Roadmap.** Now: everything in the demo. Next 30 days: a check bee that verifies screens against the decisions, B2B question banks (SSO, roles, audit logs, DPDP), an effort estimate for agencies. Then: export to coding agents (Claude Code, Cursor, Jules), Jira or Linear.
11. **Team.** Anuroop Anand Perli (founder, product). Anirudh Ponna (engineering feedback). Built with Claude Code; research with Gemini Deep Research.
12. **Ask and links.** Judges: press "Try a sample in one click", no sign-in needed. Looking for 5 agencies to pilot their next client discovery. Live URL, GitHub, video, Google Cloud project id.
