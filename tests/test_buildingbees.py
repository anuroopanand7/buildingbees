"""
BuildingBees Automated Test Suite
Verifies:
1. Core Graph DAG traversal and node registration
2. Socratic Question Engine inspection checklists
3. Stop-Rule enforcement ("Assumption is not approval")
4. Blast radius calculation
5. FastAPI REST API endpoints
"""

import pytest
from starlette.testclient import TestClient

from src.core.graph import BuildingBeesEngine
from src.core.schema import (
    ScreenNode,
    CTANode,
    APINode,
    QuestionNode,
    QuestionStatus,
    NodeStatus
)
from src.data.pcos_fixture import build_pcos_graph
from src.core.question_engine import SocraticQuestionEngine
from src.api.server import app


client = TestClient(app)


def test_pcos_graph_initialization():
    graph = build_pcos_graph()
    assert "USER_PCOS_PATIENT" in graph.nodes
    assert "FLOW_PCOS_PURCHASE" in graph.nodes
    assert "W05_CHECKOUT" in graph.nodes
    assert "API32_DELIVERY_CHECK" in graph.nodes
    assert len(graph.nodes) >= 8


def test_stop_rule_blocks_unverified_branch():
    graph = build_pcos_graph()
    readiness = graph.evaluate_branch_readiness("W05_CHECKOUT")
    # Must be 0.0 because API32 has an open blocking question
    assert readiness.readiness_score == 0.0
    assert readiness.is_build_ready is False
    assert len(readiness.open_blocking_questions) >= 1


def test_question_resolution_unblocks_branch():
    graph = build_pcos_graph()
    readiness = graph.evaluate_branch_readiness("W05_CHECKOUT")
    
    # Resolve all open blocking questions
    for q in readiness.open_blocking_questions:
        q_node = graph.get_node(q.id)
        q_node.question_status = QuestionStatus.ANSWERED
        q_node.answer_text = "Verified architectural fallback decision."

    new_readiness = graph.evaluate_branch_readiness("W05_CHECKOUT")
    assert new_readiness.readiness_score == 1.0
    assert new_readiness.is_build_ready is True


def test_blast_radius_calculation():
    graph = build_pcos_graph()
    blast = graph.get_blast_radius("API32_DELIVERY_CHECK")
    assert "W05_CHECKOUT" in blast["impacted_screens"]
    assert "CTA_W05_CONTINUE" in blast["impacted_ctas"]
    assert "FLOW_PCOS_PURCHASE" in blast["impacted_flows"]


def test_api_endpoints():
    # 1. Root route
    res = client.get("/")
    assert res.status_code == 200

    # 2. Graph state
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] >= 8

    # 3. Branch readiness
    res = client.get("/api/branch-readiness/W05_CHECKOUT")
    assert res.status_code == 200
    assert res.json()["readiness_score"] == 0.0

    # 4. Tracks status
    res = client.get("/api/status")
    assert res.status_code == 200
    tracks = res.json()
    assert "gemini" in tracks

    # 5. Blast radius API
    res = client.get("/api/blast-radius/API32_DELIVERY_CHECK")
    assert res.status_code == 200
    assert res.json()["total_impacted_count"] >= 3
