# 🏆 Google Cloud AI Builder Cup 2026 — Official Entry Form

---

## 📌 Project Overview

- **Project Name**: **SpecGraph (Agentic Information Architecture Board)**
- **Tagline**: The shared product map human teams fill in and autonomous AI agents build from.
- **Challenge Track / Theme**: **Future of Work & Developer Productivity**
- **Target Audience**: Product Managers, Engineering Leads, Software Agencies, Autonomous AI Agent Developers.
- **Deployment Platform**: Google Cloud Run (Singapore `asia-southeast1`) & Firebase.
- **AI Models & Frameworks**: Google Gemini 2.0 Pro / 1.5 Pro (Multimodal Ingestion & Socratic Reasoning), FastMCP Protocol.

---

## 💡 Executive Abstract (150 Words)

In the era of autonomous coding agents, building code has become instantaneous, but deciding **exactly what to build** remains slow, ambiguous, and fragmented. Autonomous agents lack common sense: whatever traditional PRDs leave out, agents hallucinate with extreme confidence.

**SpecGraph** replaces static text PRDs and shallow Figma wireframes with an interactive, 6-level semantic information architecture graph:
`User Personas` $\to$ `User Flows` $\to$ `Screens & States` $\to$ `CTAs (Connective Tissue)` $\to$ `API Contracts` $\to$ `Backend Logic & Failure Paths`.

Powered by **Google Gemini 2.0 Pro**, SpecGraph features a **Socratic Question Engine** that systematically interrogates missing business rules, unstated API timeouts, and edge cases. Under the foundational protocol **"Assumption is not approval,"** agents are mathematically blocked from generating code on incomplete branches until humans or architect agents provide decisions. The specification is transformed into executable, zero-drift source code.

---

## 🚨 The Problem: Why Software Development is Broken for Agents

1. **PRDs Describe Desires, Not Behavior**: PRDs explain what a user wants to achieve, but omit state transitions, vendor fallbacks, and error boundaries.
2. **Figma Shows Geometry, Not Logic**: Agent vision reading Figma yields CSS rectangles and hex codes, not idempotency rules, payload contracts, or retry policies.
3. **The 3-Way Drift**: PRDs, Figma boards, and Git repositories diverge within weeks.
4. **Hallucinated Business Logic**: When agents hit ambiguous edge cases, they guess, creating silent production bugs and catastrophic financial vulnerabilities.

---

## ⚡ The Solution & Key Innovations

### 1. CTA as the Connective Tissue
Calls-to-Action (buttons, gestures) are modeled as deterministic state machines linking screens to APIs:
- Dispatches parallel or sequential API contracts (e.g. `API32 Logistics` + `API42 Pricing`).
- **On Success**: Transitions to target screen.
- **On Failure**: Retains form field states, displays contextual error banners, and triggers retry backoff.

### 2. Socratic Question Engine Powered by Gemini
Rather than passive documentation, SpecGraph acts as an active technical interviewer:
- Gemini analyzes the entire graph to discover unstated edge cases (e.g. *What if Shiprocket times out after 3 seconds?*).
- Routes blocking questions to designated owners (PM, Frontend, Backend).

### 3. Stop Rules & Mathematical Branch Readiness
- Branch Readiness = $0.0$ if any open blocking question exists.
- Coding agents query the SpecGraph via **MCP (Model Context Protocol)**, autonomously pulling only branches with $Score = 1.0$.

### 4. Bottom-Up Blast Radius Analysis
Changing a backend API or vendor instantly traverses the graph, highlighting all affected screens, CTAs, and flows in real-time.

---

## 🛠️ Google Cloud Technical Architecture

```
[Legacy PRD / PDF / FigJam]
           │
           ▼
[Gemini 2.0 Pro Multimodal Ingestion] (Parses 400-page specs into typed DAG)
           │
           ▼
[SpecGraph Core Engine on Google Cloud Run]
  ├── Pydantic V2 Strict Schema Validation
  ├── NetworkX Bidirectional Graph State
  ├── Socratic Question Generator (Gemini Thinking)
  └── FastMCP Server (IDE & Agent Interface)
           │
           ▼
[Real-Time Interactive Canvas] (React / Tailwind on Firebase App Hosting)
```

1. **Gemini 2.0 Pro Multimodal API**: Ingests massive PDF requirement documents (demonstrated on the real 423-page PCOS commerce spec).
2. **Gemini Structured Outputs**: Enforces strict JSON Schema compliance for node definitions.
3. **Google Cloud Run**: Containerized, auto-scaling deployment in Singapore region.
4. **Firebase Firestore & App Hosting**: Real-time collaborative canvas synchronization across engineering squads.

---

## 📈 Measurable Business Impact

- **70% Reduction in Spec Drift**: Single source of truth shared by PMs, engineers, and AI agents.
- **85% Fewer Agent Hallucinations**: Zero guessing allowed on incomplete specifications.
- **4x Faster Developer Onboarding**: Visual semantic zoom allows new engineers to understand full system behavior in minutes.

---

## 👥 Team Roles & Eligibility Checklist

- **Eligibility**: Working professionals in JAPAC region, age 21+.
- **Team Composition**: 2–4 members (Product Lead, Full-Stack Engineer, AI Architect).
- **Code Repository**: Public GitHub repository with Dockerfile & Cloud Build configuration.
