"""BuildingBees as an MCP server, so a coding agent (Claude Code, Cursor, Codex) can read a plan and talk back to
the bees while it builds (idea from Archify, Roger, 18 Oct 2026). Standard library only; speaks MCP over stdio.

Add it to Claude Code:
    claude mcp add buildingbees -- python3 scripts/mcp_server.py
Every tool takes `board`: the board id, or a board link (https://.../?board=<id>).
BUILDINGBEES_URL points at another deployment (default: the live Nemotron site, which has bring your own AI).

Bring your own AI (21 Oct 2026): start_board and run_bees let the agent's own model do the bees' thinking. BuildingBees
hands it the exact prompt and JSON Schema, the agent answers with submit_answer, and the board validates and draws it,
so the person sees their plan on the board at no model cost to us. The agent relays the person's decisions with
answer_question; it must not invent them.
"""

import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.getenv("BUILDINGBEES_URL", "https://buildingbees-nemotron-853213660594.asia-south1.run.app").rstrip("/")
PENDING = {}  # board id -> the request the bees are waiting to repeat once the agent has answered

TOOLS = [
    {"name": "get_plan", "description": "The whole plan as Markdown: plan check, features (F1), flows (FL1) with their splits, "
     "screens (S1) with buttons (B1) and APIs (A1), decisions, assumptions and what is still open. Build from this; ask about "
     "anything marked NOT DECIDED instead of assuming.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}}, "required": ["board"]}},
    {"name": "plan_check", "description": "Blockers and gaps before building. Do not build a part with an open blocker.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}}, "required": ["board"]}},
    {"name": "open_questions", "description": "Questions the team has not answered yet, with the part of the board each is about.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}}, "required": ["board"]}},
    {"name": "add_note", "description": "Leave a note on part of the board when the plan is unclear or wrong (for example "
     "'S2: what happens if the upload fails?'). The team sees it and the bees apply it in the next round. "
     "target is a node id from get_plan's board (use the flow, screen, button or API it is about); step is a flow step number or 0.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}, "target": {"type": "string"},
                                                     "text": {"type": "string"}, "step": {"type": "integer"}},
                     "required": ["board", "target", "text"]}},
    {"name": "start_board", "description": "Bring your own AI: start a new board from an idea, with YOUR model doing the bees' "
     "thinking (no BuildingBees model cost). Returns a board id, a link the person can open to watch the board, and a task: "
     "a prompt plus a JSON Schema. Answer the task with submit_answer. mode is 'solo' or 'team'.",
     "inputSchema": {"type": "object", "properties": {"idea": {"type": "string"}, "mode": {"type": "string"}}, "required": ["idea"]}},
    {"name": "run_bees", "description": "Bring your own AI: run the next bee step on a board with your own model. action is "
     "'update' (apply the answers and notes waiting on the board), 'screens' (draw screens, buttons and APIs) or 'plan' "
     "(user stories, build order). Returns a task to answer with submit_answer.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}, "action": {"type": "string"}},
                     "required": ["board", "action"]}},
    {"name": "submit_answer", "description": "Send the JSON your model wrote for the last task on this board. It is checked "
     "against the schema; if it does not fit you get the reason and can fix it. On success the board redraws.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}, "answer": {"type": "object"}},
                     "required": ["board", "answer"]}},
    {"name": "answer_question", "description": "Record the PERSON's answer to an open question (ids from open_questions). "
     "Ask the person first: product decisions are theirs, never invent them. Answers wait until run_bees 'update'.",
     "inputSchema": {"type": "object", "properties": {"board": {"type": "string"}, "question_id": {"type": "string"},
                                                     "answer": {"type": "string"}}, "required": ["board", "question_id", "answer"]}},
]


def _board(value: str) -> str:
    """Accepts a board id or a board link and returns the id."""
    if "board=" in value:
        return urllib.parse.parse_qs(urllib.parse.urlparse(value).query).get("board", [value])[0]
    return value.strip()


def _call(path: str, board: str, body=None):
    """Calls the BuildingBees API for one board; returns text or parsed JSON."""
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"X-Board": _board(board), "Content-Type": "application/json", "X-Role": "AGENT"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if r.headers.get_content_type() == "application/json" else raw
    except urllib.error.HTTPError as e:
        detail = json.loads(e.read().decode("utf-8") or "{}").get("detail")
        if e.code == 409 and isinstance(detail, dict) and detail.get("needs_agent"):
            return detail  # bring your own AI: a task for the agent's model, not a failure
        raise RuntimeError(f"HTTP {e.code}: {detail}")


ACTIONS = {"update": ("/api/questions/react-batch?engine=agent", {"question_ids": []}),
           "screens": ("/api/expand?engine=agent", None), "plan": ("/api/plan?engine=agent", None)}


def _task_or_done(board: str, path: str, body) -> str:
    """Makes a bee request with engine=agent; returns the task for the agent's model, or what changed on the board."""
    out = _call(path, board, {} if body is None else body)
    if isinstance(out, dict) and out.get("needs_agent"):
        PENDING[_board(board)] = (path, body, out["kind"])
        return (f"TASK ({out['kind']}): answer the prompt below with ONE JSON object matching the schema, then call "
                f"submit_answer with board={_board(board)}.\n\nPROMPT:\n{out['prompt']}\n\nSCHEMA:\n{json.dumps(out['schema'])}")
    PENDING.pop(_board(board), None)
    nodes = out.get("nodes", []) if isinstance(out, dict) else []
    count = lambda layer: sum(1 for n in nodes if n.get("layer") == layer)
    return (f"Done. The board now has {count('FLOW')} flows, {count('SCREEN')} screens and "
            f"{sum(1 for n in nodes if n.get('layer') == 'QUESTION' and n.get('question_status') == 'OPEN')} open questions. "
            f"The person can watch it at {BASE}/?board={_board(board)} . Next: open_questions, ask the person, "
            "answer_question, then run_bees 'update'; when nothing blocks, run_bees 'screens', then 'plan', then get_plan.")


def run_tool(name: str, args: dict) -> str:
    """Runs one tool and returns the text the agent reads."""
    b = args.get("board", "")
    if name == "get_plan":
        return _call("/api/brief", b)
    if name == "plan_check":
        c = _call("/api/plan-check", b)
        lines = [("Ready for a builder." if c["passed"] else "Not ready yet.")]
        lines += [f"- {i['level']}: {i['text']}" for i in c["issues"]]
        return "\n".join(lines)
    if name == "open_questions":
        g = _call("/api/graph", b)
        ids = g.get("short_ids", {})
        open_qs = [n for n in g["nodes"] if n.get("layer") == "QUESTION" and n.get("question_status") == "OPEN"]
        return "\n".join(f"- {q['id']} [{ids.get(q['target_node_id'], q['target_node_id'])}] {q['question_text']}"
                         + (" (needed before building)" if q.get("is_blocking") else "") for q in open_qs) or "Nothing is open."
    if name == "add_note":
        _call("/api/comments", b, {"target": args["target"], "step": int(args.get("step") or 0), "text": args["text"], "by": "Coding agent"})
        return "Note added. The team sees it, and the bees apply it when the round is processed."
    if name == "start_board":
        b = "agent-" + secrets.token_hex(4)  # a fresh board; the id is also the link
        return f"Board {b} started.\n" + _task_or_done(b, "/api/ingest-prd?engine=agent",
                                                         {"prd_markdown": args["idea"], "mode": args.get("mode") or "solo"})
    if name == "run_bees":
        if args.get("action") not in ACTIONS:
            raise ValueError("action must be 'update', 'screens' or 'plan'")
        path, body = ACTIONS[args["action"]]
        return _task_or_done(b, path, body)
    if name == "submit_answer":
        pend = PENDING.get(_board(b))
        if not pend:
            raise ValueError("No task is waiting on this board. Call start_board or run_bees first.")
        path, body, kind = pend
        _call("/api/agent/answer", b, {"kind": kind, "answer": args["answer"]})
        return _task_or_done(b, path, body)
    if name == "answer_question":
        _call(f"/api/questions/{urllib.parse.quote(args['question_id'])}/resolve", b,
              {"answer_text": args["answer"], "by": "Coding agent (relaying the person)", "later": True})
        return "Saved. It is applied with the other answers when you call run_bees 'update'."
    raise ValueError(f"Unknown tool {name}")


def handle(msg: dict):
    """Answers one MCP JSON-RPC message; returns None for notifications."""
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "buildingbees", "version": "1.1"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        p = msg.get("params", {})
        try:
            result = {"content": [{"type": "text", "text": run_tool(p.get("name", ""), p.get("arguments") or {})}]}
        except Exception as e:  # the agent sees what went wrong instead of a dead tool
            result = {"content": [{"type": "text", "text": f"BuildingBees could not do that: {e}"}], "isError": True}
    elif mid is None:
        return None  # a notification (for example notifications/initialized)
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    """Reads one JSON-RPC message per line from stdin and writes each answer to stdout."""
    for line in sys.stdin:
        if not line.strip():
            continue
        reply = handle(json.loads(line))
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
