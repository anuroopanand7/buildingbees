# 09. Registration Copy — Founder Persona (Anuroop Style)

> **Tags**: #registration #founder-persona #human-tone #hackathon
> **Parent**: [[00_Map_of_Content]]

---

## 🟢 Track 1: Google Cloud AI Builder Cup 2026 (Hack2skill)

### Project Name:
`BuildingBees`

### Tagline / One-liner (Under 100 chars):
`the shared product map your team fills in and your agents build from`

### Problem Statement (What problem are you solving?):
`AI makes prototypes in 20 seconds now, but deciding what to actually build is still broken. PRDs are vague and Figma just shows boxes and colors without any backend logic. When a spec misses an edgecase, agents dont stop—they just guess confidently and write buggy code. Then PRD, Figma and repo drift apart in two weeks.`

### Solution Description (Tell us about your solution):
`We built a clickable information architecture board that replaces PRDs as the actual source of truth for agents. It opens level by level: User -> Flow -> Screen -> CTA -> API -> backend logic. 

The core thing is what we call connective tissue: CTAs link directly to APIs and define where to go on success or failure, plus what form inputs to keep. We run an AI question engine on top of Gemini 2.0 that interviews the team on edge cases like vendor timeouts and idempotency. If there is an open question, the agent has a strict rule: assumption is not approval. It stops and asks the PM or engineer instead of guessing, so the agent only builds verified branches.`

### Technologies Used:
`Google Gemini 2.0 Pro, Google Cloud Run, Firebase, Python, React, FastMCP`

---

## 🟢 Track 2: Nebius x NVIDIA Global AI Hackathon (Devpost)

### Project Title:
`BuildingBees: Agentic IA Board with NeMo Guardrails`

### Short Description / Elevator Pitch:
`An agentic architecture board that replaces PRDs. Uses NeMo guardrails to stop coding agents from guessing missing specs, plus cuGraph for instant dependency blast-radius analysis.`

### What it does:
`Most coding agents fail in production because specs leave out backend edge cases and the agent assumes things on its own. 

BuildingBees turns requirements into a typed dependency graph. Every screen CTA connects to APIs and error paths. We use NeMo Guardrails to enforce a simple stop-rule: 'assumption is not approval'. When an agent hits an unclear spec, it pauses, flags a blocking question for the backend lead, and works on another branch. We also use cuGraph so whenever someone touches an API contract, it instantly calculates the blast radius across every screen and flow in less than a millisecond.`

### How we built it:
`Built with Python, FastMCP for IDE agent connections, NVIDIA NeMo Guardrails to block unauthorized business assumptions, cuGraph for GPU graph traversal, and an interactive zoomable canvas.`
