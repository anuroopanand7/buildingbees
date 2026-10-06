"""
SI-Product Core Domain Schema
Defines strongly typed representations for the 5-Stage Evolutionary Pipeline,
The Multi-Agent Hive (Bees), Department Input Boxes, and Dual Hackathon Engine Tracks.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import uuid
import datetime


class EngineTrack(str, Enum):
    GOOGLE_GEMINI = "GOOGLE_GEMINI"
    NVIDIA_NEMO = "NVIDIA_NEMO"


class NodeLayer(str, Enum):
    USER = "USER"
    FLOW = "FLOW"
    SCREEN = "SCREEN"
    CTA = "CTA"
    API = "API"
    LOGIC_STEP = "LOGIC_STEP"
    QUESTION = "QUESTION"
    CHANGE = "CHANGE"


class BeeType(str, Enum):
    QUEEN_PM = "QUEEN_PM"          # Scope, user flow orchestration, business readiness
    FRONTEND_BEE = "FRONTEND_BEE"  # UI hierarchy, Loading/Empty/Error states, form retention
    BACKEND_BEE = "BACKEND_BEE"    # APIs, vendor SLAs, idempotency, timeouts, failure routes
    DESIGNER_BEE = "DESIGNER_BEE"  # Visual layout, CTA contrast, wireframe synthesis
    TESTER_BEE = "TESTER_BEE"      # Test cases, edge cases, Gherkin BDD specs, race conditions


class NodeStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    READY = "READY"
    IMPLEMENTED = "IMPLEMENTED"
    TESTED = "TESTED"
    BLOCKED = "BLOCKED"
    LEVEL_1_DRAFT = "LEVEL_1_DRAFT"             # 20% XP: Initial draft
    LEVEL_2_QUESTIONED = "LEVEL_2_QUESTIONED"   # 50% XP: Bees dropped pollen dots
    LEVEL_3_VERIFIED = "LEVEL_3_VERIFIED"       # 85% XP: Human players answered confirmation Qs
    LEVEL_4_BUILD_READY = "LEVEL_4_BUILD_READY" # 100% XP: Full specs + tests passed, ready for final boss


class QuestionStatus(str, Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    DISMISSED = "DISMISSED"


class QuestionCategory(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DESIGN = "DESIGN"
    TESTER = "TESTER"
    PM = "PM"
    COMPLIANCE = "COMPLIANCE"


class PlayerRole(str, Enum):
    SOLO_FOUNDER = "SOLO_FOUNDER"
    FRONTEND_LEAD = "FRONTEND_LEAD"
    BACKEND_LEAD = "BACKEND_LEAD"
    DESIGN_LEAD = "DESIGN_LEAD"
    QA_LEAD = "QA_LEAD"
    PM_LEAD = "PM_LEAD"


class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: PlayerRole
    skills: List[str] = Field(default_factory=list)
    email: Optional[str] = None


class PlayerRoster(BaseModel):
    is_solo_founder: bool = True
    players: List[Player] = Field(default_factory=list)
    team_rules: List[str] = Field(default_factory=list)


class DepartmentInputs(BaseModel):
    """Dedicated department input boxes on each screen node."""
    frontend_notes: Optional[str] = None
    backend_notes: Optional[str] = None
    design_notes: Optional[str] = None
    qa_test_cases: List[str] = Field(default_factory=list)


class BaseGraphNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    layer: NodeLayer
    description: Optional[str] = ""
    owner: str = "PM"
    status: NodeStatus = NodeStatus.DRAFT
    xp_score: int = 20  # 0 to 100
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.USER
    persona_type: str = "CUSTOMER"
    flow_ids: List[str] = Field(default_factory=list)


class FlowNode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.FLOW
    goal: str = ""
    screen_ids: List[str] = Field(default_factory=list)


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
    visual_mockup_svg: Optional[str] = None
    department_inputs: DepartmentInputs = Field(default_factory=DepartmentInputs)


class CTANode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.CTA
    owner: str = "FRONTEND"
    parent_screen_id: str
    label: str
    preconditions: List[str] = Field(default_factory=list)
    apis_called: List[str] = Field(default_factory=list)
    target_screen_on_success: str
    target_screen_on_failure: str
    preserved_fields_on_failure: List[str] = Field(default_factory=list)
    error_display_type: str = "INLINE"
    debounce_ms: int = 500
    allow_retry: bool = True
    max_retries: int = 3


class APINode(BaseGraphNode):
    layer: NodeLayer = NodeLayer.API
    owner: str = "BACKEND"
    method: str = "POST"
    path: str
    service: str
    vendor: Optional[str] = None
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
    is_blocking: bool = True
    assigned_to: str = "BACKEND_LEAD"
    question_status: QuestionStatus = QuestionStatus.OPEN
    author_bee: BeeType = BeeType.BACKEND_BEE
    suggested_options: List[str] = Field(default_factory=list)
    answer_text: Optional[str] = None
    answered_at: Optional[str] = None


# PollenDot is the gamified Hive alias for QuestionNode
PollenDot = QuestionNode


class BranchReadiness(BaseModel):
    branch_id: str
    screen_id: str
    readiness_score: float  # 0.0 to 1.0
    xp_percentage: int = 20  # 0 to 100
    is_build_ready: bool
    total_nodes: int = 0
    open_blocking_questions: List[QuestionNode] = Field(default_factory=list)
    non_blocking_questions: List[QuestionNode] = Field(default_factory=list)
    completeness_reasons: List[str] = Field(default_factory=list)
