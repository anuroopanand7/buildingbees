"""
SpecGraph Core Graph Engine
Implements Directed Acyclic Graph (DAG) state management, bidirectional traversal,
blast radius impact analysis, and readiness evaluation.
"""

from typing import Dict, List, Optional, Set, Any
from .schema import (
    BaseGraphNode,
    NodeLayer,
    NodeStatus,
    ScreenNode,
    CTANode,
    APINode,
    LogicStepNode,
    QuestionNode,
    QuestionStatus,
    BranchReadiness
)


class SpecGraphEngine:
    def __init__(self):
        # In-memory node store: ID -> BaseGraphNode
        self.nodes: Dict[str, BaseGraphNode] = {}
        
        # Adjacency lists for graph edges
        # forward_edges: source_id -> set of target_ids
        self.forward_edges: Dict[str, Set[str]] = {}
        # reverse_edges: target_id -> set of source_ids (for blast radius)
        self.reverse_edges: Dict[str, Set[str]] = {}

    def add_node(self, node: BaseGraphNode) -> BaseGraphNode:
        self.nodes[node.id] = node
        if node.id not in self.forward_edges:
            self.forward_edges[node.id] = set()
        if node.id not in self.reverse_edges:
            self.reverse_edges[node.id] = set()
        return node

    def add_edge(self, source_id: str, target_id: str) -> None:
        if source_id not in self.forward_edges:
            self.forward_edges[source_id] = set()
        if target_id not in self.reverse_edges:
            self.reverse_edges[target_id] = set()
            
        self.forward_edges[source_id].add(target_id)
        self.reverse_edges[target_id].add(source_id)

    def get_node(self, node_id: str) -> Optional[BaseGraphNode]:
        return self.nodes.get(node_id)

    def get_questions_for_node(self, node_id: str) -> List[QuestionNode]:
        questions = []
        for n in self.nodes.values():
            if isinstance(n, QuestionNode) and n.target_node_id == node_id:
                questions.append(n)
        return questions

    def get_blast_radius(self, node_id: str) -> Dict[str, Any]:
        """
        Bottom-Up Impact Analysis:
        When a low-level node (e.g. API or Logic Step) is modified or fails,
        traverse upstream to determine every affected CTA, Screen, and Flow.
        """
        visited = set()
        queue = [node_id]
        impacted_nodes: List[BaseGraphNode] = []
        
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            
            node = self.nodes.get(curr)
            if node and curr != node_id:
                impacted_nodes.append(node)
                
            # Traverse reverse edges (who depends on this node?)
            for upstream in self.reverse_edges.get(curr, set()):
                if upstream not in visited:
                    queue.append(upstream)
                    
        return {
            "root_node_id": node_id,
            "total_impacted_count": len(impacted_nodes),
            "impacted_screens": [n.id for n in impacted_nodes if n.layer == NodeLayer.SCREEN],
            "impacted_ctas": [n.id for n in impacted_nodes if n.layer == NodeLayer.CTA],
            "impacted_flows": [n.id for n in impacted_nodes if n.layer == NodeLayer.FLOW],
            "all_impacted_node_details": [n.dict() for n in impacted_nodes]
        }

    def evaluate_branch_readiness(self, screen_id: str) -> BranchReadiness:
        """
        Calculates whether a screen branch (Screen -> CTAs -> APIs -> Logic) is ready to build.
        Core Rule: "Assumption is not approval"
        If ANY node in the branch has an open blocking question, Readiness = 0.0.
        """
        screen = self.nodes.get(screen_id)
        if not screen or not isinstance(screen, ScreenNode):
            raise ValueError(f"Screen node '{screen_id}' not found.")

        # Collect all nodes in this branch
        branch_nodes: List[BaseGraphNode] = [screen]
        visited_ids = {screen_id}
        
        # Traverse downstream from Screen -> CTAs -> APIs -> Logic
        queue = [screen_id]
        while queue:
            curr = queue.pop(0)
            for downstream_id in self.forward_edges.get(curr, set()):
                if downstream_id not in visited_ids:
                    visited_ids.add(downstream_id)
                    downstream_node = self.nodes.get(downstream_id)
                    if downstream_node and downstream_node.layer != NodeLayer.QUESTION:
                        branch_nodes.append(downstream_node)
                        queue.append(downstream_id)

        # Collect questions attached to any node in this branch
        open_blocking_q: List[QuestionNode] = []
        non_blocking_q: List[QuestionNode] = []
        completeness_reasons: List[str] = []

        for b_node in branch_nodes:
            questions = self.get_questions_for_node(b_node.id)
            for q in questions:
                if q.question_status == QuestionStatus.OPEN:
                    if q.is_blocking:
                        open_blocking_q.append(q)
                    else:
                        non_blocking_q.append(q)

            # Node completeness checks
            if isinstance(b_node, ScreenNode):
                if not b_node.states.loading or not b_node.states.error:
                    completeness_reasons.append(f"Screen {b_node.id} missing explicit loading/error states")
            elif isinstance(b_node, CTANode):
                if not b_node.target_screen_on_failure:
                    completeness_reasons.append(f"CTA {b_node.id} missing failure fallback destination")
            elif isinstance(b_node, APINode):
                if b_node.timeout_ms <= 0:
                    completeness_reasons.append(f"API {b_node.id} missing defined timeout constraint")

        # Evaluate final readiness score
        if open_blocking_q:
            score = 0.0
            is_ready = False
            completeness_reasons.append(f"BLOCKED: {len(open_blocking_q)} open blocking questions remain unresolved.")
        else:
            base_score = 1.0 - (len(completeness_reasons) * 0.1)
            score = max(0.0, min(1.0, base_score))
            is_ready = score >= 0.8

        return BranchReadiness(
            branch_id=f"branch_{screen_id}",
            screen_id=screen_id,
            readiness_score=round(score, 2),
            is_build_ready=is_ready,
            total_nodes=len(branch_nodes),
            open_blocking_questions=open_blocking_q,
            non_blocking_questions=non_blocking_q,
            completeness_reasons=completeness_reasons
        )
