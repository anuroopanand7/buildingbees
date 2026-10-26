# Video script: Nebius x NVIDIA (rewritten 27 Oct 2026)

**Length: under 3:00 (hard limit).** Target 2:50. Public YouTube. Must show **Token Factory** and **Nemotron**.
Record on the Nemotron-only link: https://buildingbees-nemotron-853213660594.asia-south1.run.app (Chrome, 1440 by 900, zoom 100%).

**Sample idea (paste it):** "A tiffin delivery service in Pune: home cooks list daily meals, office workers order by 10 am and pay by UPI, a rider delivers at lunch."

**Before recording (so there are no dead waits):**
- Tab 1: the demo. Tab 2: https://tokenfactory.nebius.com usage page (key hidden). Tab 3: Claude Code open in a terminal.
- Do one dry run and keep that board as backup. Model times: map about 10 s (about 35 s cold), round 4 s, screens 11 to 16 s, docs about 15 s. Cut the waits in the edit, or talk over them.
- Warm the service once before you hit record, so the map is not a cold start.

Narration is about 330 words. Silent screen moments are marked.

| Time | On screen (exact clicks) | Say |
|---|---|---|
| 0:00 to 0:12 | Start screen. Big tagline visible. | "Other tools guess. BuildingBees asks. Six AI bees interview your team, and write the docs a coding agent builds from. Everything runs on NVIDIA Nemotron, through Nebius Token Factory." |
| 0:12 to 0:30 | Pick Just me. Paste the tiffin idea. Click Map it. Silent while it loads. | "A tiffin service in Pune. Home cooks list meals, office workers order by ten, pay by UPI, a rider delivers. Scout reads the web with Tavily, and Nemotron 3.5 Super VL draws the user flows. That model won our A/B test for flows." |
| 0:30 to 0:42 | Board appears. Point at the flows, then the engine pill. | "About ten seconds of model time. Every reply uses Token Factory's native JSON schema output, so it is valid before it touches the board." |
| 0:42 to 1:05 | Open the question panel. Show the two tiers. Answer two questions. Click Decide for me. | "Six bees ask only what a human must decide. These are for me only: UPI or cash on delivery, what happens if a cook cancels. These the bees can pick. Decide for me." |
| 1:05 to 1:15 | Click Update the board. | "One press, one Nemotron 3 Super call reads the whole round. Four seconds." |
| 1:15 to 1:30 | Click Draw the screens. Show the cook's kitchen screen drawn wide with the desktop tag. | "Now Nemotron 3 Ultra draws the screens. The cook's kitchen screen is used at a desk, so it is tagged desktop and drawn wide." |
| 1:30 to 1:45 | Press C. Failure screens outline; dashed buttons show. | "Press C: what can go wrong. Outlined screens handle a failure. Dashed buttons have none. These are the gaps an agent would guess at." |
| 1:45 to 2:00 | Press P. Click through order, pay. Click What if it fails? | "Press P to play the flow like a working app. And What if it fails? shows the payment failing." |
| 2:00 to 2:20 | Open the order API. Show example JSON. Switch to a browser tab with `/mock/<board>/<path>` returning JSON. Click the OpenAPI download. | "Each API has a contract. This URL is a live mock, so a frontend can build today. Or download OpenAPI." |
| 2:20 to 2:35 | Click Copy build prompt on one screen. Switch to Claude Code, paste. Silent. | "Copy build prompt gives a coding agent one screen at a time, with decisions attached, and open questions marked do not guess." |
| 2:35 to 2:45 | Back to the board. Click Share with team. Show the role links. | "Share with team: each teammate answers only their bee's questions, and every decision is logged with who and when." |
| 2:45 to 2:55 | Zoom on the engine pill: model, seconds, tokens, cache hits, cost. Then the Token Factory usage tab. Show the GitHub link on screen. | "The pill shows every call: model, seconds, tokens, cache hits, cost. Open source at github.com/anuroopanand7/buildingbees. BuildingBees asks, so agents don't guess." |

**Tips**
- A chat gives one PRD. This is a shared board where each gap goes to its owner. Show that in the Share beat if you have a spare second.
- If the screens call runs long, record it once and speed up that stretch in the edit.
- Do not add an intro slide. The tagline is the hook.

**After recording:** check the length is under 3:00, check the volume, upload as Public, add the link to `01_DEVPOST_ENTRY.md`.
