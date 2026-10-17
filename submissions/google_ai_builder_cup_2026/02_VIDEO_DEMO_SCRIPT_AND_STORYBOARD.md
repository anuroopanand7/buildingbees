# Demo video: script and storyboard (rewritten 18 Oct 2026)

**Length: 3:30 to 3:50.** The organisers ask for "at least 3 to four minutes" (Ask the Expert, 15 Oct, 4:41). Speak loud and close to the mic: in an earlier hackathon low-volume videos lost points (32:39). Record the live site in Chrome at 1440 by 900, zoom 100%, signed out (the demo is open). Use the "Just me" mode.

**Before you record (10 minutes):**
1. Open the live link in a fresh Chrome window, clear the board (menu, New spec).
2. Open a second tab already showing a finished board (in case Gemini is slow: the expert suggests keeping a ready tab, 39:22). Ready board: `?board=smoke-plan2-18oct` (the Pune tuition centre).
3. Close every other tab and notification. Phone on silent.

| Time | On screen | Say (word for word, about 140 words a minute) |
|---|---|---|
| 0:00 to 0:25 | Your face or the start screen | "I'm Anuroop. As a consultant, a client asked me to build his whole product with an AI agent. I learned fast that agents only go straight when the plan has no gaps. So for seven days I ran a ritual: Codex drew the user flows on a Figma board and left questions for every role, the team commented by day, and every evening I fed it all back and redrew. After a week, an agent could build it without guessing. BuildingBees is that ritual, on one board, in hours." |
| 0:25 to 0:40 | Start screen | "Other tools guess. We ask. I pick Just me, and type my idea in plain words." Type: "A tuition centre app in Pune: parents see attendance and test marks, pay monthly fees, and get a message when the child misses class." Press Map it. |
| 0:40 to 1:05 | The board appears: flows, the Features strip | "Gemini 3.1 Pro on Google Cloud's Agent Platform draws the user flows first, not screens: every step, and the splits where things can go wrong, like a failed payment. Up top, the feature list a PRD starts with: F1, F2, F3. Every flow, screen and API gets a short id that stays the same everywhere." |
| 1:05 to 1:40 | The question set in the dock | "Now the bees: product, design, frontend, backend, testing and compliance, plus a Scout Bee that read the web first. They only ask what this team must decide. Round one is six questions, and the count never grows. Look: because it's Pune, it asks how parents pay, and suggests UPI. Standard details, like loading spinners and timeouts, are not asked: they become defaults in an assumption log." Pick UPI, type one answer, press Decide the rest for me. |
| 1:40 to 2:05 | Tap a step card, its thread opens | "Every card has a thread, like comments in Figma. The bees' questions about this step are here to answer, and I can add my own note: something is missing." Type a note, Add note. Point at the tray: "Nothing on the board changes until I say so. Seven inputs, then Update the board." |
| 2:05 to 2:30 | Press Update the board: the scan band, the board redraws, "Round 1 done" | "One press, one Gemini call for the whole round, and the board redraws once. Changed steps are marked From your answer, and round two begins. On a team board, each person answers their own role, and the product owner processes the round. If two people disagree, the bees don't pick a side: they flag the misalignment for the owner." |
| 2:30 to 2:55 | Draw the screens; the screens view | "When the flows are agreed, it draws the screens, as specs, not pictures: every element, what each card holds, every button and the API behind it, and loading and error states only where they're real." |
| 2:55 to 3:25 | The Brief: Plan check at the top, Write the full plan, Share as a web page | "The Brief is the plan an agent builds from. A plan check first: what still blocks a builder. Then user stories with Given, When, Then tests, a must, should, later feature list, a build order, and every decision with who made it. I can download it, share it as one web page with no sign-in, or plug it straight into Claude Code or Cursor through our MCP server." |
| 3:25 to 3:45 | Architecture slide or the README | "Under the hood: Cloud Run, Gemini 3.1 Pro on Agent Platform with a fail-over chain across models and quotas, Firestore, Firebase sign-in, and schema validation on every Gemini reply, so nobody's guess reaches the board. Agentic product planning: humans and agents, building from a plan with no gaps. That's BuildingBees." |

**After recording:** trim the waits (keep one real wait so judges see it is live), add captions if you can, check the volume, upload to YouTube as Unlisted or Public, put the link into the deck (last slide) and the form.

**If something breaks while recording:** switch to the ready tab (`smoke-plan2-18oct`) and carry on from the board; say nothing about it.
