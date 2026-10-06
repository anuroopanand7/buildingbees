# 🎥 SpecGraph: 3-Minute Video Demo Script & Storyboard
### Google Cloud AI Builder Cup 2026 Submission Video

---

## ⏱️ Video Breakdown (180 Seconds Total)

| Timestamp | Visual on Screen | Voiceover / Narration |
| :--- | :--- | :--- |
| **0:00 - 0:30** | Opening slide $\to$ Frustration showing traditional 400-page PRD vs broken AI-generated code. | *"AI coding agents have made code generation fast and cheap, but deciding exactly what to build is still painfully vague. When requirements leave out an edge case, agents don't stop—they guess with confidence, introducing critical bugs into production. Meet SpecGraph: the shared product map human teams fill in, and autonomous agents build from."* |
| **0:30 - 1:00** | Interactive Canvas: Zooming from L1 User Persona $\to$ L2 Flow $\to$ L3 Screen $\to$ L4 CTA $\to$ L5 API $\to$ L6 Logic. | *"SpecGraph replaces static text PRDs with an agentic, 6-level information architecture map. Powered by Google Gemini 2.0 Pro's 2M-token context window, we ingest entire 400-page PDFs—like our live PCOS Commerce App benchmark—and compile them into strongly-typed graph nodes. Notice Level 4: Call-to-Actions are deterministic state machines connecting screen gestures directly to backend APIs."* |
| **1:00 - 1:45** | Socratic Question Engine in action $\to$ Screen W05 is highlighted RED with Readiness Score: 0.0. | *"Notice screen W05 Checkout: its readiness badge is RED (0.0). Why? Because our Socratic Question Engine, powered by Gemini Thinking, detected that backend API32 has no defined behavior if third-party vendor Shiprocket times out. Under our foundational stop-rule, 'Assumption is not approval,' the coding agent is strictly forbidden from guessing. The branch is paused, and a blocking question is routed to the Backend Lead."* |
| **1:45 - 2:15** | Clicking "Resolve with Decision" $\to$ Screen turns GREEN (Readiness 1.0) $\to$ MCP agent starts building. | *"Watch what happens when the human architect provides a decision: 'Fallback to static pincode tier lookup; allow tentative checkout.' The decision is written directly into the specification. Instantly, the readiness score jumps to 1.0 GREEN. Our MCP server notifies the waiting autonomous agent, which now builds the exact branch with zero hallucination and verified unit tests."* |
| **2:15 - 2:45** | Clicking API32 $\to$ Instant Blast Radius highlight of all upstream screens and flows. | *"What if an API contract changes next month? Click API32 to trigger our Bottom-Up Blast Radius Analyzer. Within milliseconds, SpecGraph flags every screen, CTA, and flow across the company that depends on this endpoint, preventing silent regressions before a single line of code is pushed."* |
| **2:45 - 3:00** | Google Cloud architecture diagram $\to$ Call to Action. | *"Built on Google Cloud Run, Firebase, and Gemini 2.0 Pro, SpecGraph transforms the specification into the new source code. Join us in shaping the future of autonomous software engineering."* |

---

## 🎬 Production & Recording Checklist
- [ ] Record high-resolution screen capture of the interactive canvas (`web/index.html`).
- [ ] Show both Red (Blocked) and Green (Unblocked) state transitions clearly.
- [ ] Show the FastAPI interactive swagger docs (`/docs`) and automated test run (`pytest`).
- [ ] Export in 1080p / 60fps MP4 format with crisp voiceover and subtitle captions.
