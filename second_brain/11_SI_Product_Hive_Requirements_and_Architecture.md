# 11. SI-Product: The Super Intelligent Product Management Hive (Master Requirements)

> **Document Status**: Requirements Baseline (Gamified Multi-Agent Hive)  
> **Tags**: #hive #multi-agent #bees #gamification #si-product #requirements  
> **Parent**: [[00_Map_of_Content]]

---

## 🐝 1. The Core Paradigm: The Super Intelligent Hive

Instead of another boring spreadsheet, PRD doc, or static diagramming board, **SI-Product is a gamified, multi-agent product management Hive**.

Software is not built by a single generic AI model. It is designed, debated, and verified by a **swarm of specialized AI Bees** who collaborate with human players (or a solo founder wearing multiple hats) to turn a raw idea into bulletproof, buildable architecture.

```
                    👑 [Queen Bee: Lead PM Orchestrator]
                                      │
     ┌──────────────────┬─────────────┴─────────────┬──────────────────┐
     ▼                  ▼                           ▼                  ▼
🎨 [Designer Bee]  💻 [Frontend Bee]           ⚙️ [Backend Bee]  🧪 [Tester Bee]
UI & Visuals       States, DOM, CTAs          APIs, Idempotency  Test Cases & Gherkin
     │                  │                           │                  │
     ▼                  ▼                           ▼                  ▼
[Design Input Box] [Frontend Input Box]      [Backend Input Box] [QA / Test Box]
     │                  │                           │                  │
     └──────────────────┴─────────────┬─────────────┴──────────────────┘
                                      │
                                      ▼
             🎮 [The "Question, Answer & Improve" Loop]
                   (Node Readiness Scores: 0% ➔ 100%)
                                      │
                                      ▼
             👾 [Handover to the "Final Boss": Coding Agent]
```

---

## 👥 2. Upfront Stakeholder Onboarding (The Player Roster)

Before generating specs, the Hive maps the human players and organizational context:

### A. Team Mode
- The Lead registers the players:
  - **Frontend Player**: e.g., `@alex (React / TypeScript)`
  - **Backend Player**: e.g., `@anuroop (Python / FastAPI / Postgres)`
  - **Designer Player**: e.g., `@sarah (UI/UX / Design Tokens)`
  - **QA / Tester Player**: e.g., `@david (Automated Testing / Playwright)`
- Each Bee directs questions specifically to the assigned player in their domain.

### B. Solo Founder Mode ("Virtual Co-Founders")
- If the user is a solo founder, the Bees act as their **virtual C-Suite and department heads**.
- The Bees prompt the founder sequentially: *"Now putting on your Backend hat: how should we handle vendor timeouts?"*

### C. Team Ground Rules
- Players define global engineering rules that all Bees must enforce:
  - *e.g., "All mutating APIs must have an X-Idempotency-Key header."*
  - *e.g., "Mobile-first responsive layout; no desktop-only screens."*
  - *e.g., "Zero client-side secrets; auth handled via Google Firebase."*

---

## 🐝 3. The Specialist Bee Swarm

Each Bee is an autonomous domain specialist that analyzes the graph, drops comments ("pollen dots"), and interrogates human players:

| Bee Specialist | Domain Responsibility | Key Confirmation & Edge-Case Questions |
| :--- | :--- | :--- |
| 👑 **Queen Bee (PM)** | Overall scope, user flow sequencing, business goals, readiness scoring | *"Is marketing consent required before proceeding to checkout?"* *"Can users buy as guest without password?"* |
| 💻 **Frontend Bee** | Component tree, UI states (Loading/Empty/Error), CTAs, form retention | *"While serviceability is calculating, what shows on screen?"* *"If PIN is invalid, which fields stay filled?"* |
| ⚙️ **Backend Bee** | Endpoints, payload schemas, third-party vendor SLAs, idempotency, fallback routes | *"If Shiprocket times out (>3s), do we block checkout or fallback to manual review?"* *"Is pricing quote cached?"* |
| 🎨 **Designer Bee** | Layout hierarchy, CTA visual affordance, spacing, dark/light contrast | *"Does this primary CTA have clear visual contrast over the secondary cancel action?"* |
| 🧪 **Tester Bee** | Acceptance criteria, edge cases, failure scenarios, Gherkin BDD specs | *"Generates 5 automated test cases: Case 1: Happy path; Case 2: Expired coupon; Case 3: Network drop mid-payment."* |

---

## 🎮 4. The Gamified "Question, Answer, and Improve" Loop

The product development process is structured as an interactive improvement game:

1. **Bees Drop Pollen Dots**: Specialist Bees land on nodes (Screens, CTAs, APIs) and flag gaps with color-coded dot badges.
2. **Confirmation & Input Boxes**:
   - Each node contains dedicated department tabs: `[Frontend Input]`, `[Backend Input]`, `[Design Input]`, `[QA Input]`.
   - Bees present single-click confirmation options or short structured inputs.
3. **Clarity Score & Level-Ups**:
   - Unclarified node: **Level 1 (Draft, 20% XP)** 🔴
   - Questioned by Bees: **Level 2 (In Review, 50% XP)** 🟡
   - Answered & Confirmed: **Level 3 (Verified, 85% XP)** 🔵
   - Visual Screen + QA Tests Passed: **Level 4 (Build Ready, 100% XP)** 🟢
4. **The Stop Rule**: A branch cannot be tackled by the coding agent until all blocking Bee questions are answered.

---

## 👾 5. Stage 4 & Stage 5 Handover to "The Final Boss"

### Stage 4: Visual Screen Synthesis
- Designer Bee synthesizes the live rendered UI mockups directly on the canvas.
- Players review the actual visual screen, click through buttons to test state transitions, and give final visual approval.

### Stage 5: Handover to the "Final Boss" (Autonomous Coding Agent)
- Once the entire branch hits 100% readiness and all Bees have signed off:
  - The Queen Bee compiles the **Unified Spec Package** (Frontend DOM structure, Backend API payloads, Visual UI layout, Tester Bee's test cases).
  - The package is dispatched to the coding model (Google Antigravity, Claude Code, or Codex).
  - The coding agent writes **100% deterministic code** that immediately passes all generated test cases on the first run.
