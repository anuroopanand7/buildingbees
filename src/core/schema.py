"""
SpecGraph Core Domain Schema
Defines strongly typed representations for the 6-layer Agentic Information Architecture.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uuid
import datetime


class NodeLayer(str, Enum):
    USER = "USER"
    FLOW = "FLOW"
    SCREEN = "SCREEN"
    CTA = "CTA"
    API = "API"
    LOGIC_STEP = "LOGIC_STEP"
    QUESTION = "QUESTION"
    CHANGE = "CHANGE"


class NodeStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    READY = "READY"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    BLOCKED = "BLOCKED"


class QuestionStatus(str, Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    DISMISSED = "DISMISSED"


class QuestionCategory(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    PM = "PM"
    COMPLIANCE = "COMPLIANCE"


class BaseGraphNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    layer: NodeLayer
    description: Optional[str] = ""
    owner: str = "PM"  # PM, FRONTEND, BACKEND
    status: NodeStatus = NodeStatus.DRAFT
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.USER
    persona_type: str = "CUSTOMER"  # CUSTOMER, ADMIN, VENDOR
    flow_ids: List[str] = Field(default_factory=list)


class FlowNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.FLOW
    goal: str = ""
    screen_ids: List[str] = Field(default_factory=list)  # Ordered sequence


class ScreenStates(BaseModel):
    default: str = "Default populated screen"
    loading: str = "Skeleton loading state"
    empty: str = "Zero state / Empty placeholder"
    error: str = "Full-page or contextual error container"


class ScreenNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.SCREEN
    owner: str = "FRONTEND"
    flow_id: str
    states: ScreenStates = Field(default_factory=ScreenStates)
    cta_ids: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    figma_url: Optional[str] = None


class CTANode(BaseGraphNode):
    """
    The Connective Tissue of SpecGraph.
    Connects screens to the APIs they trigger and routes outcomes on success or failure.
    """
    layer: NodeLayer = NodeLayer.CTA
    owner: str = "FRONTEND"
    parent_screen_id: str
    label: str
    preconditions: List[str] = Field(default_factory=list)  # e.g. Form valid, PIN filled
    apis_called: List[str] = Field(default_factory=list)   # IDs of API nodes
    
    # Success route
    target_screen_on_success: str
    
    # Failure route
    target_screen_on_failure: str
    preserved_fields_on_failure: List[str] = Field(default_factory=list)
    error_display_type: str = "INLINE"  # INLINE, TOAST, MODAL
    
    # Resiliency & UX Policies
    debounce_ms: int = 500
    allow_retry: bool = True
    max_retries: int = 3


class APINode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.API
    owner: str = "BACKEND"
    method: str = "POST"  # GET, POST, PUT, DELETE
    path: str
    service: str
    vendor: Optional[str] = None  # e.g. "Shiprocket", "Razorpay"
    inputs_schema: Dict[str, Any] = Field(default_factory=dict)
    outputs_schema: Dict[str, Any] = Field(default_factory=dict)
    error_codes: Dict[Union[int, str], Dict[str, str]] = Field(default_factory=dict)
    idempotency_required: bool = False
    timeout_ms: int = 3000
    cache_ttl_seconds: int = 0
    calling_screen_ids: List[str] = Field(default_factory=list)
    logic_step_ids: List[str] = Field(default_factory=list)


class LogicStepNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.LOGIC_STEP
    owner: str = "BACKEND"
    api_id: str
    step_order: int = 1
    edge_cases: List[str] = Field(default_factory=list)
    vendor_down_fallback: Optional[str] = None


class QuestionNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.QUESTION
    target_node_id: str
    category: QuestionCategory = QuestionCategory.BACKEND
    question_text: str
    is_blocking: bool = True  # If true, halts build loop for this branch
    assigned_to: str = "BACKEND_LEAD"
    question_status: QuestionStatus = QuestionStatus.OPEN
    answer_text: Optional[str] = None
    answered_at: Optional[str] = None


class BranchReadiness(BaseModel):
    branch_id: str
    screen_id: str
    readiness_score: float  # 0.0 to 1.0
    is_build_ready: bool
    total_nodes: int
    open_blocking_questions: List[QuestionNode] = Field(default_factory=list)
    non_blocking_questions: List[QuestionNode] = Field(default_factory=list)
    completeness_reasons: List[str] = Field(default_factory=list)
