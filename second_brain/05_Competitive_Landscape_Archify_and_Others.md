# 05. Competitive Landscape: Archify, Spec-Driven Tools & Our Moat

> **Tags**: #competition #archify #market-analysis #moat
> **Parent**: [[00_Map_of_Content]] | **Next**: [[06_Engineering_Roadmap_from_Scratch]]

---

## 🥊 Analysis of Competitors & Existing Approaches

### 1. Archify & Open-Source Spec-to-Code Tools
- **What Archify does**: Focuses on generating system architecture diagrams and boilerplate project scaffolding from natural language prompts.
- **The Gap**:
  - Archify is primarily **one-way generation** (prompt $\to$ diagram or code). It lacks the **Socratic Question Loop** that interrogates missing business rules.
  - No connective tissue linking **Screen CTAs to API failure modes**.
  - Does not enforce **"Assumption is not approval"** or halt autonomous agents when edge cases are undefined.

### 2. GitHub Spec Kit & AWS Kiro
- **What they do**: Markdown/YAML spec files paired with coding agents (developer-centric).
- **The Gap**:
  - Text-file-heavy, single-user developer tools.
  - Zero visual shared canvas for PMs, Designers, and Tech Leads.
  - No role-based review workflows (PM pull-request approval of product changes).
  - Incapable of semantic zooming across User $\to$ Flow $\to$ Screen $\to$ CTA $\to$ API.

### 3. Plane (plane.so) & Linear
- **What they do**: Modern project management, issue tracking, and agent work-item dispatch.
- **The Gap**:
  - They manage **work tickets** ("Task 102: Build checkout screen"), but possess **zero architectural understanding** of what the screen actually looks like or which API it invokes.
  - **Our Opportunity**: SpecGraph acts as the **intelligence and architecture layer** on top of Plane. We tell the agent *what to build*, while Plane tracks *that it is being built*.

---

## 🛡️ SpecGraph's Competitive Moats

```
                     ┌────────────────────────────────────────┐
                     │          SpecGraph Moat Quad           │
                     └──────────────────┬─────────────────────┘
                                        │
     ┌──────────────────────┬───────────┴───────────┬──────────────────────┐
     ▼                      ▼                       ▼                      ▼
[1. Connective Tissue] [2. Socratic Interrogator] [3. Stop-Rule Protocol] [4. Bidirectional Blast]
CTA state machines     Agents interview humans    Guaranteed zero-guess   Modify API32 -> see
(success/failure)      until spec is complete     safe build loops        exact screens affected
```

1. **CTA-Centric Connective Tissue**: Competitors connect screens to screens (wireframes) or APIs to databases (backends). We link the CTA directly to API invocations, success redirects, and failure recovery.
2. **The Question Engine**: While other tools let you write a spec, SpecGraph interviews your team until the spec is mathematically buildable.
3. **Branch-Level Readiness Score**: Enables parallel asynchronous engineering: agents build branches that have 0 open questions while PMs and architects refine adjacent branches.
4. **Agent-Native MCP Server**: Any IDE agent (Claude Code, Gemini CLI, Cursor, Windsurf) can connect directly to SpecGraph via standard MCP tools.
