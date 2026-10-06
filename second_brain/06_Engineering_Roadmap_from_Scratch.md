# 06. Engineering Roadmap: Building From Scratch

> **Tags**: #roadmap #implementation #tech-stack #milestones
> **Parent**: [[00_Map_of_Content]] | **Next**: [[07_PCOS_Reference_Flow_Model]]

---

## 🛠️ The Technology Stack

### 1. Core Engine & Backend
- **Language**: Python 3.11+ / FastAPI
- **Graph & State Management**: NetworkX (local) + cuGraph (GPU acceleration) + SQLite / PostgreSQL for persistent node storage
- **MCP Server**: FastMCP (Python) exposing standard Model Context Protocol tools to IDE agents (Claude Code, Gemini CLI, Cursor, Windsurf)
- **Validation**: Pydantic v2 (Strict Schema enforcement)

### 2. Socratic AI & Acceleration Layer (Dual Provider)
- **Google Track**: `google-genai` SDK (Gemini 2.0 Flash / Pro) for multimodal ingest & structured question generation
- **NVIDIA Track**: `langchain-nvidia-ai-endpoints` / NVIDIA NIMs + NeMo Guardrails (`colang` policies) + cuGraph

### 3. Frontend & Visual Semantic Zoom Canvas
- **Framework**: Vite + React / Next.js + TypeScript + Tailwind CSS
- **Interactive Graph**: `@xyflow/react` (React Flow) or Cytoscape.js with custom semantic zoom levels
- **Design System**: Lucide Icons + Radix UI / Shadcn

---

## 📅 Phased Execution Plan

### Phase 0: Foundations & Data Model (Days 1–2)
- [x] Establish Obsidian Second Brain & architectural blueprints
- [ ] Define Pydantic models for the 6-layer ontology (User, Flow, Screen, CTA, API, Logic, Question)
- [ ] Implement Graph Manager with bidirectional traversal & blast-radius calculation
- [ ] Model the canonical PCOS flow (W05 Checkout $\to$ W06 Payment $\to$ API32/42)

### Phase 1: Socratic Question & Stop-Rule Engine (Days 3–4)
- [ ] Implement rule-based checklists per node type (Screen states, CTA debouncing, API timeouts)
- [ ] Implement LLM-powered domain question generation (Google Gemini & NVIDIA NIM adapters)
- [ ] Build the Branch Readiness scoring engine ($Readiness = 0.0$ if blocking questions exist)

### Phase 2: SpecGraph MCP Server (Days 5–6)
- [ ] Expose standard MCP tools:
  - `list_ready_branches()`
  - `get_node_details(node_id)`
  - `post_blocking_question(node_id, question, assigned_to)`
  - `record_build_status(node_id, status, commit_hash)`
  - `calculate_blast_radius(node_id)`
- [ ] Verify agent loop: agent reads branch $\to$ identifies gap $\to$ posts question $\to$ stops guessing $\to$ switches branch

### Phase 3: Interactive Semantic Zoom Canvas UI (Days 7–9)
- [ ] Build zoomable visual map with level-by-level reveal (L1 $\to$ L6)
- [ ] Color-coded readiness indicators (Green = Ready, Red = Blocked, Blue = Review)
- [ ] Node inspector panel with markdown definitions and question thread resolver

### Phase 4: Dual Hackathon Polish & Showcase (Days 10–12)
- [ ] **Google Track Showcase**: One-click PDF PRD & FigJam ingestion into live Graph + Gemini 2.0 reasoning
- [ ] **NVIDIA Track Showcase**: NeMo Guardrails stopping hallucinated code + cuGraph blast radius visualization
- [ ] Record high-impact video demos & side-by-side comparison benchmark (Traditional PRD vs SpecGraph)
