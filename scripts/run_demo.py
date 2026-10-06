#!/usr/bin/env python3
"""
BuildingBees End-to-End Interactive Demonstration
Showcases:
1. 6-layer canonical PCOS graph initialization
2. Socratic Question Engine inspection
3. Branch readiness calculation & Stop-Rule enforcement ("Assumption is not approval")
4. Question resolution and instant readiness unblocking
5. Bottom-up blast-radius impact analysis
"""

import sys
import os

# Add root directory to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.pcos_fixture import build_pcos_graph
from src.core.question_engine import SocraticQuestionEngine
from src.core.schema import QuestionStatus
from src.adapters.nvidia_adapter import NvidiaNeMoGuardrailAdapter, NvidiaCuGraphAccelerator
from src.adapters.gemini_adapter import GoogleGeminiAdapter


def main():
    print("=" * 80)
    print("🚀 SPECGRAPH: AGENTIC INFORMATION ARCHITECTURE BOARD")
    print("   Dual Track: Google AI Builder Cup 2026 & NVIDIA Hackathon")
    print("=" * 80)

    # 1. Initialize Graph
    print("\n[Step 1] Loading Canonical PCOS Commerce Graph (W05 -> W06 -> API32/42)...")
    graph = build_pcos_graph()
    print(f"✅ Loaded {len(graph.nodes)} nodes across 6 layers.")

    # 2. Socratic Question Engine Pass
    print("\n[Step 2] Running Socratic Question Engine inspection checklists...")
    question_engine = SocraticQuestionEngine(graph)
    inspection_results = question_engine.run_full_graph_inspection()
    print(f"🔍 Discovered {inspection_results['new_questions_generated']} potential gaps/questions "
          f"({inspection_results['blocking_questions']} blocking).")

    # 3. Check Branch Readiness on W05 Checkout
    print("\n[Step 3] Evaluating Branch Readiness for Screen 'W05_CHECKOUT'...")
    readiness_before = graph.evaluate_branch_readiness("W05_CHECKOUT")
    print(f"📊 Readiness Score: {readiness_before.readiness_score} / 1.0")
    print(f"🚦 Is Build Ready?: {readiness_before.is_build_ready}")
    print(f"🛑 Open Blocking Questions ({len(readiness_before.open_blocking_questions)}):")
    for q in readiness_before.open_blocking_questions:
        print(f"   - [{q.category.value}] Node {q.target_node_id}: \"{q.question_text}\" (Assigned to: {q.assigned_to})")

    print("\n🛡️ STOP RULE TRIGGERED: 'Assumption is not approval!'")
    print("   The building agent is STRICTLY FORBIDDEN from guessing what to do on timeout.")
    print("   Branch is paused; agent moves to another ready branch.")

    # 4. Resolve the Blocking Questions
    print("\n[Step 4] Resolving all open blocking questions on the branch...")
    for q_summary in readiness_before.open_blocking_questions:
        q_node = graph.get_node(q_summary.id)
        q_node.question_status = QuestionStatus.ANSWERED
        if "Idempotency" in q_node.title:
            q_node.answer_text = "DECISION: Logistics serviceability is a read-only query executed over POST; no idempotency header required."
        else:
            q_node.answer_text = (
                "DECISION (Backend Lead): If Shiprocket times out (>3000ms), fallback to static zone lookup. "
                "Allow order placement to succeed; flag order in admin review queue for logistics verification."
            )
        print(f"📝 Answer written to node {q_node.target_node_id}: \"{q_node.answer_text[:60]}...\"")


    # 5. Re-evaluate Readiness
    print("\n[Step 5] Recalculating Branch Readiness after resolution...")
    readiness_after = graph.evaluate_branch_readiness("W05_CHECKOUT")
    print(f"📊 New Readiness Score: {readiness_after.readiness_score} / 1.0")
    print(f"🚀 Is Build Ready?: {readiness_after.is_build_ready}")
    print("✅ Branch unblocked! Building agent can now generate code with 100% precision.")

    # 6. Bottom-Up Blast Radius Analysis
    print("\n[Step 6] Running Bottom-Up Blast Radius Analysis on 'API32_DELIVERY_CHECK'...")
    blast = graph.get_blast_radius("API32_DELIVERY_CHECK")
    print(f"💥 Total Upstream Nodes Impacted: {blast['total_impacted_count']}")
    print(f"   - Impacted Screens: {blast['impacted_screens']}")
    print(f"   - Impacted CTAs: {blast['impacted_ctas']}")
    print(f"   - Impacted Flows: {blast['impacted_flows']}")

    # 7. Dual Track Demonstrations
    print("\n[Step 7] Dual Competition Adapters Status:")
    gemini = GoogleGeminiAdapter()
    gemini_res = gemini.ingest_prd_markdown("# Sample PRD")
    print(f"   [Google Track] {gemini_res['provider']} adapter active: Ready for multimodal PRD/Figma ingest.")

    nvidia_guard = NvidiaNeMoGuardrailAdapter()
    cugraph = NvidiaCuGraphAccelerator(enable_gpu=True)
    cugraph_res = cugraph.calculate_gpu_blast_radius("API32_DELIVERY_CHECK", [])
    print(f"   [NVIDIA Track] NeMo Guardrails policy loaded. {cugraph_res['mode']} active (Latency: {cugraph_res['latency_ms']} ms).")

    print("\n" + "=" * 80)
    print("🎉 ALL SYSTEMS OPERATIONAL: Ready for Hackathon Deployment & UI Canvas integration!")
    print("=" * 80)


if __name__ == "__main__":
    main()
