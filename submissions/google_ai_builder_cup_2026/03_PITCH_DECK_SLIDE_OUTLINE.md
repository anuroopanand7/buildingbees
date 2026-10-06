# 📊 BuildingBees Pitch Deck (10-Slide Championship Outline)
### Google Cloud AI Builder Cup 2026

---

### Slide 1: Cover Slide
- **Title**: BuildingBees
- **Subtitle**: The Agentic Information Architecture Board
- **Tagline**: The shared map your team fills in and your agents build from.
- **Presenter**: BuildingBees Engineering Team | JAPAC Track: Future of Work

### Slide 2: The Core Problem
- **Headline**: Building is cheap. Deciding *what* to build is the new bottleneck.
- **Key Points**:
  - AI agents build in seconds, but guess confidently on missing requirements.
  - PRDs describe intent, not runtime behavior.
  - Figma frames show pixels, not backend failure paths.
  - Three sources of truth (PRD, Figma, Code) drift out of sync by Day 14.

### Slide 3: The Insight & Thesis
- **Headline**: "The Spec is the New Source Code"
- **Visual**: Diagram showing humans writing code in the 2010s vs agents reading structured specs in the 2020s.
- **Core Principle**: If agents read specs directly, the specification must be as strongly typed, testable, and deterministic as code itself.

### Slide 4: The Solution — BuildingBees
- **Headline**: 6-Level Semantic Zoom for Products
- **Levels**:
  - L1: User Personas
  - L2: User Flows
  - L3: Screens & States (Loading, Empty, Error)
  - L4: CTAs (Connective Tissue)
  - L5: API Contracts & Timeouts
  - L6: Backend Steps & Vendor Failure Paths

### Slide 5: Innovation 1 — The CTA as Connective Tissue
- **Headline**: Buttons are State Machines, Not Static Rectangles
- **Mechanism**: A CTA binds screen gestures directly to parallel API contracts, mapping success routes and error fallbacks with form-field preservation.

### Slide 6: Innovation 2 — The Socratic Question Engine
- **Headline**: "Assumption is Not Approval"
- **Mechanism**: Powered by Google Gemini 2.0 Pro, the engine interrogates the graph with checklists per node type, flagging ambiguities and blocking hallucinated builds until resolved by human architects.

### Slide 7: Innovation 3 — Bottom-Up Blast Radius
- **Headline**: Microservice Impact Analysis in 0.4 Milliseconds
- **Mechanism**: Change an API endpoint or vendor, and BuildingBees immediately highlights every dependent screen and flow across the company.

### Slide 8: Technical Architecture on Google Cloud
- **Headline**: Enterprise-Grade Scale with Google Cloud
- **Components**:
  - Gemini 2.0 Pro Multimodal API (2M context ingestion)
  - Gemini Structured Outputs (`response_schema`)
  - Google Cloud Run (Containerized FastAPI service)
  - Firebase App Hosting & Firestore (Real-time collaborative canvas sync)
  - FastMCP Protocol for Cursor, Windsurf, Claude Code, and Gemini CLI

### Slide 9: Market Opportunity & Traction
- **Target Customers**: Software development agencies, venture studios, enterprise engineering teams.
- **ROI**: 70% decrease in spec drift, 85% drop in agent hallucinated rework, 4x faster delivery cycles.

### Slide 10: The Team & Vision
- **Vision**: Re-architecting how software is conceived, specified, and built in the autonomous agent era.
- **Call to Action**: Try the interactive demo on Google Cloud Run today!
