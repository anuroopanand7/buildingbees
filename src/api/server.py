"""
BuildingBees FastAPI Server
Provides REST endpoints and state synchronization for the Semantic Zoom Canvas,
Socratic Question Engine, and Dual Hackathon Track Adapters.
"""

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import datetime
import json
import os

# Load KEY=value lines from a local .env (never committed) before adapters read the environment.
_ENV = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_ENV):
    for _line in open(_ENV):
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.strip().split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

from src.core.graph import BuildingBeesEngine
from src.core.schema import (
    NodeStatus,
    QuestionNode,
    QuestionStatus,
    QuestionCategory
)
from src.data.pcos_fixture import build_pcos_graph
from src.core.question_engine import SocraticQuestionEngine
from src.adapters.gemini_adapter import GoogleGeminiAdapter
from src.core.ingest import add_questions, build_graph_from_extract

app = FastAPI(
    title="BuildingBees API",
    description="Agentic Information Architecture & Stop-Rule Verification Engine",
    version="1.0.0"
)

# Root path to web directory
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web"))

@app.get("/")
def serve_index():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BuildingBees API is running"}


# Enable CORS for local development and canvas UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared in-memory graph initialized with canonical PCOS flow
graph = build_pcos_graph()
question_engine = SocraticQuestionEngine(graph)
gemini_adapter = GoogleGeminiAdapter()


class QuestionResolveRequest(BaseModel):
    answer_text: str


class PostQuestionRequest(BaseModel):
    target_node_id: str
    question_text: str
    category: str = "BACKEND"
    assigned_to: str = "TECH_LEAD"


class IngestPRDRequest(BaseModel):
    prd_markdown: str


@app.get("/api/graph")
def get_graph_state() -> Dict[str, Any]:
    """Returns the full graph state: nodes, edges, and open blocking questions."""
    nodes_serialized = [node.model_dump() for node in graph.nodes.values()]
    edges = []
    for source, targets in graph.forward_edges.items():
        for target in targets:
            edges.append({"source": source, "target": target})

    return {
        "nodes": nodes_serialized,
        "edges": edges,
        "total_nodes": len(graph.nodes),
        "total_edges": len(edges)
    }


@app.get("/api/branch-readiness/{screen_id}")
def get_branch_readiness(screen_id: str) -> Dict[str, Any]:
    """Calculates branch readiness score and checks stop-rule conditions."""
    try:
        readiness = graph.evaluate_branch_readiness(screen_id)
        return readiness.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/inspect")
def run_socratic_inspection() -> Dict[str, Any]:
    """Runs automated Socratic Question Engine checklists over the entire graph."""
    results = question_engine.run_full_graph_inspection()
    return results


@app.post("/api/questions/{question_id}/resolve")
def resolve_question(question_id: str, payload: QuestionResolveRequest) -> Dict[str, Any]:
    """Resolves a blocking question, writes answer into spec, and recalculates readiness."""
    node = graph.get_node(question_id)
    if not node or not isinstance(node, QuestionNode):
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")

    if not payload.answer_text.strip():
        raise HTTPException(status_code=400, detail="Answer is empty")
    node.question_status = QuestionStatus.ANSWERED
    node.answer_text = payload.answer_text
    node.answered_at = datetime.datetime.utcnow().isoformat()
    
    # Target node status can be updated to READY if no other blocking questions exist
    target_node = graph.get_node(node.target_node_id)

    return {
        "status": "RESOLVED",
        "question_id": question_id,
        "target_node_id": node.target_node_id,
        "answer_text": node.answer_text
    }


@app.post("/api/questions")
def post_question(payload: PostQuestionRequest) -> Dict[str, Any]:
    """Manually or agentically posts a blocking question to a node."""
    target = graph.get_node(payload.target_node_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target node '{payload.target_node_id}' not found")

    q_cat = QuestionCategory.BACKEND
    try:
        q_cat = QuestionCategory(payload.category.upper())
    except ValueError:
        pass

    q = QuestionNode(
        target_node_id=payload.target_node_id,
        title=f"Spec Gap on {payload.target_node_id}",
        category=q_cat,
        question_text=payload.question_text,
        is_blocking=True,
        assigned_to=payload.assigned_to,
        question_status=QuestionStatus.OPEN
    )

    graph.add_node(q)
    graph.add_edge(payload.target_node_id, q.id)

    return {"status": "CREATED", "question": q.model_dump()}


@app.get("/api/blast-radius/{node_id}")
def get_blast_radius(node_id: str) -> Dict[str, Any]:
    """Returns all upstream nodes impacted by changes to node_id."""
    return graph.get_blast_radius(node_id)


def _set_graph(new_graph) -> None:
    global graph, question_engine
    graph = new_graph
    question_engine = SocraticQuestionEngine(graph)


def _require_gemini() -> None:
    if not gemini_adapter.enabled:
        raise HTTPException(status_code=503, detail="Gemini is not configured. Set GEMINI_API_KEY and restart.")


@app.post("/api/ingest-prd")
def ingest_prd(payload: IngestPRDRequest) -> Dict[str, Any]:
    """Gemini turns pasted PRD text into a fresh typed graph, with blocking questions."""
    _require_gemini()
    if not payload.prd_markdown.strip():
        raise HTTPException(status_code=400, detail="PRD text is empty")
    try:
        _set_graph(build_graph_from_extract(gemini_adapter.extract_spec(text=payload.prd_markdown)))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini ingest failed: {e}")
    return get_graph_state()


@app.post("/api/ingest-file")
async def ingest_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Gemini reads an uploaded PDF (multimodal) or text/markdown file into a fresh graph."""
    _require_gemini()
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is over 20 MB")
    is_pdf = data[:4] == b"%PDF"
    try:
        extract = (gemini_adapter.extract_spec(pdf_bytes=data) if is_pdf
                   else gemini_adapter.extract_spec(text=data.decode("utf-8", errors="ignore")))
        _set_graph(build_graph_from_extract(extract))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini ingest failed: {e}")
    return get_graph_state()


@app.post("/api/nodes/{node_id}/interrogate")
def interrogate_node(node_id: str) -> Dict[str, Any]:
    """Gemini Socratic pass over one node: adds new blocking questions to the graph."""
    _require_gemini()
    node = graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    neighbour_ids = graph.forward_edges.get(node_id, set()) | graph.reverse_edges.get(node_id, set())
    context = {
        "node": node.model_dump(),
        "neighbours": [graph.nodes[i].model_dump() for i in neighbour_ids
                       if i in graph.nodes and graph.nodes[i].layer.value != "QUESTION"],
    }
    asked = [q.question_text for q in graph.get_questions_for_node(node_id)]
    try:
        questions = gemini_adapter.interrogate(node_id, json.dumps(context, default=str)[:12000], asked)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini interrogation failed: {e}")
    added = add_questions(graph, questions)
    return {"node_id": node_id, "added": [q.model_dump() for q in added]}


@app.get("/api/screens")
def list_screen_readiness() -> List[Dict[str, Any]]:
    """Readiness for every screen branch, for the dashboard."""
    return [graph.evaluate_branch_readiness(n.id).model_dump()
            for n in graph.nodes.values() if n.layer.value == "SCREEN"]


@app.post("/api/reset")
def reset_to_sample() -> Dict[str, Any]:
    """Reloads the built-in PCOS checkout sample."""
    _set_graph(build_pcos_graph())
    return get_graph_state()


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Honest runtime status: is a real model connected, and which one."""
    return {
        "product_name": getattr(graph, "product_name", "PCOS Wellness Store (sample)"),
        "gemini": {"enabled": gemini_adapter.enabled, "model": gemini_adapter.model},
        "total_nodes": len(graph.nodes),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
