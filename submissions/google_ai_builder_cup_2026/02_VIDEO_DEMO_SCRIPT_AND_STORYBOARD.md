# Demo video script, 2:40 (17 Oct 2026)

Built from Gemini's second-by-second draft, checked against what the product really does. Every claim below is true on the live site.

**Setup:** live site in Chrome, window 1440 px wide, page zoom 110%, one tab, notifications off. Start on a new board (Menu, New spec). Rehearse once. The first map takes about 20 seconds: keep it in the video (it is real Gemini), or speed that stretch up 2x in editing and say so with a small "2x" label. Thumbnail: "BuildingBees: Other tools guess. We ask. Built with Gemini on Cloud Run".

| Time | On screen | Say |
|---|---|---|
| 0:00 to 0:08 | The start screen: "Other tools guess. We ask." | "BuildingBees is agentic product planning on Google Gemini and Cloud Run. Other tools guess. We ask." |
| 0:08 to 0:18 | Hover the "Try a sample" button | "When an agency quotes a fixed price from a one-line idea, the edge cases nobody wrote down, a double booking, a failed payment, eat the margin later." |
| 0:18 to 0:40 | Click "With my team" then "Try a sample in one click" (or type the B2B consultation idea). The flow rises in; point at the stage bar (Idea, Flows) and the engine pill (model name, seconds, schema validated) | "Gemini reads the idea and draws the user flow first, no screens yet. This pill shows which Gemini model answered and that its output passed our schema check." |
| 0:40 to 0:55 | Point at the diamond "Slot still free?" and the amber "Not decided yet" path | "Where the flow can break, it draws the split, and leaves the path nobody decided empty. That empty box is what a spec forgets." |
| 0:55 to 1:15 | Role picker: Client. Type a vague answer: "whatever is normal" | "Each teammate hears only their own bees. The client gets business questions. If an answer is vague, the bee does not accept it: it asks one sharper question." |
| 1:15 to 1:35 | Answer clearly: pick two suggestions (multi-select) and Send. The node sketches, then "From your answer" | "A clear answer redraws the board, and marks what changed." |
| 1:35 to 1:50 | Answer another with "Later, not in the first version" | "Anything we put off is logged as out of scope, so it cannot creep back in for free." |
| 1:50 to 2:05 | Menu, Change your role, Backend. Click "Draw the screens". Screens, buttons and APIs appear. Click "Flows" in the stage bar, then back | "When the flows are agreed, it draws screens, buttons and the API behind each one. You can go back to the flows any time." |
| 2:05 to 2:25 | Click "Brief" in the stage bar. Scroll: decisions with who answered, standard defaults applied, out of scope for v1. Press Sign off | "The Brief has every decision and who made it, the standard defaults it applied instead of asking, what is out of scope, and a sign-off that records who approved it and when." |
| 2:25 to 2:40 | Copy agent link. End card: live URL, GitHub, "Gemini on Cloud Run, Firestore, Firebase" | "Our first tester answered 70 questions on an early version. The same idea now takes 9. BuildingBees: other tools guess, we ask. Try the sample on our live link." |

Optional 10 seconds if time allows: upload a photo of a whiteboard sketch on the start screen; Gemini vision turns it into flows and the bees ask what it leaves out.

Do not claim: a cryptographic sign-off, sub-second answers, a fixed number of defaults, or a time from idea to brief that we have not measured.
