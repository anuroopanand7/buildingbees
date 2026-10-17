"""BuildingBees as an MCP server, so a coding agent (Claude Code, Cursor, Codex) can read a plan and talk back to
the bees while it builds (idea from Archify, Roger, 18 Oct 2026). Standard library only; speaks MCP over stdio.

Add it to Claude Code:
    claude mcp add buildingbees -- python3 scripts/mcp_server.py
Every tool takes `board`: the board id, or a board link (https://.../?board=<id>).
BUILDINGBEES_URL points at another deployment (default: the live site).
"""

import json
import os
import sys
import urllib.parse
import urllib.request

BASE = os.getenv("BUILDINGBEES_URL", "https://buildingbees-853213660594.asia-south1.run.app").rstrip("/")

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
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read().decode("utf-8")
    return json.loads(raw) if r.headers.get_content_type() == "application/json" else raw


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
        return "\n".join(f"- [{ids.get(q['target_node_id'], q['target_node_id'])}] {q['question_text']}"
                         + (" (needed before building)" if q.get("is_blocking") else "") for q in open_qs) or "Nothing is open."
    if name == "add_note":
        _call("/api/comments", b, {"target": args["target"], "step": int(args.get("step") or 0), "text": args["text"], "by": "Coding agent"})
        return "Note added. The team sees it, and the bees apply it when the round is processed."
    raise ValueError(f"Unknown tool {name}")


def handle(msg: dict):
    """Answers one MCP JSON-RPC message; returns None for notifications."""
    method, mid = msg.get("method"), msg.get("id")
    if method == "initialize":
        result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "buildingbees", "version": "1.0"}}
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
