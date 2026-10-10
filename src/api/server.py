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
from collections import OrderedDict
from contextvars import ContextVar

# Load KEY=value lines from a local .env (never committed) before adapters read the environment.
_ENV = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_ENV):
    for _line in open(_ENV):
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.strip().split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"'))

from src.core.graph import BuildingBeesEngine
from src.core.schema import (
    APINode,
    CTANode,
    FlowNode,
    LogicStepNode,
    ScreenNode,
    UserNode,
    NodeStatus,
    QuestionNode,
    QuestionStatus,
    QuestionCategory
)
from src.core.question_engine import SocraticQuestionEngine
from src.adapters.gemini_adapter import GoogleGeminiAdapter
from src.adapters.nvidia_adapter import NvidiaNemotronAdapter
from src.adapters.nvidia_adapter import pdf_to_text
from src.core.ingest import add_questions, build_flows_graph, build_graph_from_extract

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

# One board per visitor, keyed by the X-Board header the web app sends.
# shortcut: boards live in memory and vanish when Cloud Run scales to zero; the browser keeps a
# copy and re-uploads it via /api/restore. Move to Firestore if accounts are added.
MAX_BOARDS = 300
boards: "OrderedDict[str, BuildingBeesEngine]" = OrderedDict()
_board_id: ContextVar[str] = ContextVar("board_id", default="default")


def _board() -> BuildingBeesEngine:
    bid = _board_id.get()
    if bid not in boards:
        boards[bid] = BuildingBeesEngine()
        while len(boards) > MAX_BOARDS:
            boards.popitem(last=False)
    boards.move_to_end(bid)
    return boards[bid]


class _BoardProxy:
    """Lets the endpoints keep writing `graph.x` while each request sees its own board."""
    def __getattr__(self, name):
        return getattr(_board(), name)


graph = _BoardProxy()


@app.middleware("http")
async def _select_board(request, call_next):
    _board_id.set((request.headers.get("x-board") or "default")[:64])
    return await call_next(request)
engines = {e.key: e for e in (GoogleGeminiAdapter(), NvidiaNemotronAdapter())}


class QuestionResolveRequest(BaseModel):
    answer_text: str


class PostQuestionRequest(BaseModel):
    target_node_id: str
    question_text: str
    category: str = "BACKEND"
    assigned_to: str = "TECH_LEAD"


class IngestPRDRequest(BaseModel):
    prd_markdown: str


app.mount("/examples", StaticFiles(directory=os.path.join(WEB_DIR, "examples")), name="examples")


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
        "product_name": getattr(graph, "product_name", ""),
        "spec_text": getattr(graph, "spec_text", ""),
        # Stage one agrees the flows; screens are only drawn after that.
        "stage": "screens" if any(n.layer.value == "SCREEN" for n in graph.nodes.values()) else "flows",
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
    results = SocraticQuestionEngine(_board()).run_full_graph_inspection()
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


@app.post("/api/questions/{question_id}/reopen")
def reopen_question(question_id: str) -> Dict[str, Any]:
    """Lets the user change their mind: the answer is cleared and the question is asked again."""
    node = graph.get_node(question_id)
    if not node or not isinstance(node, QuestionNode):
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    node.question_status = QuestionStatus.OPEN
    node.answer_text = None
    node.answered_at = None
    return {"status": "REOPENED", "question_id": question_id}


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
    boards[_board_id.get()] = new_graph


LAYER_CLASSES = {c.model_fields["layer"].default.value: c for c in
                 (UserNode, FlowNode, ScreenNode, CTANode, APINode, LogicStepNode, QuestionNode)}


class RestoreRequest(BaseModel):
    product_name: str = ""
    spec_text: str = ""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, str]]


@app.post("/api/restore")
def restore_board(payload: RestoreRequest) -> Dict[str, Any]:
    """Rebuilds a board from the copy the browser kept (after the server slept)."""
    g = BuildingBeesEngine()
    g.product_name = payload.product_name
    g.spec_text = payload.spec_text[:SPEC_LIMIT]
    for n in payload.nodes[:2000]:
        cls = LAYER_CLASSES.get(n.get("layer"))
        if cls:
            g.add_node(cls.model_validate(n))
    for e in payload.edges[:10000]:
        if e.get("source") in g.nodes and e.get("target") in g.nodes:
            g.add_edge(e["source"], e["target"])
    _set_graph(g)
    return get_graph_state()


def _engine(name: str):
    """Every AI call names its engine; the hackathon rules require each track to run on its sponsor's models."""
    eng = engines.get(name)
    if not eng:
        raise HTTPException(status_code=400, detail=f"Unknown engine '{name}'. Choose 'gemini' or 'nvidia'.")
    if not eng.enabled:
        raise HTTPException(status_code=503, detail=f"{eng.label} is not configured. Add its API key to .env and restart.")
    return eng


SPEC_LIMIT = 60_000


def _start_board(eng, text: str = "", pdf_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """Stage one: flows and the questions about them. No screens are drawn yet."""
    try:
        g = build_flows_graph(eng.extract_flows(text=text, pdf_bytes=pdf_bytes), eng.label)
        g.spec_text = (text or pdf_to_text(pdf_bytes))[:SPEC_LIMIT]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not read the spec: {e}")
    _set_graph(g)
    return get_graph_state()


@app.post("/api/ingest-prd")
def ingest_prd(payload: IngestPRDRequest, engine: str) -> Dict[str, Any]:
    """Pasted spec or idea in, user flows and flow-level questions out."""
    eng = _engine(engine)
    if not payload.prd_markdown.strip():
        raise HTTPException(status_code=400, detail="PRD text is empty")
    return _start_board(eng, text=payload.prd_markdown)


@app.post("/api/ingest-file")
async def ingest_file(engine: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    """Uploaded PDF or text/markdown in, user flows and flow-level questions out."""
    eng = _engine(engine)
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is over 20 MB")
    if data[:4] == b"%PDF":
        return _start_board(eng, pdf_bytes=data)
    return _start_board(eng, text=data.decode("utf-8", errors="ignore"))


@app.post("/api/expand")
def expand_to_screens(engine: str) -> Dict[str, Any]:
    """Stage two: draw screens, buttons and APIs from the agreed flows and the decisions made so far."""
    eng = _engine(engine)
    old = _board()
    flows = [n for n in old.nodes.values() if n.layer.value == "FLOW"]
    if not flows:
        raise HTTPException(status_code=400, detail="There are no flows to draw screens for yet")
    users = [n for n in old.nodes.values() if n.layer.value == "USER"]
    asked = [n for n in old.nodes.values() if isinstance(n, QuestionNode)]
    decisions = [q for q in asked if q.question_status == QuestionStatus.ANSWERED]
    brief = "\n".join([
        getattr(old, "spec_text", ""),
        "\nAGREED USERS AND FLOWS (keep exactly these ids, and give every screen one of these flow ids):",
        json.dumps({
            "users": [{"id": u.id, "title": u.title} for u in users],
            "flows": [{"id": f.id, "title": f.title, "goal": f.goal, "steps": f.metadata.get("steps", []),
                       "user_id": next(iter(old.reverse_edges.get(f.id, [])), "")} for f in flows],
        }),
        "\nDECISIONS THE PRODUCT OWNER HAS ALREADY MADE (part of the spec now, do not ask these again):",
        "\n".join(f"- {q.question_text} => {q.answer_text}" for q in decisions) or "(none yet)",
    ])
    try:
        g = build_graph_from_extract(eng.extract_spec(text=brief[:SPEC_LIMIT + 8000]), eng.label)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not draw the screens: {e}")
    g.spec_text = getattr(old, "spec_text", "")
    for f in flows:  # the steps the user agreed to stay on the flow
        if f.id in g.nodes:
            g.nodes[f.id].metadata["steps"] = f.metadata.get("steps", [])
    for q in asked:  # every earlier question and its answer travels with the board
        if q.target_node_id in g.nodes:
            g.add_node(q)
            g.add_edge(q.target_node_id, q.id)
    _set_graph(g)
    return get_graph_state()


@app.post("/api/nodes/{node_id}/interrogate")
def interrogate_node(node_id: str, engine: str) -> Dict[str, Any]:
    """Socratic pass over one node: adds new blocking questions to the graph."""
    eng = _engine(engine)
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
        questions = eng.interrogate(node_id, json.dumps(context, default=str)[:12000], asked)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} interrogation failed: {e}")
    added = add_questions(graph, questions, eng.label)
    return {"node_id": node_id, "added": [q.model_dump() for q in added]}


@app.get("/api/screens")
def list_screen_readiness() -> List[Dict[str, Any]]:
    """Readiness for every screen branch, for the dashboard."""
    return [graph.evaluate_branch_readiness(n.id).model_dump()
            for n in graph.nodes.values() if n.layer.value == "SCREEN"]


@app.post("/api/reset")
def reset_to_sample() -> Dict[str, Any]:
    """Clears the board."""
    _set_graph(BuildingBeesEngine())
    return get_graph_state()


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Honest runtime status: is a real model connected, and which one."""
    return {
        "product_name": getattr(graph, "product_name", ""),
        "engines": {k: {"label": e.label, "enabled": e.enabled, "model": e.model} for k, e in engines.items()},
        "total_nodes": len(graph.nodes),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
