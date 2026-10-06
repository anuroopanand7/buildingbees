"""
SpecGraph Model Context Protocol (MCP) Server
Allows autonomous coding agents (Claude Code, Gemini CLI, Cursor, Windsurf)
to query graph specifications, check branch readiness, enforce stop rules,
and post/resolve blocking questions.
"""

import json
from typing import Dict, Any, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("specgraph-mcp")
except ImportError:
    # Graceful mock/fallback for environments without official MCP library (e.g. Python < 3.10)
    class FastMCPFallback:
        def __init__(self, name: str):
            self.name = name
            self.tools = {}

        def tool(self):
            def decorator(fn):
                self.tools[fn.__name__] = fn
                return fn
            return decorator

        def run(self):
            print(f"[{self.name}] FastMCP running in stdio simulation mode.")

    mcp = FastMCPFallback("specgraph-mcp")

from src.core.graph import SpecGraphEngine
from src.core.schema import (
    NodeStatus,
    QuestionNode,
    QuestionStatus,
    QuestionCategory
)
from src.data.pcos_fixture import build_pcos_graph
from src.core.question_engine import SocraticQuestionEngine


# Shared in-memory graph instance (initialized with PCOS canonical fixture)
graph_instance: SpecGraphEngine = build_pcos_graph()
question_engine_instance = SocraticQuestionEngine(graph_instance)


@mcp.tool()
def list_nodes(layer: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List nodes in the SpecGraph information architecture.
    Optionally filter by layer: 'USER', 'FLOW', 'SCREEN', 'CTA', 'API', 'QUESTION'.
    """
    results = []
    for node in graph_instance.nodes.values():
        if layer and node.layer.value != layer.upper():
            continue
        results.append({
            "id": node.id,
            "title": node.title,
            "layer": node.layer.value,
            "owner": node.owner,
            "status": node.status.value
        })
    return results


@mcp.tool()
def get_node_details(node_id: str) -> Dict[str, Any]:
    """
    Retrieve full structured specification for a specific node,
    including states, schemas, attached questions, and upstream/downstream edges.
    """
    node = graph_instance.get_node(node_id)
    if not node:
        return {"error": f"Node '{node_id}' not found"}

    downstream = list(graph_instance.forward_edges.get(node_id, set()))
    upstream = list(graph_instance.reverse_edges.get(node_id, set()))
    questions = [q.dict() for q in graph_instance.get_questions_for_node(node_id)]

    return {
        "node": node.dict(),
        "downstream_connections": downstream,
        "upstream_dependents": upstream,
        "questions": questions
    }


@mcp.tool()
def check_branch_readiness(screen_id: str) -> Dict[str, Any]:
    """
    Evaluates if a screen branch is ready for an agent to build.
    Returns readiness score (0.0 - 1.0) and lists any blocking questions.
    Remember: Assumption is not approval! If readiness is 0.0, the agent must NOT guess.
    """
    try:
        readiness = graph_instance.evaluate_branch_readiness(screen_id)
        return readiness.dict()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def post_blocking_question(
    target_node_id: str,
    question_text: str,
    category: str = "BACKEND",
    assigned_to: str = "TECH_LEAD"
) -> Dict[str, Any]:
    """
    Post a blocking question to a node.
    Use this when encountering an unstated requirement or ambiguous edge case.
    Immediately halts the build loop on this branch until answered.
    """
    target = graph_instance.get_node(target_node_id)
    if not target:
        return {"error": f"Target node '{target_node_id}' not found"}

    q_cat = QuestionCategory.BACKEND
    try:
        q_cat = QuestionCategory(category.upper())
    except ValueError:
        pass

    q = QuestionNode(
        target_node_id=target_node_id,
        title=f"Agent Gap Query on {target_node_id}",
        category=q_cat,
        question_text=question_text,
        is_blocking=True,
        assigned_to=assigned_to,
        question_status=QuestionStatus.OPEN
    )

    graph_instance.add_node(q)
    graph_instance.add_edge(target_node_id, q.id)

    return {
        "status": "POSTED",
        "question_id": q.id,
        "message": f"Branch blocked until '{assigned_to}' answers question: {question_text}"
    }


@mcp.tool()
def resolve_question(question_id: str, answer_text: str) -> Dict[str, Any]:
    """
    Answer an open question and write the specification resolution directly into the graph.
    Unblocks the branch and recalculates readiness.
    """
    node = graph_instance.get_node(question_id)
    if not node or not isinstance(node, QuestionNode):
        return {"error": f"Question '{question_id}' not found"}

    node.question_status = QuestionStatus.ANSWERED
    node.answer_text = answer_text

    return {
        "status": "RESOLVED",
        "question_id": question_id,
        "target_node_id": node.target_node_id,
        "message": "Question answered. Specification updated and branch unblocked."
    }


@mcp.tool()
def get_blast_radius(node_id: str) -> Dict[str, Any]:
    """
    Bottom-Up Impact Analysis:
    Determine all screens, CTAs, and user flows affected by a change to an API or logic step.
    """
    return graph_instance.get_blast_radius(node_id)


@mcp.tool()
def record_build_status(
    node_id: str,
    status: str,
    commit_hash: Optional[str] = None
) -> Dict[str, Any]:
    """
    Agent writes back implementation status ('IMPLEMENTED', 'TESTED')
    with an optional Git commit hash or test log link.
    """
    node = graph_instance.get_node(node_id)
    if not node:
        return {"error": f"Node '{node_id}' not found"}

    try:
        node.status = NodeStatus(status.upper())
        if commit_hash:
            node.metadata["commit_hash"] = commit_hash
        return {
            "status": "UPDATED",
            "node_id": node_id,
            "new_status": node.status.value
        }
    except ValueError:
        return {"error": f"Invalid status '{status}'"}


if __name__ == "__main__":
    mcp.run()
