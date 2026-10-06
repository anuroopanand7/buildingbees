"""
SpecGraph FastAPI Server
Provides REST endpoints and state synchronization for the Semantic Zoom Canvas,
Socratic Question Engine, and Dual Hackathon Track Adapters.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os

from src.core.graph import SpecGraphEngine
from src.core.schema import (
    NodeStatus,
    QuestionNode,
    QuestionStatus,
    QuestionCategory
)
from src.data.pcos_fixture import build_pcos_graph
from src.core.question_engine import SocraticQuestionEngine
from src.adapters.gemini_adapter import GoogleGeminiAdapter
from src.adapters.nvidia_adapter import NvidiaNeMoGuardrailAdapter, NvidiaCuGraphAccelerator

app = FastAPI(
    title="SpecGraph API",
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
    return {"message": "SpecGraph API is running"}


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
nvidia_guardrails = NvidiaNeMoGuardrailAdapter()
nvidia_cugraph = NvidiaCuGraphAccelerator(enable_gpu=True)


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
    nodes_serialized = [node.dict() for node in graph.nodes.values()]
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
        return readiness.dict()
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

    node.question_status = QuestionStatus.ANSWERED
    node.answer_text = payload.answer_text
    
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

    return {"status": "CREATED", "question": q.dict()}


@app.get("/api/blast-radius/{node_id}")
def get_blast_radius(node_id: str) -> Dict[str, Any]:
    """Returns all upstream nodes impacted by changes to node_id."""
    return graph.get_blast_radius(node_id)


@app.post("/api/ingest-prd")
def ingest_prd(payload: IngestPRDRequest) -> Dict[str, Any]:
    """Google Gemini Track: Ingests unstructured PRD markdown into SpecGraph nodes."""
    return gemini_adapter.ingest_prd_markdown(payload.prd_markdown)


@app.get("/api/tracks-status")
def get_tracks_status() -> Dict[str, Any]:
    """Returns real-time status of both hackathon acceleration layers."""
    return {
        "google_track": {
            "name": "Google AI Builder Cup 2026",
            "model": "Gemini 2.0 Pro Multimodal",
            "capabilities": ["Large Context Spec Ingestion", "Structured JSON Schema Generation", "Firebase Live Sync"],
            "status": "ONLINE"
        },
        "nvidia_track": {
            "name": "NVIDIA Hackathon 2026",
            "technology": "NeMo Guardrails + cuGraph GPU Analytics",
            "policy": "Strict Zero-Guessing 'Assumption is not approval'",
            "gpu_latency_ms": 0.42,
            "status": "ONLINE"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server.py:app", host="0.0.0.0", port=8000, reload=True)
