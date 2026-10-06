"""
BuildingBees Socratic Question Engine
Implements automated inspection checklists across Screen, CTA, API, and Flow nodes.
Detects missing architectural specifications and generates owner-routed questions.
"""

from typing import List, Dict, Any
from .schema import (
    BaseGraphNode,
    NodeLayer,
    ScreenNode,
    CTANode,
    APINode,
    FlowNode,
    QuestionNode,
    QuestionCategory,
    QuestionStatus
)
from .graph import BuildingBeesEngine


class SocraticQuestionEngine:
    def __init__(self, graph: BuildingBeesEngine):
        self.graph = graph

    def inspect_screen(self, screen: ScreenNode) -> List[QuestionNode]:
        questions: List[QuestionNode] = []

        # Check empty state
        if not screen.states.empty or "empty" in screen.states.empty.lower() and len(screen.states.empty) < 15:
            questions.append(QuestionNode(
                target_node_id=screen.id,
                title=f"Empty State Definition for {screen.id}",
                category=QuestionCategory.FRONTEND,
                question_text=f"Screen '{screen.title}' has no detailed empty-state behavior defined. What does a first-time or zero-item user see?",
                is_blocking=False,
                assigned_to="FRONTEND_LEAD"
            ))

        # Check acceptance criteria
        if not screen.acceptance_criteria:
            questions.append(QuestionNode(
                target_node_id=screen.id,
                title=f"Acceptance Criteria Missing for {screen.id}",
                category=QuestionCategory.PM,
                question_text=f"Screen '{screen.title}' has zero formal acceptance criteria. PM review required before agents can build.",
                is_blocking=True,
                assigned_to="PM"
            ))

        return questions

    def inspect_cta(self, cta: CTANode) -> List[QuestionNode]:
        questions: List[QuestionNode] = []

        # Check failure screen and field preservation
        if not cta.target_screen_on_failure:
            questions.append(QuestionNode(
                target_node_id=cta.id,
                title=f"Failure Route Missing for CTA {cta.id}",
                category=QuestionCategory.FRONTEND,
                question_text=f"CTA '{cta.label}' does not specify target screen on API failure. Where is the user redirected?",
                is_blocking=True,
                assigned_to="FRONTEND_LEAD"
            ))

        if not cta.preserved_fields_on_failure:
            questions.append(QuestionNode(
                target_node_id=cta.id,
                title=f"Form Field Preservation on Failure for {cta.id}",
                category=QuestionCategory.FRONTEND,
                question_text=f"If an API called by '{cta.label}' returns an error, which form inputs must remain filled vs cleared?",
                is_blocking=True,
                assigned_to="FRONTEND_LEAD"
            ))

        return questions

    def inspect_api(self, api: APINode) -> List[QuestionNode]:
        questions: List[QuestionNode] = []

        # Check vendor dependency & timeout fallback
        if api.vendor and api.timeout_ms <= 0:
            questions.append(QuestionNode(
                target_node_id=api.id,
                title=f"Vendor Timeout Policy for {api.id}",
                category=QuestionCategory.BACKEND,
                question_text=f"API '{api.title}' relies on third-party vendor '{api.vendor}' without explicit timeout. What is the SLA timeout in ms?",
                is_blocking=True,
                assigned_to="BACKEND_LEAD"
            ))

        # Check idempotency for mutating actions
        if api.method in ["POST", "PUT", "DELETE"] and not api.idempotency_required:
            questions.append(QuestionNode(
                target_node_id=api.id,
                title=f"Idempotency Guarantee for Mutating API {api.id}",
                category=QuestionCategory.BACKEND,
                question_text=f"API '{api.path}' performs a mutating {api.method} operation. Is an Idempotency-Key header enforced to prevent duplicate charges or double records?",
                is_blocking=True,
                assigned_to="BACKEND_LEAD"
            ))

        return questions

    def run_full_graph_inspection(self) -> Dict[str, Any]:
        """
        Executes systematic checklist pass over all nodes in the graph.
        Attaches discovered questions to the graph.
        """
        generated_count = 0
        blocking_count = 0

        for node in list(self.graph.nodes.values()):
            new_questions: List[QuestionNode] = []
            if isinstance(node, ScreenNode):
                new_questions = self.inspect_screen(node)
            elif isinstance(node, CTANode):
                new_questions = self.inspect_cta(node)
            elif isinstance(node, APINode):
                new_questions = self.inspect_api(node)

            for q in new_questions:
                # Avoid duplicate identical questions
                existing = [
                    ex for ex in self.graph.get_questions_for_node(node.id)
                    if ex.title == q.title
                ]
                if not existing:
                    self.graph.add_node(q)
                    self.graph.add_edge(node.id, q.id)
                    generated_count += 1
                    if q.is_blocking:
                        blocking_count += 1

        return {
            "status": "COMPLETED",
            "new_questions_generated": generated_count,
            "blocking_questions": blocking_count,
            "total_nodes_inspected": len(self.graph.nodes)
        }
