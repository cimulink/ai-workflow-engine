"""
Pure LangGraph + AG-UI Integration
Uses real LangGraph streaming with AG-UI events emitted from nodes
"""

import os
import json
import uuid
import sqlite3
import asyncio
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, AsyncGenerator
from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.base import Checkpoint
try:
    from langgraph.checkpoint.base import CheckpointMetadata
except ImportError:
    # Fallback for older versions
    CheckpointMetadata = dict
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv

# Fix import path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.types import AgentResponse, AgentState, WorkflowStatus, DocumentExtractedData

load_dotenv()

# AG-UI Compatible LangGraph State
class AGUIWorkflowState(TypedDict):
    # Core workflow data
    workflow_id: str
    document_content: str
    extracted_data: Optional[Dict[str, Any]]
    
    # AG-UI specific fields
    current_step: str
    status: str  # WorkflowStatus enum values
    human_review_required: bool
    reason_for_review: Optional[str]
    
    # Event streaming callback
    stream_callback: Optional[Any]  # AsyncGenerator callback
    
    # History tracking
    workflow_history: List[str]
    created_at: str
    updated_at: str

class AGUIStreamingCheckpointer(SqliteSaver):
    """Custom checkpointer that emits AG-UI events on state changes"""
    
    def __init__(self, conn: sqlite3.Connection, stream_callback=None):
        super().__init__(conn)
        self.stream_callback = stream_callback
        
    async def aput(self, config, checkpoint: Checkpoint, metadata: dict):
        """Override to emit AG-UI events when state is saved"""
        result = await super().aput(config, checkpoint, metadata)
        
        if self.stream_callback and checkpoint.channel_values:
            state_data = checkpoint.channel_values
            
            # Emit state update event (safely handle both dict and object formats)
            workflow_id = None
            if isinstance(state_data, dict):
                workflow_id = state_data.get("workflow_id")
            else:
                workflow_id = getattr(state_data, "workflow_id", None)
            
            if workflow_id:
                event_data = {
                    "workflow_id": workflow_id,
                    "current_step": state_data.get("current_step") if isinstance(state_data, dict) else getattr(state_data, "current_step", "unknown"),
                    "status": state_data.get("status") if isinstance(state_data, dict) else getattr(state_data, "status", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
                
                try:
                    await self.stream_callback("STATE_UPDATE", event_data)
                except Exception as e:
                    print(f"[AG-UI] Warning: Could not emit state update event: {e}")
            
        return result

class AGUIDocumentProcessor:
    """LangGraph processor with native AG-UI event emission"""
    
    def __init__(self, stream_callback=None):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free"),
            temperature=0,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        self.stream_callback = stream_callback
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit AG-UI event if callback is available"""
        if self.stream_callback:
            await self.stream_callback(event_type, data)
    
    async def intake_node(self, state: AGUIWorkflowState) -> AGUIWorkflowState:
        """Initialize workflow with AG-UI events"""
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": f"🔄 Starting document processing...\n",
            "workflow_id": state["workflow_id"]
        })
        
        current_time = datetime.now().isoformat()
        
        # Update state
        state["current_step"] = "intake"
        state["status"] = "processing"
        state["workflow_history"].append(f"Document received at {current_time}")
        state["updated_at"] = current_time
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": f"📄 Document ID: {state['workflow_id']}\n",
            "workflow_id": state["workflow_id"]
        })
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": f"📊 Content length: {len(state['document_content'])} characters\n",
            "workflow_id": state["workflow_id"]
        })
        
        print(f"[AG-UI] Processing document {state['workflow_id']}")
        return state
    
    async def extract_data_node(self, state: AGUIWorkflowState) -> AGUIWorkflowState:
        """Extract data with real-time progress updates"""
        workflow_id = state["workflow_id"]
        current_time = datetime.now().isoformat()
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": "🔍 Analyzing document structure...\n",
            "workflow_id": workflow_id
        })
        
        # Update step
        state["current_step"] = "extract_data"
        state["updated_at"] = current_time
        
        extraction_prompt = """
        You are a document processing assistant. Extract the following information from the given document text:
        
        For invoices:
        - vendor_name: The name of the vendor/company
        - invoice_id: The invoice number or ID
        - due_date: The payment due date
        - total_amount: The total amount due (as a number)
        
        For customer support tickets:
        - customer_name: Customer's name
        - email: Customer's email
        - topic: Main topic/category
        - sentiment: Customer sentiment (Happy, Neutral, Frustrated, Irate)
        - urgency: Urgency level (Low, Medium, High, Critical)
        
        Return the extracted data as a JSON object. If you cannot find a field, set it to null.
        If the document doesn't clearly match either category, try to extract whatever structured information you can.
        """
        
        try:
            await self._emit_event("TEXT_MESSAGE_CHUNK", {
                "content": "🤖 Calling LLM for data extraction...\n",
                "workflow_id": workflow_id
            })
            
            messages = [
                SystemMessage(content=extraction_prompt),
                HumanMessage(content=f"Document content:\n{state['document_content']}")
            ]
            
            # Make LLM call
            response = self.llm.invoke(messages)
            
            await self._emit_event("TEXT_MESSAGE_CHUNK", {
                "content": "📝 Processing LLM response...\n",
                "workflow_id": workflow_id
            })
            
            # Parse JSON response
            try:
                extracted_data = json.loads(response.content)
                
                # Count extracted fields
                field_count = len([v for v in extracted_data.values() if v is not None])
                
                await self._emit_event("TEXT_MESSAGE_CHUNK", {
                    "content": f"✅ Successfully extracted {field_count} data fields\n",
                    "workflow_id": workflow_id
                })
                
            except json.JSONDecodeError:
                # Fallback JSON parsing
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    await self._emit_event("TEXT_MESSAGE_CHUNK", {
                        "content": "⚠️ Used fallback JSON parsing\n",
                        "workflow_id": workflow_id
                    })
                else:
                    extracted_data = {"error": "Failed to parse LLM response as JSON"}
                    await self._emit_event("TEXT_MESSAGE_CHUNK", {
                        "content": "❌ Failed to parse LLM response\n",
                        "workflow_id": workflow_id
                    })
            
            # Update state
            state["extracted_data"] = extracted_data
            state["workflow_history"].append(f"Data extracted at {current_time}")
            
            # Emit structured data event
            await self._emit_event("TOOL_CALL_CHUNK", {
                "tool_call_id": f"extract_data_{workflow_id}",
                "tool_name": "document_extractor",
                "arguments": json.dumps(extracted_data),
                "workflow_id": workflow_id
            })
            
            print(f"[AG-UI] Extracted data for {workflow_id}: {extracted_data}")
            
        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            
            await self._emit_event("TEXT_MESSAGE_CHUNK", {
                "content": f"❌ ERROR: {error_msg}\n",
                "workflow_id": workflow_id
            })
            
            state["extracted_data"] = {"error": error_msg}
            state["status"] = "error"
            state["workflow_history"].append(f"Extraction failed at {current_time}: {error_msg}")
            
            await self._emit_event("RUN_ERROR", {
                "error": error_msg,
                "workflow_id": workflow_id
            })
            
            print(f"[AG-UI] Error extracting data from {workflow_id}: {error_msg}")
        
        return state
    
    def validation_router(self, state: AGUIWorkflowState) -> str:
        """Route workflow based on validation rules"""
        workflow_id = state["workflow_id"]
        extracted_data = state.get("extracted_data", {})
        
        print(f"[AG-UI] Validating document {workflow_id}")
        
        # Basic validation
        if not extracted_data or "error" in extracted_data:
            print(f"[AG-UI] Document {workflow_id} requires review: Missing or invalid data")
            return "await_human_review"
        
        reasons = []
        
        # Invoice validation rules
        if "total_amount" in extracted_data:
            if not extracted_data.get("vendor_name"):
                reasons.append("Missing vendor name")
            if not extracted_data.get("invoice_id"):
                reasons.append("Missing invoice ID")
                
            # Amount threshold check
            amount = extracted_data.get("total_amount")
            if amount:
                try:
                    numeric_amount = float(str(amount).replace("$", "").replace(",", ""))
                    if numeric_amount > 1000:
                        reasons.append("Amount exceeds $1000 threshold")
                except (ValueError, TypeError):
                    reasons.append("Invalid amount format")
        
        # Customer support validation
        elif "sentiment" in extracted_data:
            sentiment = extracted_data.get("sentiment", "").lower()
            topic = extracted_data.get("topic", "").lower()
            
            if sentiment == "irate":
                reasons.append("Customer sentiment is irate")
            if "security" in topic or "vulnerability" in topic:
                reasons.append("Security-related issue")
        
        # Generic validation - check for missing fields
        else:
            empty_fields = [k for k, v in extracted_data.items() if v is None or v == ""]
            if empty_fields:
                reasons.extend([f"Missing field: {field}" for field in empty_fields])
        
        if reasons:
            print(f"[AG-UI] Document {workflow_id} requires review: {'; '.join(reasons)}")
            return "await_human_review"
        
        print(f"[AG-UI] Document {workflow_id} passed validation")
        return "finalize"
    
    async def await_human_review_node(self, state: AGUIWorkflowState) -> AGUIWorkflowState:
        """Pause workflow for human review with interactive UI"""
        workflow_id = state["workflow_id"]
        current_time = datetime.now().isoformat()
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": "⏸️ Workflow requires human review\n",
            "workflow_id": workflow_id
        })
        
        # Calculate review reasons
        extracted_data = state.get("extracted_data", {})
        reasons = []
        
        if not extracted_data or "error" in extracted_data:
            reasons.append("Missing or invalid extracted data")
        else:
            # Check specific validation rules
            if "total_amount" in extracted_data:
                if not extracted_data.get("vendor_name"):
                    reasons.append("Missing vendor name")
                if not extracted_data.get("invoice_id"):
                    reasons.append("Missing invoice ID")
                    
                amount = extracted_data.get("total_amount")
                if amount:
                    try:
                        numeric_amount = float(str(amount).replace("$", "").replace(",", ""))
                        if numeric_amount > 1000:
                            reasons.append("Amount exceeds $1000 threshold")
                    except (ValueError, TypeError):
                        reasons.append("Invalid amount format")
            
            elif "sentiment" in extracted_data:
                sentiment = extracted_data.get("sentiment", "").lower()
                topic = extracted_data.get("topic", "").lower()
                
                if sentiment == "irate":
                    reasons.append("Customer sentiment is irate")
                if "security" in topic or "vulnerability" in topic:
                    reasons.append("Security-related issue")
            
            else:
                empty_fields = [k for k, v in extracted_data.items() if v is None or v == ""]
                if empty_fields:
                    reasons.extend([f"Missing field: {field}" for field in empty_fields])
        
        reason_text = "; ".join(reasons) if reasons else "Unknown validation issue"
        
        # Update state
        state["current_step"] = "await_human_review"
        state["status"] = "pending_review"
        state["human_review_required"] = True
        state["reason_for_review"] = reason_text
        state["workflow_history"].append(f"Paused for review at {current_time}: {reason_text}")
        state["updated_at"] = current_time
        
        # Emit review reasons
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": f"📋 Review needed: {reason_text}\n",
            "workflow_id": workflow_id
        })
        
        # Emit interactive review component
        await self._emit_event("GENERATIVE_UI", {
            "component": "DataReviewForm",
            "props": {
                "workflow_id": workflow_id,
                "extracted_data": extracted_data,
                "reasons": reasons,
                "review_url": f"/api/workflows/{workflow_id}/approve"
            },
            "workflow_id": workflow_id
        })
        
        # Emit human input required event
        await self._emit_event("HUMAN_INPUT_REQUIRED", {
            "workflow_id": workflow_id,
            "reasons": reasons,
            "extracted_data": extracted_data
        })
        
        print(f"[AG-UI] Document {workflow_id} awaiting human review: {reason_text}")
        return state
    
    async def finalize_node(self, state: AGUIWorkflowState) -> AGUIWorkflowState:
        """Finalize workflow with completion events"""
        workflow_id = state["workflow_id"]
        current_time = datetime.now().isoformat()
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": "🎯 Finalizing workflow...\n",
            "workflow_id": workflow_id
        })
        
        # Update state
        state["current_step"] = "finalize"
        state["status"] = "finalized"
        state["human_review_required"] = False
        state["workflow_history"].append(f"Workflow finalized at {current_time}")
        state["updated_at"] = current_time
        
        # Save results to file
        output_file = f"output_{workflow_id}.json"
        output_data = {
            "document_id": workflow_id,
            "extracted_data": state["extracted_data"],
            "workflow_history": state["workflow_history"],
            "finalized_at": current_time
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": f"💾 Results saved to {output_file}\n",
            "workflow_id": workflow_id
        })
        
        await self._emit_event("TEXT_MESSAGE_CHUNK", {
            "content": "✅ Workflow completed successfully!\n",
            "workflow_id": workflow_id
        })
        
        # Final completion event
        await self._emit_event("RUN_FINISHED", {
            "workflow_id": workflow_id,
            "status": "completed",
            "final_data": state["extracted_data"],
            "output_file": output_file
        })
        
        print(f"[AG-UI] Document {workflow_id} processing completed successfully")
        return state

class AGUILangGraphWorkflow:
    """Main workflow class that integrates LangGraph with AG-UI streaming"""
    
    def __init__(self):
        self.processor = None
        self.checkpointer = None
        self.app = None
        self.current_stream_callback = None
    
    def setup_database(self) -> AGUIStreamingCheckpointer:
        """Initialize AG-UI compatible checkpointer"""
        os.makedirs("./checkpoints", exist_ok=True)
        db_path = "./checkpoints/agui_workflow.db"
        
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            return AGUIStreamingCheckpointer(conn, self.current_stream_callback)
        except Exception as e:
            print(f"Warning: Database setup issue: {e}")
            # Fallback to in-memory
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            return AGUIStreamingCheckpointer(conn, self.current_stream_callback)
    
    def create_workflow(self) -> StateGraph:
        """Create LangGraph workflow with AG-UI integration"""
        
        # Create the state graph
        workflow = StateGraph(AGUIWorkflowState)
        
        # Add nodes (processor will be set with stream callback)
        workflow.add_node("intake", self.processor.intake_node)
        workflow.add_node("extract_data", self.processor.extract_data_node)
        workflow.add_node("await_human_review", self.processor.await_human_review_node)
        workflow.add_node("finalize", self.processor.finalize_node)
        
        # Set entry point
        workflow.set_entry_point("intake")
        
        # Add edges
        workflow.add_edge("intake", "extract_data")
        workflow.add_conditional_edges(
            "extract_data",
            self.processor.validation_router,
            {
                "await_human_review": "await_human_review",
                "finalize": "finalize"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("finalize", END)
        
        # After human review, re-validate
        workflow.add_conditional_edges(
            "await_human_review", 
            self.processor.validation_router,
            {
                "await_human_review": "await_human_review",  # Still needs review
                "finalize": "finalize"  # Can now finalize
            }
        )
        
        return workflow
    
    async def run_streaming_workflow(
        self, 
        document_content: str, 
        workflow_id: str = None
    ) -> AsyncGenerator[AgentResponse, None]:
        """Run LangGraph workflow with AG-UI event streaming"""
        
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())
        
        # Create event queue for streaming
        event_queue = asyncio.Queue()
        
        # Stream callback to capture events from nodes
        async def stream_callback(event_type: str, data: Dict[str, Any]):
            event = AgentResponse(
                type=event_type,
                data=data,
                timestamp=datetime.now().isoformat(),
                workflow_id=workflow_id
            )
            await event_queue.put(event)
        
        # Set up processor and workflow with streaming
        self.current_stream_callback = stream_callback
        self.processor = AGUIDocumentProcessor(stream_callback)
        self.checkpointer = self.setup_database()
        
        workflow = self.create_workflow()
        self.app = workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_after=["await_human_review"]
        )
        
        # Emit workflow start event
        start_event = AgentResponse(
            type="RUN_STARTED",
            data={
                "workflow_id": workflow_id,
                "agent_name": "LangGraph Document Processor",
                "document_length": len(document_content)
            },
            timestamp=datetime.now().isoformat(),
            workflow_id=workflow_id
        )
        yield start_event
        
        # Initial state
        initial_state = AGUIWorkflowState(
            workflow_id=workflow_id,
            document_content=document_content,
            extracted_data=None,
            current_step="start",
            status="received",
            human_review_required=False,
            reason_for_review=None,
            stream_callback=stream_callback,
            workflow_history=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        config = {"configurable": {"thread_id": workflow_id}}
        
        # Start workflow execution in background
        async def run_workflow():
            try:
                async for state_chunk in self.app.astream(initial_state, config):
                    # LangGraph streaming - each chunk represents node completion
                    print(f"[AG-UI] LangGraph step completed: {list(state_chunk.keys())}")
                
                # Mark workflow as complete if it finished without interruption
                final_state = self.app.get_state(config)
                if final_state and final_state.values.get("status") == "finalized":
                    await stream_callback("WORKFLOW_COMPLETE", {
                        "workflow_id": workflow_id,
                        "final_status": "finalized"
                    })
                
            except Exception as e:
                await stream_callback("RUN_ERROR", {
                    "workflow_id": workflow_id,
                    "error": str(e)
                })
            finally:
                # Signal completion
                await event_queue.put(None)
        
        # Start workflow task
        workflow_task = asyncio.create_task(run_workflow())
        
        # Stream events as they occur
        try:
            while True:
                event = await event_queue.get()
                if event is None:  # End marker
                    break
                yield event
                
        except Exception as e:
            print(f"[AG-UI] Error in event streaming: {e}")
            error_event = AgentResponse(
                type="RUN_ERROR",
                data={"error": str(e), "workflow_id": workflow_id},
                timestamp=datetime.now().isoformat(),
                workflow_id=workflow_id
            )
            yield error_event
        
        # Wait for workflow completion
        try:
            await workflow_task
        except Exception as e:
            print(f"[AG-UI] Workflow task error: {e}")
    
    def get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get current workflow state"""
        if not self.app:
            return None
            
        config = {"configurable": {"thread_id": workflow_id}}
        try:
            state = self.app.get_state(config)
            return state.values if state else None
        except Exception as e:
            print(f"[AG-UI] Error getting workflow state: {e}")
            return None
    
    async def resume_workflow(self, workflow_id: str, updated_data: Dict[str, Any] = None) -> bool:
        """Resume paused workflow with optional data updates"""
        if not self.app:
            return False
            
        config = {"configurable": {"thread_id": workflow_id}}
        
        try:
            # Get current state
            current_state = self.app.get_state(config)
            if not current_state:
                print(f"[AG-UI] No workflow found for {workflow_id}")
                return False
            
            # Update state if needed
            if updated_data:
                new_state = current_state.values.copy()
                if "extracted_data" in new_state and isinstance(new_state["extracted_data"], dict):
                    new_state["extracted_data"].update(updated_data)
                
                new_state["workflow_history"].append(f"Human review completed at {datetime.now().isoformat()}")
                new_state["updated_at"] = datetime.now().isoformat()
                new_state["human_review_required"] = False
                
                # Update the state
                self.app.update_state(config, new_state)
                print(f"[AG-UI] Updated workflow state with: {list(updated_data.keys())}")
            
            # Resume workflow
            async for state_chunk in self.app.astream(None, config):
                print(f"[AG-UI] Resumed workflow step: {list(state_chunk.keys())}")
            
            return True
            
        except Exception as e:
            print(f"[AG-UI] Error resuming workflow: {e}")
            return False