# 🚀 BuildingBees: Deployment & Verification Guide
### Google Cloud Run & Local Staging

---

## 🛠️ 1. Local Staging & Execution

### Prerequisites
- Python 3.9+ or Python 3.11
- Virtual environment with requirements installed

### Quick Start Commands
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run automated test suite (5 tests covering all core modules)
PYTHONPATH=. pytest tests/test_buildingbees.py -v

# 3. Run interactive CLI demo
python3 scripts/run_demo.py

# 4. Launch local FastAPI server with interactive canvas
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```
Open **`http://localhost:8000`** in any web browser to interact with the live canvas!

---

## ☁️ 2. Deploying to Google Cloud Run

### Option A: Using Google Cloud Build (Recommended)
```bash
# Submit build to Cloud Build
gcloud builds submit --config=cloudbuild.yaml .
```

### Option B: Direct CLI Deployment to Cloud Run
```bash
# Build and deploy in a single command
gcloud run deploy buildingbees \
  --source . \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

Once deployed, Google Cloud Run provisions an HTTPS URL (e.g., `https://buildingbees-xyz.a.run.app`) that judges can immediately access and test without local setup.

---

## 🔌 3. FastMCP IDE Integration

To connect BuildingBees to Cursor, Windsurf, or Claude Code:
Add to your `mcp_config.json`:
```json
{
  "mcpServers": {
    "buildingbees": {
      "command": "python3",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/graph blueprint"
    }
  }
}
```
Agents will now automatically query branch readiness, enforce stop-rules, and post questions whenever edge cases are discovered!
