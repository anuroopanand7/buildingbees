# BuildingBees

**Other tools guess. BuildingBees asks.**

Tools that turn one prompt into screens or diagrams have to guess everything the prompt leaves out. BuildingBees works the way a product team does: it maps the user flows first, then six bees ask what the idea leaves out, one question at a time, and the board is redrawn with every answer. Screens are drawn only after the flows are agreed.

Live demo: https://buildingbees-853213660594.asia-south1.run.app

## How it works

1. **Say what you want to build.** Two lines are enough. A PRD or a PDF works too.
2. **Flows first.** The engine returns the users and their flows, step by step. No screens yet.
3. **The bees ask.** Each question belongs to one bee and points at one step of a flow.

   | Bee | Asks about |
   |---|---|
   | Queen Bee | who it is for, scope, success |
   | Design Bee | what the person sees and feels |
   | Frontend Bee | screen states, validation, failure behaviour |
   | Backend Bee | data, integrations, timeouts, retries |
   | Test Bee | edge cases and what goes wrong |
   | Compliance Bee | privacy, consent, rules |

4. **Every answer is read.** A vague answer ("everyone", "whatever is normal") gets one sharper follow-up and changes nothing. A clear answer rewrites the board: steps are added, changed or removed, a new flow appears if you asked for one, and the bee says what it did. You can change any answer; the bee takes back what the first one did.
5. **Draw the screens.** The agreed flows and every decision become screens with wireframes, buttons, and the APIs each button calls. The bees then ask again, screen by screen, and answers fill in the missing details (a timeout, a vendor, an empty state).
6. **Take the Brief.** One document with the flows, screens, every decision and what is still open. Copy it, download it, print it, or give your coding agent the link. Anything not decided is printed as `NOT DECIDED`, so the builder asks instead of assuming.

A screen is "ready to build" only when it has no open blocking question and no missing detail.

## Engines

| Engine | Used for | Notes |
|---|---|---|
| Google Gemini | Google Cloud AI Builder Cup | Gemini API with structured output (`response_schema`) and native PDF input. Falls over to a second model when one is overloaded. |
| NVIDIA Nemotron | Nebius x NVIDIA Global AI Hackathon | Any OpenAI-compatible endpoint; the default is Nebius Token Factory. PDFs are converted to text first. |

Both engines fill the same Pydantic schemas (`src/adapters/spec_prompts.py`), so the board code does not care which one ran. The six bees are roles inside one engine call: the prompt assigns every question to the bee that owns that aspect. They are not six separate agents.

## Run it locally

Requires Python 3.9 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then add GEMINI_API_KEY and/or the NVIDIA_* values
.venv/bin/python -m uvicorn src.api.server:app --port 8000
```

Open http://localhost:8000. Run the tests with `.venv/bin/python -m pytest -q`.

## Deploy to Google Cloud Run

```bash
gcloud run deploy buildingbees --source . --region asia-south1 --allow-unauthenticated \
  --min-instances 0 --max-instances 1 --set-env-vars "GEMINI_API_KEY=...,GEMINI_MODEL=gemini-3.5-flash"
```

## Project layout

| Path | What it is |
|---|---|
| `web/index.html` | The whole web app: start screen, bee chat, flow and screen board, wireframes, Brief viewer |
| `src/api/server.py` | FastAPI app, one board per visitor |
| `src/adapters/spec_prompts.py` | Every prompt and output schema |
| `src/adapters/gemini_adapter.py`, `nvidia_adapter.py` | The two engines |
| `src/core/ingest.py` | Turns engine output into the board |
| `src/core/graph.py` | The board and the readiness rule |
| `src/core/brief.py` | Writes the Brief (no model call) |

## API

Every call takes the board id in an `X-Board` header or a `?board=` query parameter.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/status` | Which engines are connected |
| POST | `/api/ingest-prd?engine=` | Idea or spec text in, flows and questions out |
| POST | `/api/ingest-file?engine=` | The same from a PDF or Markdown upload |
| POST | `/api/questions/{id}/resolve` | Record an answer |
| POST | `/api/questions/{id}/react?engine=` | The bee reads the answer: follow up, or update the board |
| POST | `/api/questions/{id}/reopen` | Change an answer |
| POST | `/api/expand?engine=` | Draw screens from the agreed flows and decisions |
| POST | `/api/nodes/{id}/interrogate?engine=` | Look for more gaps on one screen, button or API |
| GET | `/api/graph`, `/api/screens` | The board and each screen's readiness |
| GET | `/api/brief` | The Brief, as Markdown |
| POST | `/api/restore`, `/api/reset` | Put a saved board back; clear the board |

## Known limits

- Boards live in server memory. The browser keeps a copy and puts it back if the server restarts, but a Brief link stops working once the server has slept.
- No accounts and no shared editing yet.

## Built with

Built with Claude Code as the coding assistant. At runtime the app calls only the selected engine.

## License

MIT, see [LICENSE](LICENSE).
