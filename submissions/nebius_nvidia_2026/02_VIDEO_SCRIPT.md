# Video script: Nebius x NVIDIA Global AI Hackathon (final, 28 Oct 2026)

**Hard limit: under 3:00.** Target 2:50. Public on YouTube. Deadline: Fri 30 Oct, 10:30 pm IST.
It must show the app working, **Nebius Token Factory** and **NVIDIA Nemotron**.
Judged equally on: technical implementation (how well Nemotron and Token Factory are used), design, impact, idea.

Demo link (Nemotron only): https://buildingbees-nemotron-853213660594.asia-south1.run.app
Repo: https://github.com/anuroopanand7/buildingbees

---

## 1. Before you record (15 minutes)

**Computer**
- Chrome, window 1440 by 900 (or full screen on a laptop), page zoom 100%. Hide bookmarks bar (Cmd+Shift+B).
- Close Slack, WhatsApp and mail. Turn on Do Not Disturb.
- Screen recorder: QuickTime (File > New Screen Recording) or OBS. Record the mic at the same time, or record voice
  separately afterwards and lay it over (easier: you can read calmly).

**Tabs, in this order**
1. The demo link, on the start screen. Use a fresh board: add `?board=demo-30oct` to the URL.
2. A blank tab (for the live mock in beat 9).
3. tokenfactory.nebius.com, Billing > Usage (API key not visible).
4. A terminal with Claude Code open in an empty folder (for beat 10).
5. The GitHub repo page.

**Warm up (important)**
- Open the demo link once, 2 minutes before recording, and press nothing. The first load after a quiet hour is a cold
  start (about 35 s for the first map). Warm, the map takes about 10 to 15 s.
- Do one full dry run on a board called `dry-30oct`. Keep that tab: if anything is slow or odd during the real take,
  switch to the dry-run board and carry on (say nothing about it).

**The idea to paste (copy it now)**
> A tiffin delivery service in Pune: home cooks list daily meals, office workers order by 10 am and pay by UPI, a rider delivers at lunch.

**How to speak:** calm, a little slower than normal. About 150 words a minute. Silent moments are fine: let the
screen work. Never apologise for a wait; cut it in the edit.

---

## 2. Shot list and narration

Times are the finished video. "Cut" means you trim the wait in the edit.

### Beat 1 (0:00 to 0:12) Hook
**Screen:** the start screen. Do nothing for 8 seconds: the mini board on the right plays its story (the idea types
itself, three steps appear, North and Poke pin questions, "You decide").
**Say:**
> "Every AI app builder guesses what your prompt leaves out. BuildingBees asks. Six AI bees interview you, or your whole team, before a coding agent writes a line."

### Beat 2 (0:12 to 0:28) The idea goes in
**Screen:** click **Just me**. Click into the box, paste the tiffin idea. Click **Map it**. (Cut the wait.)
**Say:**
> "A tiffin service in Pune. Home cooks, office workers, UPI, a lunchtime rider. Scout reads the web first, with Tavily. Then NVIDIA Nemotron 3.5 Super VL, on Nebius Token Factory, maps the user flows."

### Beat 3 (0:28 to 0:40) The board, and proof of the model
**Screen:** the board appears. Move the mouse slowly across the flows. Hover the **engine pill** at the bottom
(it shows model, seconds, tokens, cost, "checked").
**Say:**
> "Every call uses Token Factory's native JSON schema output, so the reply is valid before it touches the board. The pill shows the model, the time, the tokens and the cost."

### Beat 4 (0:40 to 1:02) The bees ask
**Screen:** the question panel at the bottom. Point at the two groups: **Only you can decide these** and **The bees
can pick these**. Answer two questions in the first group by tapping an option. Then click **Take the bees' picks**.
Click the send button at the bottom of the set.
**Say:**
> "Six bees ask only what a human must decide. North owns scope, Bolt the backend, Shield privacy and, because this is India, GST and consent. The business calls are mine. Technical defaults, the bees can pick, and they say so."

### Beat 5 (1:02 to 1:12) Update the board
**Screen:** click **Update the board**. Watch the changed cards light up. (Cut the wait.)
**Say:**
> "One press. Nemotron 3 Super reads the whole round in about four seconds and redraws only what my answers changed."

### Beat 6 (1:12 to 1:28) Screens
**Screen:** click **Draw the screens**. (Cut the wait.) Scroll to a staff screen tagged **Desktop** (the cook's or the
rider's dashboard), drawn wide.
**Say:**
> "Now Nemotron 3 Ultra, the heavy reasoner, draws every screen, button and API from the decisions. Screens used at a desk are tagged desktop and drawn wide."

### Beat 7 (1:28 to 1:42) What can go wrong
**Screen:** press **C**. Red outlines on failure screens; dashed buttons say "No failure screen yet". Hold 3 seconds.
Press **C** again.
**Say:**
> "Press C: what can go wrong. Red is handled. Dashed is a gap, exactly where an AI agent would have guessed."

### Beat 8 (1:42 to 1:58) Play the flow
**Screen:** on the order flow, click **Play the flow** (or press **P**). Click the main button twice to move through the
screens. Then click **What if it fails?** under the pay button.
**Say:**
> "Press P to click through it like a real app. And what if the payment fails? You see that screen too, before anyone builds it."

### Beat 9 (1:58 to 2:16) The API, live
**Screen:** close the player (Esc). Click an API chip under a button (for example the order API). The side panel shows
method, path, example request and response. Click **Copy** next to the live mock address. Switch to the blank tab,
paste, press Enter: JSON appears. Come back. Open **Brief** and click **OpenAPI** (the file downloads).
**Say:**
> "Every API has a contract and a live mock. A frontend developer can call it today. And one click exports OpenAPI for Postman or Swagger."

### Beat 10 (2:16 to 2:32) Hand it to a coding agent
**Screen:** close the Brief. On one screen card click **Build prompt**. Switch to the Claude Code terminal, paste
(Cmd+V), and let the viewer read for 2 seconds. Do not run it.
**Say:**
> "Build prompt hands a coding agent one screen at a time: its buttons, its APIs, the team's decisions, and the open questions, marked do not guess."

### Beat 11 (2:32 to 2:43) The team
**Screen:** back to the board. Click **Share with team** (top right). Show the invite window with the role links.
**Say:**
> "Share with team turns this into a team board. Each person answers only their own bee's questions, and every decision is logged with who and when."

### Beat 12 (2:43 to 2:55) Close
**Screen:** zoom on the engine pill for 2 seconds, then the Token Factory usage tab, then the GitHub page.
**Say:**
> "Three Nemotron models, routed by job, on Nebius Token Factory. Open source on GitHub. Other tools guess. BuildingBees asks."

Narration is about 360 words. With the silent moments it lands near 2:50.

---

## 3. If something goes wrong during the take
| Problem | What to do |
|---|---|
| The map takes more than 20 s | Keep recording; cut it in the edit. If over 60 s, switch to the `dry-30oct` tab |
| No staff screen is tagged Desktop | Skip that sentence in beat 6, or use the dry-run board |
| No dashed buttons appear for C | Answer fewer questions before drawing screens next time; or show red outlines only |
| A question round feels long | Click **Decide the rest for me** and move on |
| There is no "The bees can pick these" group | Round 1 may hold only business calls. Tap **Decide for me** on one question instead and say "or let the bees pick" |
| An error message appears | Stop, open the dry-run board, restart that beat; cut the error out |
| You stumble on a line | Pause 2 seconds and say the sentence again; cut the first try |

---

## 4. Editing (iMovie, CapCut or DaVinci, all free)
- Cut every wait to half a second, or speed it up 4x with a small on-screen label "4x".
- Add simple captions for each spoken line (CapCut does this automatically). Many judges watch muted.
- Optional text labels, bottom left, 2 seconds each: "Nemotron 3.5 Super VL", "Nemotron 3 Super", "Nemotron 3 Ultra",
  "Nebius Token Factory".
- No intro slide and no music louder than your voice (music is optional; if used, keep it very low).
- Final check: under 3:00, voice clear, nothing private on screen (no API key, no WhatsApp, no email).

---

## 5. Upload
- **YouTube title:** BuildingBees: AI bees that ask before agents build (NVIDIA Nemotron on Nebius Token Factory)
- **Visibility:** Public. **Not** "made for kids".
- **Description (paste):**
  > BuildingBees turns an app idea into a decided plan before any code is written. Six AI bees ask your team only
  > what a human must decide, then draw flows, screens and APIs, and hand a coding agent one screen at a time.
  > Runs on NVIDIA Nemotron (3.5 Super VL, 3 Super, 3 Ultra) through Nebius Token Factory, with native structured output.
  > Live demo: https://buildingbees-nemotron-853213660594.asia-south1.run.app
  > Code: https://github.com/anuroopanand7/buildingbees
- Send the YouTube link to Claude. Claude adds it to `01_DEVPOST_ENTRY.md` and fills the Devpost form in your Chrome;
  you check it and press Submit.
