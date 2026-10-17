"""
BuildingBees FastAPI Server
Provides REST endpoints and state synchronization for the Semantic Zoom Canvas,
Socratic Question Engine, and Dual Hackathon Track Adapters.
"""

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import datetime
import hashlib
import json
import logging
import os
import time
import zlib
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
from src.adapters.spec_prompts import AUDIENCE, BATCH_NOTE, REACT_PROMPT
from src.api import feedback
from src.adapters import tavily
from src.core.brief import build_brief, decision_count
from src.core.ingest import add_gap_questions, add_questions, apply_gap_default, strip_guesses, build_flows_graph, merge_feature, build_graph_from_extract, clean_branches, ask_open_branches, add_gap_defaults

app = FastAPI(
    title="BuildingBees API",
    description="Agentic Information Architecture & Stop-Rule Verification Engine",
    version="1.0.0"
)

# Root path to web directory
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web"))

@app.get("/")
def serve_index():
    """Serves the single-page web app."""
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BuildingBees API is running"}



# One board per visitor, keyed by the X-Board header the web app sends.
# Memory is the cache; on Cloud Run every change is also written to Firestore, so a board and its
# Brief link survive the server sleeping. Locally there is no Firestore and the browser's copy
# (re-uploaded via /api/restore) is the only backup.
MAX_BOARDS = 300
boards: "OrderedDict[str, BuildingBeesEngine]" = OrderedDict()
_board_id: ContextVar[str] = ContextVar("board_id", default="default")
_auth: ContextVar[str] = ContextVar("auth", default="")  # this request's Authorization header, to record who made a board
log = logging.getLogger("buildingbees")

_store = None   # Firestore collection of boards
_users = None   # Firestore collection of people and the boards they own
if os.getenv("K_SERVICE"):  # set by Cloud Run; keeps tests and local runs off the network
    try:
        from google.cloud import firestore
        _db = firestore.Client()
        _store, _users = _db.collection("boards"), _db.collection("users")
    except Exception as e:
        log.warning("Firestore unavailable, boards stay in memory: %s", e)


def _doc(bid: str):
    """Firestore document for a board: the SHA-1 of the board id, so any id is a safe document name."""
    # Board ids come from the client; hashing makes any of them a legal document id.
    return _store.document(hashlib.sha1(bid.encode()).hexdigest())


def _save_board(bid: str) -> None:
    """Saves a board to Firestore as compressed JSON (Cloud Run only; a no-op locally)."""
    g = boards.get(bid)
    if _store is None or g is None:
        return
    try:
        # One compressed blob: a board with a long spec stays far under Firestore's 1 MiB document limit.
        blob = zlib.compress(json.dumps(_state(g), default=str).encode())
        _doc(bid).set({"data": blob, "updated": datetime.datetime.now(datetime.timezone.utc)})
    except Exception as e:
        log.warning("Could not save board: %s", e)


def _load_board(bid: str) -> Optional[BuildingBeesEngine]:
    """Loads a board from Firestore, or None when it is not there or Firestore is off."""
    if _store is None:
        return None
    try:
        snap = _doc(bid).get()
        return _rebuild(json.loads(zlib.decompress(snap.get("data")))) if snap.exists else None
    except Exception as e:
        log.warning("Could not load board: %s", e)
        return None


# Sign-in (Firebase Authentication, Google accounts). Optional: without FIREBASE_WEB_CONFIG the product
# works exactly as before, one board per browser. Signed in, every board a person works on is listed
# under their account, so they can come back from any device.
try:
    FIREBASE = json.loads(os.getenv("FIREBASE_WEB_CONFIG") or "null")
except ValueError:
    FIREBASE = None
_tokens: Dict[str, tuple] = {}   # token -> (uid, expiry), so each request does not re-fetch Google's keys
_user_boards: Dict[str, Dict[str, Dict[str, Any]]] = {}  # used when there is no Firestore (local runs, tests)


def _uid(authorization: str) -> Optional[str]:
    """The signed-in person's id from a Firebase ID token, or None. Never raises: signing in is optional."""
    token = authorization[7:] if authorization.lower().startswith("bearer ") else ""
    if not token or not FIREBASE:
        return None
    hit = _tokens.get(token)
    if hit and hit[1] > time.time():
        return hit[0]
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
        claims = id_token.verify_firebase_token(token, google_requests.Request(), audience=FIREBASE["projectId"])
    except Exception:
        return None
    if len(_tokens) > 2000:
        _tokens.clear()
    _tokens[token] = (claims["sub"], claims.get("exp", 0))
    return claims["sub"]


def _remember_board(uid: str, bid: str) -> None:
    """Adds a board to its owner's list. Empty boards are not worth listing."""
    g = boards.get(bid)
    if not uid or g is None or not g.nodes:
        return
    entry = {"id": bid, "name": getattr(g, "product_name", "") or "Untitled board",
             "updated": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    key = hashlib.sha1(bid.encode()).hexdigest()
    _user_boards.setdefault(uid, {})[key] = entry
    if _users is not None:
        try:
            _users.document(uid).set({"boards": {key: entry}}, merge=True)
        except Exception as e:
            log.warning("Could not save the board list: %s", e)


def _list_boards(uid: str) -> List[Dict[str, Any]]:
    """The boards a signed-in person has worked on, newest first."""
    mine = dict(_user_boards.get(uid, {}))
    if _users is not None:
        try:
            snap = _users.document(uid).get()
            if snap.exists:
                mine = {**(snap.to_dict().get("boards") or {}), **mine}
        except Exception as e:
            log.warning("Could not load the board list: %s", e)
    return sorted(mine.values(), key=lambda b: b.get("updated", ""), reverse=True)


def _board() -> BuildingBeesEngine:
    """The board this request is about, loaded from memory or Firestore."""
    bid = _board_id.get()
    if bid not in boards:
        boards[bid] = _load_board(bid) or BuildingBeesEngine()
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
    """Reads the board id from the X-Board header or ?board= and makes it current for this request."""
    # The web app sends a header; a coding agent given a link uses ?board=.
    bid = (request.headers.get("x-board") or request.query_params.get("board") or "default")[:64]
    _board_id.set(bid)
    _auth.set(request.headers.get("authorization", ""))
    response = await call_next(request)
    if (request.method == "POST" and request.url.path.startswith("/api/") and response.status_code < 400
            and not request.url.path.startswith(("/api/feedback", "/api/me/boards/"))):  # not the open board's business
        await run_in_threadpool(_save_board, bid)
        auth = request.headers.get("authorization", "")
        if auth:
            await run_in_threadpool(lambda: _remember_board(_uid(auth), bid))
    return response
engines = {e.key: e for e in (GoogleGeminiAdapter(), NvidiaNemotronAdapter())}
app.include_router(feedback.router)  # the beta testers' feedback board (src/api/feedback.py)


class QuestionResolveRequest(BaseModel):
    answer_text: str
    by: str = ""  # who answered, as the team sees it ("Backend: Ravi"); several people share one board
    bees_decided: bool = False  # "Decide for me": the bees' recommendation, listed with the defaults so it can be changed
    later: bool = False  # saved, not applied: it waits until the person presses "Update the board"


class PostQuestionRequest(BaseModel):
    target_node_id: str
    question_text: str
    category: str = "BACKEND"
    assigned_to: str = "TECH_LEAD"


class IngestPRDRequest(BaseModel):
    prd_markdown: str
    mode: str = "solo"  # "solo": one founder, plain questions; "team": several people answer by role


def audience(g_or_mode) -> str:
    """The AUDIENCE instruction for a board (or a mode name): how many questions, and in whose words."""
    mode = g_or_mode if isinstance(g_or_mode, str) else getattr(g_or_mode, "mode", "solo")
    return AUDIENCE.get(mode, AUDIENCE["solo"])


app.mount("/examples", StaticFiles(directory=os.path.join(WEB_DIR, "examples")), name="examples")


@app.get("/api/graph")
def get_graph_state() -> Dict[str, Any]:
    """Returns the full graph state: nodes, edges, and open blocking questions."""
    return _state(_board())


def _state(graph: BuildingBeesEngine) -> Dict[str, Any]:
    """The whole board as a JSON-ready dict; also what Firestore and the browser backup store."""
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
        "entities": getattr(graph, "entities", []),
        "sources": getattr(graph, "sources", []),
        "signoffs": getattr(graph, "signoffs", []),
        "comments": getattr(graph, "comments", []),
        "mode": getattr(graph, "mode", "solo"),
        "owner": getattr(graph, "owner", ""),
        "plan": getattr(graph, "plan", None),
        "plan_decisions": getattr(graph, "plan_decisions", 0),
        "last_call": getattr(graph, "last_call", None),  # engine pill: which model answered, how fast
        # Stage one agrees the flows; screens are only drawn after that.
        "stage": "screens" if any(n.layer.value == "SCREEN" for n in graph.nodes.values()) else "flows",
        "needs_redraw": bool(getattr(graph, "needs_redraw", False)),
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
    node.metadata["answered_by"] = payload.by.strip()[:60]
    if payload.later:
        node.metadata["pending"] = True  # applied with everything else waiting, by /api/questions/react-batch
    if payload.bees_decided:
        node.metadata["default"] = True
    else:
        node.metadata.pop("default", None)  # a person chose it now
    
    # Target node status can be updated to READY if no other blocking questions exist
    target_node = graph.get_node(node.target_node_id)

    return {
        "status": "RESOLVED",
        "question_id": question_id,
        "target_node_id": node.target_node_id,
        "answer_text": node.answer_text
    }


# Fields a bee may change on a drawn node after an answer, and how to read the text it sends.
_BOOL = lambda v: str(v).strip().lower() in ("true", "yes", "1")  # noqa: E731
EDITABLE = {
    "SCREEN": {"description": str, "states.loading": str, "states.empty": str, "states.error": str},
    "CTA": {"label": str, "target_screen_on_success": str, "target_screen_on_failure": str,
            "error_display_type": str, "max_retries": int},
    "API": {"method": str, "path": str, "service": str, "vendor": str, "timeout_ms": int,
            "cache_ttl_seconds": int, "idempotency_required": _BOOL},
}


def _apply_reaction(g: BuildingBeesEngine, r) -> List[str]:
    """Writes a bee's changes onto the board. Unknown ids and fields are ignored, never guessed."""
    changed: List[str] = []
    drawn = any(n.layer.value == "SCREEN" for n in g.nodes.values())
    for uu in r.user_updates:  # someone new the founder has just named (a librarian, an admin)
        if uu.user_id not in g.nodes and uu.title and not drawn:
            g.add_node(UserNode(id=uu.user_id, title=uu.title, description=uu.description))
            changed.append(uu.user_id)
    users = [n.id for n in g.nodes.values() if n.layer.value == "USER"]
    for fu in r.flow_updates:
        f = g.nodes.get(fu.flow_id)
        if f is None and fu.steps and fu.title and not drawn:
            # A flow the founder has just asked for. Only while flows are still being agreed.
            f = g.add_node(FlowNode(id=fu.flow_id, title=fu.title, goal=fu.goal,
                                   metadata={"steps": fu.steps, "branches": clean_branches(fu.branches, len(fu.steps))}))
            owner = fu.user_id if fu.user_id in users else (users[0] if users else None)
            if owner:
                g.add_edge(owner, f.id)
                g.nodes[owner].flow_ids.append(f.id)
            changed.append(f.id)
            continue
        if f and f.layer.value == "FLOW" and fu.steps:
            f.title, f.goal = fu.title or f.title, fu.goal or f.goal
            before = f.metadata.get("steps", [])
            f.metadata["was"] = before  # so the board can show what this answer changed
            f.metadata["steps"] = fu.steps
            f.metadata["was_branches"] = f.metadata.get("branches", [])
            f.metadata["branches"] = clean_branches(fu.branches, len(fu.steps)) if fu.branches else \
                [b for b in f.metadata.get("branches", []) if b["at_step"] <= len(fu.steps)]
            for q in g.get_questions_for_node(f.id):  # keep each open question on its step if that step survived
                k = int(q.metadata.get("step") or 0)
                if q.question_status == QuestionStatus.OPEN and k:
                    text = before[k - 1] if k <= len(before) else None
                    q.metadata["step"] = fu.steps.index(text) + 1 if text in fu.steps else 0
            changed.append(f.id)
    for uu in r.user_updates:
        u = g.nodes.get(uu.user_id)
        if u and u.layer.value == "USER":
            u.title, u.description = uu.title or u.title, uu.description or u.description
            changed.append(u.id)
    for x in r.field_updates:
        n = g.nodes.get(x.node_id)
        cast = EDITABLE.get(n.layer.value, {}).get(x.field) if n else None
        if not cast:
            continue
        try:
            value = cast(x.value)
        except (TypeError, ValueError):
            continue
        owner, _, leaf = x.field.rpartition(".")
        setattr(getattr(n, owner) if owner else n, leaf, value)
        if x.field == "label":
            n.title = value
        changed.append(n.id)
    return list(dict.fromkeys(changed))


@app.post("/api/questions/{question_id}/react")
def react_to_answer(question_id: str, engine: str) -> Dict[str, Any]:
    """A bee reads the answer: it asks a sharper follow-up if the answer is vague, otherwise it updates the board."""
    eng = _engine(engine)
    g = _board()
    q = g.get_node(question_id)
    if not q or not isinstance(q, QuestionNode) or q.question_status != QuestionStatus.ANSWERED:
        raise HTTPException(status_code=404, detail="No answered question with that id")
    target = g.get_node(q.target_node_id)
    stage, board = _react_board(g, [q.target_node_id])
    decisions = "\n".join(
        f"- {d.question_text} => {d.answer_text}" for d in g.nodes.values()
        if isinstance(d, QuestionNode) and d.question_status == QuestionStatus.ANSWERED and d.id != q.id
    ) or "(none)"
    step = int(q.metadata.get("step") or 0)
    prompt = audience(g) + "\n\n" + REACT_PROMPT.format(
        stage=stage, board=json.dumps(board, default=str)[:14000], decisions=decisions[:4000],
        category=q.category.value, target=(target.title if target else q.target_node_id),
        step=(f", step {step}" if step else "") + (f", the \"{q.metadata['branch'].split('|', 1)[1]}\" path that splits off there"
                                                   if q.metadata.get("branch") else ""),
        question=q.question_text, answer=q.answer_text,
        changed_from=(f"\nTHE FOUNDER FIRST ANSWERED \"{q.metadata['previous_answer']}\" AND HAS NOW CHANGED THEIR MIND. "
                      "Take back whatever that first answer put on the board, then apply the new one."
                      if q.metadata.get("previous_answer") else ""),
    )
    started = time.time()
    try:
        r = eng.react(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not process the answer: {e}")
    _trace(g, eng, started)

    changed = [] if r.is_vague else _apply_reaction(g, r)
    for f in r.follow_up[:1]:
        f.target_id, f.category = q.target_node_id, q.category.value  # the bee that asked follows up
    added = add_questions(g, r.follow_up[:1], eng.label, dedupe=False)  # a follow-up may echo its question
    if r.is_vague and not added:
        # No sharper question came back, so the original must not disappear: ask it again.
        q.question_status, q.answer_text, q.answered_at = QuestionStatus.OPEN, None, None
    if stage == "screens" and q.metadata.get("previous_answer") and not r.is_vague:
        g.needs_redraw = True  # a decision changed after the screens were drawn; field edits cannot fix structure
    _after_reaction(g, stage, eng)
    q.metadata["note"] = r.note[:300]
    q.metadata["vague"] = bool(r.is_vague)  # a vague answer is kept in the chat but is not a decision
    q.metadata.pop("previous_answer", None)
    return {"is_vague": r.is_vague, "note": q.metadata["note"], "changed": changed,
            "follow_up": [a.id for a in added]}


def _after_reaction(g: BuildingBeesEngine, stage: str, eng) -> None:
    """After answers change the board: fill standard defaults on screens, or ask about splits nobody settled."""
    if stage == "screens":
        add_gap_defaults(g)  # anything the answer left unfilled takes the standard, shown as a default
    else:
        ask_open_branches(g, eng.label)  # a split the answer drew but did not settle gets asked


def _react_board(g: BuildingBeesEngine, targets: List[str]):
    """The part of the board a bee needs to read answers about `targets`: every flow at the flows stage,
    or the target nodes and their neighbours once screens exist. Returns (stage, board)."""
    stage = "screens" if any(n.layer.value == "SCREEN" for n in g.nodes.values()) else "flows"
    if stage == "flows":
        board = {
            "users": [{"id": n.id, "title": n.title, "description": n.description}
                      for n in g.nodes.values() if n.layer.value == "USER"],
            "flows": [{"id": n.id, "title": n.title, "goal": n.goal, "steps": n.metadata.get("steps", []),
                       "branches": n.metadata.get("branches", []),
                       "user_id": next(iter(g.reverse_edges.get(n.id, [])), "")}
                      for n in g.nodes.values() if n.layer.value == "FLOW"],
        }
    else:
        near = set().union(*[g.forward_edges.get(t, set()) | g.reverse_edges.get(t, set()) for t in targets])
        board = {
            "targets": [g.nodes[t].model_dump() for t in targets if t in g.nodes],
            "neighbours": [g.nodes[i].model_dump() for i in near
                           if i in g.nodes and g.nodes[i].layer.value != "QUESTION"],
            "screens": [{"id": n.id, "title": n.title} for n in g.nodes.values() if n.layer.value == "SCREEN"],
        }
    return stage, board


class BatchRequest(BaseModel):
    question_ids: List[str] = []  # empty: every answer saved for later, plus every open note on the board


@app.post("/api/questions/react-batch")
def react_to_answers(payload: BatchRequest, engine: str) -> Dict[str, Any]:
    """"Update the board": the bees apply every waiting answer and note in ONE call and redraw once.
    The person decides when the board changes; it never moves under them after each answer."""
    eng = _engine(engine)
    g = _board()
    ids = payload.question_ids or [n.id for n in g.nodes.values() if isinstance(n, QuestionNode) and n.metadata.get("pending")]
    qs = [g.get_node(i) for i in dict.fromkeys(ids)][:20]
    qs = [q for q in qs if isinstance(q, QuestionNode) and q.question_status == QuestionStatus.ANSWERED]
    notes = [c for c in getattr(g, "comments", []) if c["status"] == "open"][:20] if not payload.question_ids else []
    if not qs and not notes:
        raise HTTPException(status_code=404, detail="Nothing is waiting to be applied")
    stage, board = _react_board(g, list(dict.fromkeys([q.target_node_id for q in qs] + [c["target"] for c in notes if c["target"] in g.nodes])))
    ids = {q.id for q in qs}
    decisions = "\n".join(
        f"- {d.question_text} => {d.answer_text}" for d in g.nodes.values()
        if isinstance(d, QuestionNode) and d.question_status == QuestionStatus.ANSWERED and d.id not in ids
    ) or "(none)"
    answers = "\n".join(f"{i}. ({q.category.value}, about {getattr(g.nodes.get(q.target_node_id), 'title', q.target_node_id)}) "
                        f"{q.question_text}\n   ANSWER: {q.answer_text}" for i, q in enumerate(qs, 1)) or "(no answers this time)"
    if notes:
        answers += "\n\nNOTES THE FOUNDER LEFT ON PARTS OF THE BOARD (apply each one like an answer; a note can add, change or remove steps, branches or whole flows):\n" + \
            "\n".join(f"- {_where(g, c)}: {c['text']}" for c in notes)
    prompt = audience(g) + "\n\n" + BATCH_NOTE + REACT_PROMPT.format(
        stage=stage, board=json.dumps(board, default=str)[:14000], decisions=decisions[:4000],
        category="several", target="the set below", step="", question="(a set of questions, listed with their answers below)",
        answer=answers, changed_from="")
    started = time.time()
    try:
        r = eng.react(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not process the answers: {e}")
    _trace(g, eng, started)
    changed = [] if r.is_vague else _apply_reaction(g, r)
    added = add_questions(g, r.follow_up[:len(qs)], eng.label, dedupe=False)
    if r.is_vague and not added:  # nothing usable and no sharper question: ask the whole set again
        for q in qs:
            q.question_status, q.answer_text, q.answered_at = QuestionStatus.OPEN, None, None
    _after_reaction(g, stage, eng)
    for q in qs:
        q.metadata["vague"] = bool(r.is_vague)
        q.metadata.pop("previous_answer", None)
        q.metadata.pop("pending", None)
    if qs:
        qs[-1].metadata["note"] = r.note[:300]  # one note for the set, shown after its last answer
    if not r.is_vague:
        for c in notes:
            c["status"] = "applied"
        if notes and stage == "screens":
            g.needs_redraw = True  # a note can change structure that field edits cannot reach
    return {"is_vague": r.is_vague, "note": r.note[:300], "changed": changed, "follow_up": [a.id for a in added]}


@app.post("/api/questions/accept-defaults")
def accept_detail_defaults() -> Dict[str, Any]:
    """The founder chooses to take the first suggestion for every remaining detail question in one go."""
    g = _board()
    now = datetime.datetime.utcnow().isoformat()
    done = []
    for q in list(g.nodes.values()):
        if isinstance(q, QuestionNode) and q.question_status == QuestionStatus.OPEN and apply_gap_default(g, q):
            q.answered_at = now
            done.append(q.target_node_id)
    return {"applied": len(done), "changed": list(dict.fromkeys(done))}


@app.post("/api/questions/{question_id}/reopen")
def reopen_question(question_id: str) -> Dict[str, Any]:
    """Lets the user change their mind: the answer is cleared and the question is asked again."""
    node = graph.get_node(question_id)
    if not node or not isinstance(node, QuestionNode):
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    # Keep what they said before, so the bee can undo what that answer put on the board.
    node.metadata["previous_answer"] = node.answer_text or node.metadata.get("previous_answer", "")
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
    """Replaces the current request's board."""
    boards[_board_id.get()] = new_graph


LAYER_CLASSES = {c.model_fields["layer"].default.value: c for c in
                 (UserNode, FlowNode, ScreenNode, CTANode, APINode, LogicStepNode, QuestionNode)}


class RestoreRequest(BaseModel):
    product_name: str = ""
    spec_text: str = ""
    entities: List[Dict[str, Any]] = []
    sources: List[Dict[str, str]] = []
    signoffs: List[Dict[str, Any]] = []
    comments: List[Dict[str, Any]] = []
    mode: str = "solo"
    owner: str = ""
    plan: Optional[Dict[str, Any]] = None
    plan_decisions: int = 0
    needs_redraw: bool = False
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, str]]


@app.post("/api/restore")
def restore_board(payload: RestoreRequest) -> Dict[str, Any]:
    """Rebuilds a board from the copy the browser kept (after the server slept)."""
    _set_graph(_rebuild(payload.model_dump()))
    return get_graph_state()


def _rebuild(d: Dict[str, Any]) -> BuildingBeesEngine:
    """Rebuilds a board object from a saved state dict."""
    g = BuildingBeesEngine()
    g.product_name = d.get("product_name", "")
    g.spec_text = d.get("spec_text", "")[:SPEC_LIMIT]
    g.entities = d.get("entities", [])[:50]
    g.sources = d.get("sources", [])[:tavily.MAX_SOURCES]
    g.signoffs = d.get("signoffs", [])[:20]
    g.comments = d.get("comments", [])[:200]
    g.mode = d.get("mode") if d.get("mode") in AUDIENCE else "solo"
    g.owner = d.get("owner", "")
    g.plan, g.plan_decisions = d.get("plan"), int(d.get("plan_decisions") or 0)
    g.needs_redraw = bool(d.get("needs_redraw"))
    for n in d["nodes"][:2000]:
        cls = LAYER_CLASSES.get(n.get("layer"))
        if cls:
            g.add_node(cls.model_validate(n))
    for e in d["edges"][:10000]:
        if e.get("source") in g.nodes and e.get("target") in g.nodes:
            g.add_edge(e["source"], e["target"])
    return g


# shortcut: one in-memory counter protects the shared model key from a runaway client; move to a real
# rate limiter if this ever runs on more than one instance.
MODEL_CALLS_PER_MINUTE = 40
_recent_calls: List[float] = []
# The Nebius key is pay-per-use, so the public site gets a hard daily ceiling: a stranger can never spend
# more than a day's allowance of the hackathon credit. Counted in memory, per UTC day.
NVIDIA_DAILY_CALLS = int(os.getenv("NVIDIA_DAILY_CALLS") or 200)
_nvidia_day: Dict[str, int] = {}


def _engine(name: str):
    """Every AI call names its engine; the hackathon rules require each track to run on its sponsor's models."""
    eng = engines.get(name)
    if not eng:
        raise HTTPException(status_code=400, detail=f"Unknown engine '{name}'. Choose 'gemini' or 'nvidia'.")
    if not eng.enabled:
        raise HTTPException(status_code=503, detail=f"{eng.label} is not configured. Add its API key to .env and restart.")
    now = time.time()
    _recent_calls[:] = [t for t in _recent_calls if now - t < 60]
    if len(_recent_calls) >= MODEL_CALLS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="The bees are busy right now. Give them a minute and try again.")
    if name == "nvidia":
        today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        used = _nvidia_day.get(today, 0)
        if used >= NVIDIA_DAILY_CALLS:
            raise HTTPException(status_code=429, detail="NVIDIA Nemotron has reached today's free limit. Try Google Gemini, or come back tomorrow.")
        _nvidia_day.clear()  # drops yesterday's count
        _nvidia_day[today] = used + 1
    _recent_calls.append(now)
    return eng


SPEC_LIMIT = 60_000


def _trace(g: BuildingBeesEngine, eng, started: float) -> None:
    """Records which model answered the last bee call and how long it took; the board shows it as the engine pill.
    "validated" because every reply was parsed against its Pydantic schema before it reached the board."""
    g.last_call = {"engine": eng.label, "model": getattr(eng, "last_model", "") or getattr(eng, "model", ""),
                   "seconds": round(time.time() - started, 1), "schema": "validated"}


def _start_board(eng, text: str = "", pdf_bytes: Optional[bytes] = None, mode: str = "solo",
                 image: Optional[tuple] = None) -> Dict[str, Any]:
    """Stage one: flows and the questions about them. No screens are drawn yet."""
    mode = mode if mode in AUDIENCE else "solo"
    sources = tavily.research(text)  # Scout Bee; empty without a key, and for PDFs
    lead = audience(mode) + "\n\nTHE IDEA:\n"  # how to ask, then what the founder actually said
    started = time.time()
    try:
        extra = {"image": image} if image else {}  # only Gemini reads images; older engines take no such argument
        # One call only: a second call to make the bees cite the research doubled the wait (17 Oct, 68 s first map).
        x = eng.extract_flows(text=lead + text + tavily.as_prompt(sources), pdf_bytes=pdf_bytes, **extra)
        g = build_flows_graph(x, eng.label)
        g.mode = mode
        g.owner = _uid(_auth.get()) or ""  # who made it: only they can delete it for everyone
        _trace(g, eng, started)
        # The spec is only what the founder said: research never counts as a decision.
        g.spec_text = (text or (pdf_to_text(pdf_bytes) if pdf_bytes else "A photo of the founder's sketch"))[:SPEC_LIMIT]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not read the spec: {e}")
    g.sources = [{"title": s["title"], "url": s["url"]} for s in sources]
    for q in g.nodes.values():  # turn the page number the engine gave into the page itself
        if isinstance(q, QuestionNode):
            n = q.metadata.pop("cite", 0)
            if isinstance(n, int) and 0 < n <= len(g.sources):
                q.metadata["cite"] = g.sources[n - 1]
    _set_graph(g)
    return get_graph_state()


@app.post("/api/ingest-prd")
def ingest_prd(payload: IngestPRDRequest, engine: str) -> Dict[str, Any]:
    """Pasted spec or idea in, user flows and flow-level questions out."""
    eng = _engine(engine)
    if not payload.prd_markdown.strip():
        raise HTTPException(status_code=400, detail="PRD text is empty")
    return _start_board(eng, text=payload.prd_markdown, mode=payload.mode)


@app.post("/api/ingest-file")
async def ingest_file(engine: str, file: UploadFile = File(...), mode: str = "solo") -> Dict[str, Any]:
    """Uploaded PDF or text/markdown in, user flows and flow-level questions out."""
    eng = _engine(engine)
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is over 20 MB")
    if data[:4] == b"%PDF":
        return _start_board(eng, pdf_bytes=data, mode=mode)
    if (file.content_type or "").startswith("image/"):  # a photo of a whiteboard or napkin sketch: Gemini vision reads it
        return _start_board(eng, mode=mode, image=(data, file.content_type))
    return _start_board(eng, text=data.decode("utf-8", errors="ignore"), mode=mode)


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
        audience(old) + "\n\nTHE SPEC:",
        getattr(old, "spec_text", ""),
        "\nAGREED USERS AND FLOWS (keep exactly these ids, and give every screen one of these flow ids):",
        json.dumps({
            "users": [{"id": u.id, "title": u.title} for u in users],
            "flows": [{"id": f.id, "title": f.title, "goal": f.goal, "steps": f.metadata.get("steps", []),
                       "branches": f.metadata.get("branches", []),
                       "user_id": next(iter(old.reverse_edges.get(f.id, [])), "")} for f in flows],
        }),
        "\nDECISIONS THE PRODUCT OWNER HAS ALREADY MADE (part of the spec now, do not ask these again):",
        "\n".join(f"- {q.question_text} => {q.answer_text}" for q in decisions) or "(none yet)",
        "\nNOTES THE TEAM LEFT ON PARTS OF THE BOARD (follow them like decisions):",
        "\n".join(f"- {_where(old, c)}: {c['text']}" for c in getattr(old, "comments", [])) or "(none)",
    ])
    started = time.time()
    try:
        g = build_graph_from_extract(eng.extract_spec(text=brief[:SPEC_LIMIT + 8000]), eng.label)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not draw the screens: {e}")
    _trace(g, eng, started)
    g.spec_text = getattr(old, "spec_text", "")
    g.product_name = getattr(old, "product_name", "") or g.product_name  # the name the founder already saw stays
    g.sources = getattr(old, "sources", [])
    g.signoffs = getattr(old, "signoffs", [])
    g.comments = getattr(old, "comments", [])
    g.mode = getattr(old, "mode", "solo")
    g.owner = getattr(old, "owner", "")
    g.plan, g.plan_decisions = getattr(old, "plan", None), getattr(old, "plan_decisions", 0)
    strip_guesses(g, g.spec_text + " " + " ".join(q.answer_text or "" for q in decisions))
    for f in flows:  # the steps the user agreed to stay on the flow
        if f.id in g.nodes:
            g.nodes[f.id].metadata["steps"] = f.metadata.get("steps", [])
            g.nodes[f.id].metadata["branches"] = f.metadata.get("branches", [])
    for c in g.comments:  # drawing the screens used every note, so nothing is left waiting
        c["status"] = "applied"
    for q in asked:  # every earlier question and its answer travels with the board
        q.metadata.pop("pending", None)  # the screens were drawn from it
        if q.target_node_id in g.nodes:
            g.add_node(q)
            g.add_edge(q.target_node_id, q.id)
    add_gap_defaults(g)
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


class ModeRequest(BaseModel):
    mode: str


@app.post("/api/mode")
def set_mode(payload: ModeRequest) -> Dict[str, Any]:
    """Switches a board between one founder ("solo") and a team; inviting a teammate makes a board a team board."""
    if payload.mode not in AUDIENCE:
        raise HTTPException(status_code=400, detail="Mode is solo or team")
    _board().mode = payload.mode
    return {"mode": payload.mode}


class StepsRequest(BaseModel):
    steps: List[str]


@app.post("/api/flows/{flow_id}/steps")
def edit_flow_steps(flow_id: str, payload: StepsRequest) -> Dict[str, Any]:
    """The team edits a flow's steps by hand, even after screens are drawn; drawn screens are then flagged for a redraw."""
    g = _board()
    f = g.nodes.get(flow_id)
    if not f or f.layer.value != "FLOW":
        raise HTTPException(status_code=404, detail="No such flow")
    steps = [s.strip()[:160] for s in payload.steps if s.strip()][:12]
    if not steps:
        raise HTTPException(status_code=400, detail="A flow needs at least one step")
    f.metadata["was"] = f.metadata.get("steps", [])  # so the board can tag what changed
    f.metadata["steps"] = steps
    f.metadata["branches"] = [b for b in f.metadata.get("branches", []) if b["at_step"] <= len(steps)]
    if any(n.layer.value == "SCREEN" for n in g.nodes.values()):
        g.needs_redraw = True
    return get_graph_state()


class CommentRequest(BaseModel):
    target: str          # the node the note is about: a flow, screen, button or API
    step: int = 0        # 1-based step of a flow; 0 = the whole node
    path: str = ""       # a branch label ("No") when the note is about a path that splits off
    text: str
    by: str = ""


def _where(g: BuildingBeesEngine, c: Dict[str, Any]) -> str:
    """Says in words which part of the board a note is about, for the bees and the Brief."""
    n = g.nodes.get(c["target"])
    name = (getattr(n, "label", "") or n.title) if n else c["target"]
    steps = n.metadata.get("steps", []) if n else []
    where = f'the flow "{name}"' if n is not None and n.layer.value == "FLOW" else f'"{name}"'
    if c.get("step") and c["step"] <= len(steps):
        where += f', step {c["step"]} "{steps[c["step"] - 1].split(":")[0]}"'
    if c.get("path"):
        where += f', the "{c["path"]}" path that splits off there'
    return where


@app.post("/api/comments")
def add_comment(payload: CommentRequest) -> Dict[str, Any]:
    """A note on any part of the board. It waits, with the other notes and answers, until someone updates the board."""
    g = _board()
    text = payload.text.strip()[:1000]
    if not text:
        raise HTTPException(status_code=400, detail="The note is empty")
    if payload.target not in g.nodes:
        raise HTTPException(status_code=404, detail="That part of the board is gone")
    g.comments = getattr(g, "comments", []) + [{
        "id": hashlib.sha1(f"{payload.target}{text}{time.time()}".encode()).hexdigest()[:10],
        "target": payload.target, "step": max(0, payload.step), "path": payload.path[:60], "text": text,
        "by": payload.by.strip()[:60], "at": datetime.datetime.utcnow().isoformat(), "status": "open"}][-200:]
    return get_graph_state()


@app.post("/api/comments/{comment_id}/delete")
def delete_comment(comment_id: str) -> Dict[str, Any]:
    """Takes back a note that has not been applied yet; applied notes stay as the record of why the board changed."""
    g = _board()
    g.comments = [c for c in getattr(g, "comments", []) if not (c["id"] == comment_id and c["status"] == "open")]
    return get_graph_state()


class FeatureRequest(BaseModel):
    text: str


@app.post("/api/features")
def add_feature(payload: FeatureRequest, engine: str) -> Dict[str, Any]:
    """Adds a new feature to the same board: the engine draws only its new flows and questions,
    and every flow, answer and screen already on the board stays as it is."""
    eng = _engine(engine)
    g = _board()
    text = payload.text.strip()[:4000]
    if not text:
        raise HTTPException(status_code=400, detail="Say what the new feature is")
    if not any(n.layer.value == "FLOW" for n in g.nodes.values()):
        raise HTTPException(status_code=400, detail="Map the idea first, then add features to it")
    board = {
        "users": [{"id": n.id, "title": n.title} for n in g.nodes.values() if n.layer.value == "USER"],
        "flows": [{"id": n.id, "title": n.title, "steps": n.metadata.get("steps", [])}
                  for n in g.nodes.values() if n.layer.value == "FLOW"],
    }
    lead = (audience(g) + "\n\nTHE PRODUCT SO FAR (already agreed, do not return these flows again; reuse a user's id "
            "when the same person does the new feature, and give every new flow and user a new id):\n"
            + json.dumps(board)[:12000] + "\n\nTHE NEW FEATURE TO ADD TO THIS PRODUCT:\n")
    started = time.time()
    try:
        new = build_flows_graph(eng.extract_flows(text=lead + text), eng.label)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not add the feature: {e}")
    _trace(g, eng, started)
    added = merge_feature(g, new)
    if not added:
        raise HTTPException(status_code=422, detail="No new flow came back. Try saying what the person does in the new feature.")
    g.spec_text = (getattr(g, "spec_text", "") + "\n\nAdded feature: " + text)[:SPEC_LIMIT]  # the founder said it, so it counts
    if any(n.layer.value == "SCREEN" for n in g.nodes.values()):
        g.needs_redraw = True  # the new flows have no screens yet
    return {**get_graph_state(), "added": added}


class SignoffRequest(BaseModel):
    by: str


@app.post("/api/signoff")
def sign_off(payload: SignoffRequest) -> Dict[str, Any]:
    """Someone who owns part of the scope approves the Brief as it stands. Signing again replaces their earlier sign-off."""
    g = _board()
    by = payload.by.strip()[:60]
    if not g.nodes:
        raise HTTPException(status_code=404, detail="There is nothing on the board yet")
    if not by:
        raise HTTPException(status_code=400, detail="Say who is signing off")
    g.signoffs = [s for s in getattr(g, "signoffs", []) if s["by"] != by] + [
        {"by": by, "at": datetime.datetime.utcnow().isoformat(), "decisions": decision_count(g),
         "open": sum(1 for n in g.nodes.values() if isinstance(n, QuestionNode) and n.question_status == QuestionStatus.OPEN)}]
    return {"signoffs": g.signoffs}


@app.post("/api/plan")
def write_plan(engine: str) -> Dict[str, Any]:
    """Writes the plan an agent builds from (user stories with acceptance criteria, features, build order, glossary)
    from the board's current Brief, and keeps it on the board. One engine call; run again after decisions change."""
    eng = _engine(engine)
    g = _board()
    if not any(n.layer.value == "FLOW" for n in g.nodes.values()):
        raise HTTPException(status_code=400, detail="Map an idea first")
    started = time.time()
    try:
        x = eng.write_plan(audience(g) + "\n\n" + build_brief(g, with_plan=False)[:40000])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{eng.label} could not write the plan: {e}")
    _trace(g, eng, started)
    g.plan = x.model_dump()
    g.plan_decisions = decision_count(g)  # to tell the reader when later decisions made it out of date
    return get_graph_state()


@app.get("/api/brief", response_class=PlainTextResponse)
def get_brief() -> str:
    """The whole board as one Markdown brief: flows, screens, every decision, and what is still open."""
    if not graph.nodes:
        raise HTTPException(status_code=404, detail="There is nothing on the board yet")
    return build_brief(_board())


@app.post("/api/reset")
def reset_to_sample() -> Dict[str, Any]:
    """Clears the board."""
    _set_graph(BuildingBeesEngine())
    return get_graph_state()


@app.post("/api/me/boards")
def my_boards(request: Request) -> Dict[str, Any]:
    """The signed-in person's boards, newest first. The board open right now is added to the list."""
    uid = _uid(request.headers.get("authorization", ""))
    if not uid:
        raise HTTPException(status_code=401, detail="Sign in to see your boards.")
    _remember_board(uid, _board_id.get())
    return {"boards": _list_boards(uid)}


class RenameRequest(BaseModel):
    name: str


def _signed_in(request: Request) -> str:
    """The signed-in person's uid, or 401."""
    uid = _uid(request.headers.get("authorization", ""))
    if not uid:
        raise HTTPException(status_code=401, detail="Sign in to manage your boards.")
    return uid


def _forget_board(uid: str, bid: str) -> None:
    """Takes a board off one person's list (memory and Firestore)."""
    key = hashlib.sha1(bid.encode()).hexdigest()
    _user_boards.get(uid, {}).pop(key, None)
    if _users is not None:
        try:
            from google.cloud import firestore
            _users.document(uid).update({f"boards.{key}": firestore.DELETE_FIELD})
        except Exception as e:
            log.warning("Could not update the board list: %s", e)


@app.post("/api/me/boards/{bid}/delete")
def delete_my_board(bid: str, request: Request) -> Dict[str, Any]:
    """Deletes a board for whoever created it; for anyone else (a teammate) it only leaves their list,
    so a shared board never disappears for the whole team because one member tidied up."""
    uid = _signed_in(request)
    g = boards.get(bid) or _load_board(bid)
    _forget_board(uid, bid)
    deleted = bool(g) and getattr(g, "owner", "") == uid
    if deleted:
        boards.pop(bid, None)
        if _store is not None:
            try:
                _doc(bid).delete()
            except Exception as e:
                log.warning("Could not delete board: %s", e)
    return {"deleted": deleted, "boards": _list_boards(uid)}


@app.post("/api/me/boards/{bid}/rename")
def rename_my_board(bid: str, payload: RenameRequest, request: Request) -> Dict[str, Any]:
    """Renames a board on the person's list and on the board itself (the name everyone sees)."""
    uid = _signed_in(request)
    name = payload.name.strip()[:60]
    if not name:
        raise HTTPException(status_code=400, detail="Give the board a name")
    key = hashlib.sha1(bid.encode()).hexdigest()
    entry = next((b for b in _list_boards(uid) if b["id"] == bid), None)
    if not entry:
        raise HTTPException(status_code=404, detail="That board is not in your list")
    g = boards.get(bid) or _load_board(bid)
    if g:
        g.product_name = name
        boards[bid] = g
        _save_board(bid)
    entry = {**entry, "name": name}
    _user_boards.setdefault(uid, {})[key] = entry
    if _users is not None:
        try:
            _users.document(uid).set({"boards": {key: entry}}, merge=True)
        except Exception as e:
            log.warning("Could not save the board list: %s", e)
    return {"boards": _list_boards(uid)}


@app.get("/api/status")
def get_status() -> Dict[str, Any]:
    """Honest runtime status: is a real model connected, and which one."""
    return {
        "product_name": getattr(graph, "product_name", ""),
        "engines": {k: {"label": e.label, "enabled": e.enabled, "model": e.model} for k, e in engines.items()},
        "research": tavily.enabled(),
        "firebase": FIREBASE,  # public web config, safe to send to the browser
        "total_nodes": len(graph.nodes),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
