"""
Canonical PCOS Benchmark Fixture
Models the PCOS Commerce Checkout -> Payment -> Confirmation flow (W05 -> W06 -> W07)
along with API32 (Shiprocket Serviceability) and API42 (Quote Revalidation).
"""

from src.core.schema import (
    UserNode,
    FlowNode,
    ScreenNode,
    ScreenStates,
    CTANode,
    APINode,
    LogicStepNode,
    QuestionNode,
    QuestionStatus,
    QuestionCategory,
    NodeStatus
)
from src.core.graph import SpecGraphEngine


def build_pcos_graph() -> SpecGraphEngine:
    engine = SpecGraphEngine()

    # 1. User Persona
    user = UserNode(
        id="USER_PCOS_PATIENT",
        title="PCOS Patient / Customer",
        description="Patient seeking tailored nutritional, herbal, and hormonal health protocols.",
        flow_ids=["FLOW_PCOS_PURCHASE"]
    )
    engine.add_node(user)

    # 2. Flow
    flow = FlowNode(
        id="FLOW_PCOS_PURCHASE",
        title="PCOS Purchase Flow",
        goal="Order diagnosis-specific supplements and consultations seamlessly.",
        screen_ids=["W05_CHECKOUT", "W06_PAYMENT", "W07_CONFIRMATION"]
    )
    engine.add_node(flow)
    engine.add_edge(user.id, flow.id)

    # 3. Screens
    w05 = ScreenNode(
        id="W05_CHECKOUT",
        title="W05: Checkout & Shipping",
        flow_id=flow.id,
        states=ScreenStates(
            default="Address input form, saved addresses, item breakdown, pincode check",
            loading="Skeleton placeholder for shipping calculations",
            empty="Redirect to cart if cart is empty",
            error="Inline error under pincode if delivery unserviceable. Keep filled address fields."
        ),
        cta_ids=["CTA_W05_CONTINUE"],
        acceptance_criteria=[
            "Pincode must be validated with logistics provider before proceed",
            "Customer can enter alternative shipping address",
            "Subtotal and discounts must be verified before payment gateway redirect"
        ],
        status=NodeStatus.UNDER_REVIEW
    )
    
    w06 = ScreenNode(
        id="W06_PAYMENT",
        title="W06: Payment Selection",
        flow_id=flow.id,
        states=ScreenStates(
            default="UPI, NetBanking, Credit Card, Cash on Delivery options",
            loading="Payment processing spinner with cancel protection",
            empty="Unavailable payment methods hidden",
            error="Payment failure banner with retry button"
        ),
        status=NodeStatus.DRAFT
    )

    w07 = ScreenNode(
        id="W07_CONFIRMATION",
        title="W07: Order Confirmation",
        flow_id=flow.id,
        status=NodeStatus.DRAFT
    )

    engine.add_node(w05)
    engine.add_node(w06)
    engine.add_node(w07)
    engine.add_edge(flow.id, w05.id)
    engine.add_edge(flow.id, w06.id)
    engine.add_edge(flow.id, w07.id)

    # 4. CTA (Connective Tissue)
    cta_w05 = CTANode(
        id="CTA_W05_CONTINUE",
        title="CTA: Continue to Payment",
        parent_screen_id=w05.id,
        label="Continue to Payment",
        preconditions=[
            "Shipping address fields valid",
            "Pincode length == 6 digits",
            "Customer phone number verified via OTP"
        ],
        apis_called=["API32_DELIVERY_CHECK", "API42_QUOTE_REVALIDATE"],
        target_screen_on_success=w06.id,
        target_screen_on_failure=w05.id,
        preserved_fields_on_failure=["address_line1", "address_line2", "city", "state", "pincode", "phone"],
        error_display_type="INLINE",
        debounce_ms=500,
        status=NodeStatus.READY
    )
    engine.add_node(cta_w05)
    engine.add_edge(w05.id, cta_w05.id)

    # 5. APIs
    api32 = APINode(
        id="API32_DELIVERY_CHECK",
        title="API32: Shiprocket Delivery Serviceability",
        method="POST",
        path="/api/v1/logistics/serviceability",
        service="Logistics Integration Service",
        vendor="Shiprocket",
        inputs_schema={"pincode": "string", "weight_grams": "int"},
        outputs_schema={"is_serviceable": "bool", "estimated_days": "int", "cod_available": "bool"},
        timeout_ms=3000,
        cache_ttl_seconds=3600,
        calling_screen_ids=[w05.id],
        status=NodeStatus.UNDER_REVIEW
    )

    api42 = APINode(
        id="API42_QUOTE_REVALIDATE",
        title="API42: Price Quote Revalidation",
        method="POST",
        path="/api/v1/cart/revalidate",
        service="Cart & Pricing Engine",
        idempotency_required=True,
        timeout_ms=2000,
        calling_screen_ids=[w05.id],
        status=NodeStatus.READY
    )

    engine.add_node(api32)
    engine.add_node(api42)
    engine.add_edge(cta_w05.id, api32.id)
    engine.add_edge(cta_w05.id, api42.id)

    # 6. Socratic Question (Demonstrating Stop Rule)
    question_api32 = QuestionNode(
        id="Q_API32_TIMEOUT",
        title="Handling Shiprocket Upstream Timeout",
        target_node_id=api32.id,
        category=QuestionCategory.BACKEND,
        question_text="If Shiprocket API times out (>3000ms), should the user be blocked from checkout, or do we allow tentative order placement with manual review?",
        is_blocking=True,
        assigned_to="BACKEND_LEAD",
        question_status=QuestionStatus.OPEN
    )
    engine.add_node(question_api32)
    engine.add_edge(api32.id, question_api32.id)

    return engine
