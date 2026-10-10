# BuildingBees

**AI made building cheap. Deciding exactly what to build is still slow and vague, and whatever a spec leaves out, coding agents guess.**

BuildingBees turns a product spec into a typed, zoomable graph:

```
User -> Flow -> Screen -> CTA -> API
```

Then a Socratic Question Engine reads every node and asks about what the spec leaves out: failure paths, timeouts, retries, empty and error states. Blocking questions stop a branch from being "ready to build" until a human answers them. **Assumption is not approval.**

## How it works

1. **Choose an engine.** Google Gemini or NVIDIA Nemotron (on Nebius Token Factory). Every AI call runs on the engine you pick.
2. **Bring your spec.** Paste a PRD or upload a PDF / Markdown file. The engine extracts users, flows, screens, CTAs and APIs as structured JSON and flags the gaps.
3. **Zoom in.** Click any node to focus the board on its path. The inspector shows its fields; anything unspecified shows in red.
4. **Answer the questions.** Each answer is written back into the spec, and the screen's readiness score updates live. A branch is build-ready only when no blocking question is open.
5. **Ask for more.** "Ask the engine what this node is missing" runs a fresh Socratic pass on one node.

## Engines

| Engine | Used for | Notes |
|---|---|---|
| Google Gemini | Google AI Builder Cup | Structured output (`response_schema`), native PDF input |
| NVIDIA Nemotron | Nebius x NVIDIA Global AI Hackathon | Served from Nebius Token Factory through its OpenAI-compatible API; PDFs are converted to text first |

Both engines return the same Pydantic schemas (`src/adapters/spec_prompts.py`), so the graph code does not care which one ran.

## Run it locally

Requires Python 3.9+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then add GEMINI_API_KEY and/or the NVIDIA_* values
.venv/bin/python -m uvicorn src.api.server:app --port 8000
```

Open http://localhost:8000. Run the tests with `.venv/bin/python -m pytest -q`.

## Project layout

| Path | What it is |
|---|---|
| `src/core/graph.py` | Graph engine: edges, blast radius, branch readiness (the stop rule) |
| `src/core/ingest.py` | Turns engine output into graph nodes and questions |
| `src/adapters/` | Gemini and Nemotron adapters, shared prompts and schemas |
| `src/api/server.py` | FastAPI app and REST endpoints |
| `web/index.html` | The web app |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/status` | Which engines are connected |
| POST | `/api/ingest-prd?engine=` | Spec text to graph |
| POST | `/api/ingest-file?engine=` | PDF or Markdown upload to graph |
| POST | `/api/nodes/{id}/interrogate?engine=` | Socratic pass on one node |
| GET | `/api/graph` | Nodes and edges |
| GET | `/api/screens` | Readiness for every screen branch |
| POST | `/api/questions/{id}/resolve` | Answer a question |

## Built with

Built with Claude Code as the coding assistant. At runtime the app uses only the selected sponsor engine.

## License

MIT, see [LICENSE](LICENSE).
