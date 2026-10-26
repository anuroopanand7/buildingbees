# Demo video: script and storyboard (rewritten 18 Oct 2026)

**Length: 3:30 to 3:50.** The organisers ask for "at least 3 to four minutes" (Ask the Expert, 15 Oct, 4:41). Speak loud and close to the mic: in an earlier hackathon low-volume videos lost points (32:39). Record the live site in Chrome at 1440 by 900, zoom 100%, signed out (the demo is open). Use the "Just me" mode.

**Before you record (10 minutes):**
1. Open the live link in a fresh Chrome window, clear the board (menu, New spec).
2. Open a second tab already showing a finished board (in case Gemini is slow: the expert suggests keeping a ready tab, 39:22). Ready board: `?board=smoke-plan2-18oct` (the Pune tuition centre).
3. Close every other tab and notification. Phone on silent.

| Time | On screen | Say (word for word, about 140 words a minute) |
|---|---|---|
| 0:00 to 0:25 | Your face or the start screen | "I'm Anuroop. As a consultant, I suggested to one of my clients that we build his whole product with an AI agent. I learned fast that agents only go straight when the plan has no gaps. So for seven days I ran a ritual: Codex drew the user flows on a Figma board and left questions for every role, the team commented by day, and every evening I fed it all back and redrew. After a week, an agent could build it without guessing. BuildingBees is that ritual, on one board, in hours." |
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

---

## Version recorded on 18 Oct: Roger on camera, then Sravani demos her own idea

**Roger, on camera (0:00 to 0:30):** the story above, then the hand-off: "Sravani is a real founder, and we tested BuildingBees on her idea for custom-fit jeans. Over to her."

**Sravani, screen recording with her voice (0:30 to 3:30).** Live link in a fresh Chrome window at 1440 by 900; backup tab with her finished board: `?board=bf641be7-0d69-49f2-b2ff-95507c482003`.

| Time | Do | Say |
|---|---|---|
| 0:30 | Start screen | "Hi, I'm Sravani. I'm building CustomDenimFit, jeans made to your body. I'm not technical, so I tried BuildingBees to plan it before anyone builds it. I pick Just me and write my idea the way I'd tell a friend." |
| 0:40 | Type the idea, press Map it | Type: "Custom-fit jeans: customers take a short body shape quiz, enter their waist, thigh and hip, choose the fabric and the rise, see a preview, and pay. We make the jeans to fit." Say: "And I press Map it." |
| 0:55 | The board appears | "Instead of jumping to screens, it draws my user flows first, step by step. Look, it already split the flow: if my measurements are outside what we can make, the customer sees a fit warning and can try again. At the top is my feature list, F1, F2, F3." |
| 1:20 | The question set | "Now the bees ask me questions, but only things I have to decide, six in this round. This one asks what happens if the jeans don't fit when they arrive. Honestly, I hadn't thought about that. I pick one free remake. If I'm not sure, I can press Decide for me and it takes the recommended answer." Answer two, then press Decide the rest for me. |
| 1:50 | Tap the Enter measurements card | "Every card has its own thread, like comments in Figma. I can answer the bees here, or add my own note. I'll add: customers should see a short video on how to measure." Press Add note. |
| 2:10 | Point at the tray, press Update the board | "Nothing changes until I say so. When I'm ready, I press Update the board, and it redraws everything in one go. My changes are marked From your answer." |
| 2:30 | Draw the screens | "Once my flows are agreed, it draws the screens. Not pretty pictures: what each screen shows, every button, and what happens behind it. Exactly what a developer needs." |
| 2:55 | Open the Brief, scroll the Plan check, press Share as a web page | "And this is my plan. A check at the top tells me what still needs a decision. Then user stories, features, a build order, and every decision I made. I can share it as one web page with my developer, or give it to an AI coding agent. For the first time, I know exactly what I'm asking someone to build." |
| 3:20 | Back to the board | "That's how I planned CustomDenimFit with BuildingBees." |

**Close (Roger or Sravani, 3:20 to 3:40):** the "Under the hood" lines above.

**If the map is slow:** keep talking ("it's reading my idea and drawing the flows"), or switch to the backup tab and carry on.
