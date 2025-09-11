"""
Shared type definitions for the AI Workflow Engine.
"""

from typing import TypedDict, List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class WorkflowStatus(str, Enum):
    """Workflow status enumeration"""
    RECEIVED = "received"
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    FINALIZED = "finalized"
    ERROR = "error"


class WorkflowState(TypedDict):
    """Legacy workflow state structure (for compatibility)"""
    id: str
    content: str
    status: str
    extracted_data: Optional[Dict[str, Any]]
    workflow_history: List[str]
    reason_for_review: Optional[str]
    created_at: str
    updated_at: str


class DocumentExtractedData(BaseModel):
    """Structured extracted data from documents"""
    # Invoice fields
    vendor_name: Optional[str] = None
    invoice_id: Optional[str] = None
    due_date: Optional[str] = None
    total_amount: Optional[float] = None
    
    # Support ticket fields
    customer_name: Optional[str] = None
    email: Optional[str] = None
    topic: Optional[str] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    
    # Generic fields
    document_type: Optional[str] = None
    confidence_score: Optional[float] = None
    extraction_timestamp: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of document validation"""
    is_valid: bool
    needs_review: bool
    reasons: List[str]
    auto_approved: bool
    validation_rules_applied: List[str]


class WorkflowEvent(BaseModel):
    """AG-UI workflow event"""
    event_type: str
    data: Dict[str, Any]
    timestamp: str
    workflow_id: str
    step_name: Optional[str] = None


class Message(BaseModel):
    """AG-UI message format"""
    role: str
    content: str


class RunRequest(BaseModel):
    """AG-UI run request format"""
    messages: List[Message]
    tools: Optional[List[Dict]] = []
    state: Optional[Dict] = {}


class AgentResponse(BaseModel):
    """AG-UI agent response event"""
    type: str
    data: Dict[str, Any]
    timestamp: str
    workflow_id: Optional[str] = None


class AgentState(BaseModel):
    """AG-UI compatible agent state"""
    workflow_id: str
    status: WorkflowStatus
    current_step: str
    document_content: str
    extracted_data: Optional[DocumentExtractedData] = None
    validation_result: Optional[ValidationResult] = None
    workflow_history: List[str] = []  # Changed to match database
    human_review_required: bool = False
    reason_for_review: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime  # Changed to string for compatibility
    updated_at: datetime  # Changed to string for compatibility
    
    class Config:
        use_enum_values = True