"""
AG-UI Server Implementation for the AI Workflow Engine.
This server wraps the existing LangGraph workflow with AG-UI protocol.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ag_ui_protocol import create_server_engine
from ag_ui_protocol.protocol.agent_protocol import AgentProtocol, RunRequest
from pydantic import BaseModel

# Import existing workflow components
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.engine import DocumentProcessor, create_workflow, setup_database
from shared.types import AgentState, WorkflowStatus, DocumentExtractedData, ValidationResult, WorkflowEvent
from shared.database import WorkflowDatabase


class DocumentWorkflowAgent(AgentProtocol):
    """AG-UI compatible document workflow agent"""
    
    def __init__(self):
        self.legacy_processor = DocumentProcessor()
        self.db = WorkflowDatabase()
        self.current_workflow_id = None
        self.current_message_id = None
    
    def create_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create AG-UI protocol event"""
        return {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "workflow_id": self.current_workflow_id
        }
    
    async def run(self, request: RunRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """Main AG-UI run method - streams workflow execution"""
        
        # Extract document content from messages
        document_content = ""
        for message in request.messages:
            if message.role == "user":
                document_content += message.content + "\n"
        
        if not document_content.strip():
            yield self.create_event("RUN_ERROR", {
                "error": "No document content provided"
            })
            return
        
        # Initialize workflow
        self.current_workflow_id = str(uuid.uuid4())[:8]
        self.current_message_id = str(uuid.uuid4())
        
        # Create initial agent state
        agent_state = AgentState(
            workflow_id=self.current_workflow_id,
            status=WorkflowStatus.RECEIVED,
            current_step="initialization",
            document_content=document_content.strip(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save initial state
        self.db.save_agent_state(agent_state)
        
        # Emit RUN_STARTED
        yield self.create_event("RUN_STARTED", {
            "run_id": self.current_workflow_id,
            "agent_name": "Document Workflow Agent",
            "workflow_id": self.current_workflow_id
        })
        
        try:
            # Stream the workflow execution
            async for event in self.execute_workflow_stream(agent_state):
                yield event
                
        except Exception as e:
            # Handle errors
            error_event = WorkflowEvent(
                workflow_id=self.current_workflow_id,
                event_type="ERROR",
                data={"error": str(e)},
                timestamp=datetime.now().isoformat(),
                step_name="error_handling"
            )
            self.db.add_workflow_event(error_event)
            
            yield self.create_event("RUN_ERROR", {
                "error": str(e),
                "workflow_id": self.current_workflow_id
            })
    
    async def execute_workflow_stream(self, state: AgentState) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the workflow with streaming updates"""
        
        # Step 1: Document Intake
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": f"📄 Processing document {state.workflow_id}...\n",
            "message_id": self.current_message_id
        })
        
        # Update state
        state.status = WorkflowStatus.PROCESSING
        state.current_step = "intake"
        state.updated_at = datetime.now()
        self.db.save_agent_state(state)
        
        # Add event
        intake_event = WorkflowEvent(
            workflow_id=state.workflow_id,
            event_type="INTAKE_STARTED",
            data={"document_length": len(state.document_content)},
            timestamp=datetime.now().isoformat(),
            step_name="intake"
        )
        self.db.add_workflow_event(intake_event)
        
        await asyncio.sleep(0.5)  # Simulate processing
        
        # Step 2: Data Extraction
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": "🤖 Extracting structured data using AI...\n",
            "message_id": self.current_message_id
        })
        
        # Perform extraction
        async for event in self.stream_data_extraction(state):
            yield event
        
        # Update state with extracted data
        state = self.db.get_agent_state(state.workflow_id)
        
        # Step 3: Validation
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": "✅ Validating extracted data...\n",
            "message_id": self.current_message_id
        })
        
        validation_result = await self.validate_data(state)
        
        # Update state with validation result
        state.validation_result = validation_result
        state.updated_at = datetime.now()
        self.db.save_agent_state(state)
        
        # Step 4: Decision point
        if validation_result.needs_review:
            # Human review required
            yield self.create_event("TEXT_MESSAGE_CHUNK", {
                "content": f"⚠️ Document requires human review: {', '.join(validation_result.reasons)}\n",
                "message_id": self.current_message_id
            })
            
            # Create review UI component
            async for event in self.create_review_ui_component(state):
                yield event
            
            # Mark as needing review
            state.status = WorkflowStatus.PENDING_REVIEW
            state.human_review_required = True
            state.current_step = "awaiting_review"
            state.updated_at = datetime.now()
            self.db.save_agent_state(state)
            
            # Add to review queue
            self.db.add_to_review_queue(
                state.workflow_id, 
                "; ".join(validation_result.reasons)
            )
            
            yield self.create_event("HUMAN_INPUT_REQUIRED", {
                "workflow_id": state.workflow_id,
                "reasons": validation_result.reasons,
                "extracted_data": state.extracted_data.model_dump() if state.extracted_data else {}
            })
            
        else:
            # Auto-approve and finalize
            yield self.create_event("TEXT_MESSAGE_CHUNK", {
                "content": "✅ Document approved automatically. Finalizing...\n",
                "message_id": self.current_message_id
            })
            
            await self.finalize_workflow(state)
        
        # Emit final status
        final_state = self.db.get_agent_state(state.workflow_id)
        yield self.create_event("RUN_FINISHED", {
            "status": final_state.status.value,
            "workflow_id": final_state.workflow_id,
            "final_data": final_state.extracted_data.model_dump() if final_state.extracted_data else {}
        })
    
    async def stream_data_extraction(self, state: AgentState) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the data extraction process"""
        
        # Simulate streaming LLM processing
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": "Processing with DeepSeek model...\n",
            "message_id": self.current_message_id
        })
        
        # Use legacy processor for actual extraction
        try:
            # Create a mock state for legacy processor
            legacy_state = {
                "id": state.workflow_id,
                "content": state.document_content,
                "status": "processing",
                "extracted_data": None,
                "workflow_history": [],
                "reason_for_review": None,
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            }
            
            # Run extraction
            result_state = self.legacy_processor.extract_data_node(legacy_state)
            
            # Convert back to AG-UI format
            extracted_data_dict = result_state.get("extracted_data", {})
            
            if "error" not in extracted_data_dict:
                extracted_data = DocumentExtractedData(**extracted_data_dict)
                
                # Update agent state
                state.extracted_data = extracted_data
                state.current_step = "extraction_complete"
                state.updated_at = datetime.now()
                self.db.save_agent_state(state)
                
                # Emit extracted data as tool result
                yield self.create_event("TOOL_CALL_CHUNK", {
                    "tool_call_id": "extract_data",
                    "tool_name": "document_extractor",
                    "parent_message_id": self.current_message_id,
                    "arguments": json.dumps(extracted_data_dict)
                })
                
                yield self.create_event("TEXT_MESSAGE_CHUNK", {
                    "content": f"✅ Extracted {len(extracted_data_dict)} data fields\n",
                    "message_id": self.current_message_id
                })
            else:
                # Extraction error
                yield self.create_event("TEXT_MESSAGE_CHUNK", {
                    "content": f"❌ Extraction error: {extracted_data_dict['error']}\n",
                    "message_id": self.current_message_id
                })
                
        except Exception as e:
            yield self.create_event("TEXT_MESSAGE_CHUNK", {
                "content": f"❌ Extraction failed: {str(e)}\n",
                "message_id": self.current_message_id
            })
    
    async def validate_data(self, state: AgentState) -> ValidationResult:
        """Validate extracted data using legacy validation logic"""
        
        if not state.extracted_data:
            return ValidationResult(
                is_valid=False,
                needs_review=True,
                reasons=["No data extracted"],
                auto_approved=False,
                validation_rules_applied=["data_presence_check"]
            )
        
        # Use legacy validation router logic
        extracted_data = state.extracted_data.model_dump()
        reasons = []
        rules_applied = []
        
        # Invoice validation
        if extracted_data.get("total_amount") is not None:
            rules_applied.append("invoice_validation")
            
            if not extracted_data.get("vendor_name"):
                reasons.append("Missing vendor name")
            
            if not extracted_data.get("invoice_id"):
                reasons.append("Missing invoice ID")
            
            amount = extracted_data.get("total_amount")
            if amount and float(amount) > 1000:
                reasons.append("Amount exceeds $1000 threshold")
        
        # Support ticket validation
        elif extracted_data.get("sentiment"):
            rules_applied.append("support_ticket_validation")
            
            sentiment = extracted_data.get("sentiment", "").lower()
            if sentiment == "irate":
                reasons.append("Customer sentiment is irate")
            
            topic = extracted_data.get("topic", "").lower()
            if "security" in topic or "vulnerability" in topic:
                reasons.append("Security-related issue")
        
        # Generic validation
        else:
            rules_applied.append("generic_validation")
            empty_fields = [k for k, v in extracted_data.items() if v is None or v == ""]
            if empty_fields:
                reasons.extend([f"Missing field: {field}" for field in empty_fields])
        
        needs_review = len(reasons) > 0
        
        return ValidationResult(
            is_valid=not needs_review,
            needs_review=needs_review,
            reasons=reasons,
            auto_approved=not needs_review,
            validation_rules_applied=rules_applied
        )
    
    async def create_review_ui_component(self, state: AgentState) -> AsyncGenerator[Dict[str, Any], None]:
        """Create interactive review UI component"""
        
        yield self.create_event("GENERATIVE_UI", {
            "component": "DocumentReview",
            "props": {
                "workflowId": state.workflow_id,
                "extractedData": state.extracted_data.model_dump() if state.extracted_data else {},
                "reviewReasons": state.validation_result.reasons if state.validation_result else [],
                "originalContent": state.document_content,
                "onApprove": {"action": "approve_document"},
                "onReject": {"action": "reject_document"},
                "onUpdate": {"action": "update_document_data"}
            }
        })
    
    async def finalize_workflow(self, state: AgentState) -> None:
        """Finalize the workflow"""
        
        state.status = WorkflowStatus.FINALIZED
        state.current_step = "finalized"
        state.human_review_required = False
        state.updated_at = datetime.now()
        
        # Save final state
        self.db.save_agent_state(state)
        
        # Remove from review queue if present
        self.db.remove_from_review_queue(state.workflow_id)
        
        # Add finalization event
        final_event = WorkflowEvent(
            workflow_id=state.workflow_id,
            event_type="WORKFLOW_FINALIZED",
            data={"final_status": "completed"},
            timestamp=datetime.now().isoformat(),
            step_name="finalization"
        )
        self.db.add_workflow_event(final_event)


# API endpoints for human review actions
class ReviewActionRequest(BaseModel):
    workflow_id: str
    action: str  # "approve" or "reject"
    updated_data: Optional[Dict[str, Any]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager"""
    # Startup
    print("AG-UI Document Workflow Server starting...")
    yield
    # Shutdown
    print("AG-UI Document Workflow Server shutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Workflow Engine - AG-UI Server",
    description="AG-UI compatible server for document workflow processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create agent instance
workflow_agent = DocumentWorkflowAgent()

# Create AG-UI server engine
ag_ui_engine = create_server_engine(
    agent=workflow_agent,
    app=app
)

# Additional API endpoints
@app.get("/api/workflows/pending")
async def get_pending_reviews():
    """Get workflows pending human review"""
    db = WorkflowDatabase()
    pending_ids = db.get_pending_reviews()
    
    pending_workflows = []
    for workflow_id in pending_ids:
        state = db.get_agent_state(workflow_id)
        if state:
            pending_workflows.append({
                "workflow_id": state.workflow_id,
                "status": state.status.value,
                "extracted_data": state.extracted_data.model_dump() if state.extracted_data else {},
                "validation_reasons": state.validation_result.reasons if state.validation_result else [],
                "created_at": state.created_at.isoformat(),
                "updated_at": state.updated_at.isoformat()
            })
    
    return {"pending_workflows": pending_workflows}

@app.post("/api/workflows/{workflow_id}/approve")
async def approve_workflow(workflow_id: str, request: ReviewActionRequest):
    """Approve a workflow with optional data corrections"""
    db = WorkflowDatabase()
    state = db.get_agent_state(workflow_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if state.status != WorkflowStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="Workflow not pending review")
    
    # Update data if provided
    if request.updated_data and state.extracted_data:
        # Merge updated data
        current_data = state.extracted_data.model_dump()
        current_data.update(request.updated_data)
        state.extracted_data = DocumentExtractedData(**current_data)
    
    # Finalize workflow
    await workflow_agent.finalize_workflow(state)
    
    return {"status": "approved", "workflow_id": workflow_id}

@app.post("/api/workflows/{workflow_id}/reject")
async def reject_workflow(workflow_id: str):
    """Reject a workflow"""
    db = WorkflowDatabase()
    state = db.get_agent_state(workflow_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Mark as rejected
    state.status = WorkflowStatus.ERROR
    state.current_step = "rejected"
    state.error_message = "Rejected by human reviewer"
    state.human_review_required = False
    state.updated_at = datetime.now()
    
    db.save_agent_state(state)
    db.remove_from_review_queue(workflow_id)
    
    return {"status": "rejected", "workflow_id": workflow_id}

@app.get("/api/workflows/{workflow_id}")
async def get_workflow_details(workflow_id: str):
    """Get detailed workflow information"""
    db = WorkflowDatabase()
    state = db.get_agent_state(workflow_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "workflow_id": state.workflow_id,
        "status": state.status.value,
        "current_step": state.current_step,
        "document_content": state.document_content,
        "extracted_data": state.extracted_data.model_dump() if state.extracted_data else {},
        "validation_result": state.validation_result.model_dump() if state.validation_result else {},
        "human_review_required": state.human_review_required,
        "error_message": state.error_message,
        "workflow_history": [event.model_dump() for event in state.workflow_history],
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "ag_ui_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )