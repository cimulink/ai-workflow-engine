"""
Pure LangGraph + AG-UI Server Implementation
Uses real LangGraph streaming with AG-UI events emitted from nodes
This replaces the manual wrapper approach with true graph execution
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# Fix import paths
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import pure LangGraph processor
from ag_ui_langgraph_processor import AGUILangGraphWorkflow
from shared.types import (
    RunRequest, Message, AgentResponse, AgentState, 
    WorkflowStatus, DocumentExtractedData
)
from shared.database import WorkflowDatabase


class PureLangGraphWorkflowAgent:
    """Pure LangGraph workflow agent with native AG-UI streaming"""
    
    def __init__(self):
        self.langgraph_workflow = AGUILangGraphWorkflow()
        self.db = WorkflowDatabase()
        self.active_workflows = {}  # Track running workflows
    
    async def run(self, request: RunRequest) -> AsyncGenerator[AgentResponse, None]:
        """Run pure LangGraph workflow with AG-UI streaming"""
        
        # Extract document content
        document_content = ""
        for message in request.messages:
            if message.role == "user":
                document_content += message.content + "\n"
        
        if not document_content.strip():
            yield AgentResponse(
                type="RUN_ERROR",
                data={"error": "No document content provided"},
                timestamp=datetime.now().isoformat()
            )
            return
        
        workflow_id = str(uuid.uuid4())
        
        try:
            # Save initial state for database tracking
            initial_agent_state = AgentState(
                workflow_id=workflow_id,
                status=WorkflowStatus.RECEIVED,
                current_step="initializing",
                document_content=document_content.strip(),
                extracted_data=None,
                human_review_required=False,
                reason_for_review=None,
                workflow_history=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.db.save_agent_state(initial_agent_state)
            print(f"[AG-UI] Starting pure LangGraph workflow: {workflow_id}")
            
            # Track active workflow
            self.active_workflows[workflow_id] = {
                "start_time": datetime.now(),
                "status": "running"
            }
            
            # Stream LangGraph workflow execution
            event_count = 0
            async for event in self.langgraph_workflow.run_streaming_workflow(
                document_content.strip(), 
                workflow_id
            ):
                event_count += 1
                
                # Save all events to database  
                from shared.types import WorkflowEvent
                workflow_event = WorkflowEvent(
                    workflow_id=workflow_id,
                    event_type=event.type,
                    data=event.data,
                    timestamp=event.timestamp,
                    step_name=event.data.get("current_step", "unknown")
                )
                self.db.add_workflow_event(workflow_event)
                
                # Update database state on key events
                if event.type in ["STATE_UPDATE", "HUMAN_INPUT_REQUIRED", "RUN_FINISHED"]:
                    try:
                        langgraph_state = self.langgraph_workflow.get_workflow_state(workflow_id)
                        if langgraph_state:
                            updated_state = AgentState(
                                workflow_id=workflow_id,
                                status=langgraph_state.get("status", "processing"),
                                current_step=langgraph_state.get("current_step", "unknown"),
                                document_content=langgraph_state.get("document_content", ""),
                                extracted_data=langgraph_state.get("extracted_data"),
                                human_review_required=langgraph_state.get("human_review_required", False),
                                reason_for_review=langgraph_state.get("reason_for_review"),
                                workflow_history=langgraph_state.get("workflow_history", []),
                                created_at=langgraph_state.get("created_at", initial_agent_state.created_at),
                                updated_at=datetime.now()
                            )
                            self.db.save_agent_state(updated_state)
                            
                            # Add to review queue if needed
                            if event.type == "HUMAN_INPUT_REQUIRED":
                                self.db.add_to_review_queue(
                                    workflow_id,
                                    langgraph_state.get("reason_for_review", "Review required")
                                )
                    except Exception as state_error:
                        print(f"[AG-UI] Warning: Could not update database state: {state_error}")
                
                yield event
            
            # Mark workflow as completed
            self.active_workflows[workflow_id]["status"] = "completed"
            self.active_workflows[workflow_id]["end_time"] = datetime.now()
            
            print(f"[AG-UI] Workflow {workflow_id} completed with {event_count} events")
            
        except Exception as e:
            print(f"[AG-UI] Error in workflow {workflow_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Mark workflow as failed
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = "failed"
                self.active_workflows[workflow_id]["error"] = str(e)
            
            error_event = AgentResponse(
                type="RUN_ERROR",
                data={"error": str(e), "workflow_id": workflow_id},
                timestamp=datetime.now().isoformat(),
                workflow_id=workflow_id
            )
            
            # Save error event
            from shared.types import WorkflowEvent
            error_workflow_event = WorkflowEvent(
                workflow_id=workflow_id,
                event_type="RUN_ERROR",
                data={"error": str(e)},
                timestamp=datetime.now().isoformat(),
                step_name="error"
            )
            self.db.add_workflow_event(error_workflow_event)
            
            yield error_event
    
    async def resume_workflow(self, workflow_id: str, updated_data: Dict[str, Any] = None) -> bool:
        """Resume paused workflow"""
        try:
            print(f"[AG-UI] Resuming workflow: {workflow_id}")
            
            success = await self.langgraph_workflow.resume_workflow(workflow_id, updated_data)
            
            if success:
                # Update workflow tracking
                if workflow_id in self.active_workflows:
                    self.active_workflows[workflow_id]["status"] = "resumed"
                    self.active_workflows[workflow_id]["resume_time"] = datetime.now()
                
                # Remove from review queue
                self.db.remove_from_review_queue(workflow_id)
                
                print(f"[AG-UI] Successfully resumed workflow: {workflow_id}")
            else:
                print(f"[AG-UI] Failed to resume workflow: {workflow_id}")
                
            return success
            
        except Exception as e:
            print(f"[AG-UI] Error resuming workflow {workflow_id}: {e}")
            return False
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow status"""
        langgraph_state = self.langgraph_workflow.get_workflow_state(workflow_id)
        tracking_info = self.active_workflows.get(workflow_id, {})
        
        return {
            "workflow_id": workflow_id,
            "langgraph_state": langgraph_state,
            "tracking_info": tracking_info,
            "database_state": self.db.get_agent_state(workflow_id)
        }
    
    def get_active_workflows(self) -> Dict[str, Any]:
        """Get all active workflows"""
        return self.active_workflows


# Global workflow instance
workflow_engine: PureLangGraphWorkflowAgent 

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global workflow_engine
    
    print("[AG-UI] Initializing Pure LangGraph Workflow Engine...")
    workflow_engine = PureLangGraphWorkflowAgent()
    yield
    print("[AG-UI] Shutting down Pure LangGraph Workflow Engine...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="AI Workflow Engine - Pure LangGraph + AG-UI",
    description="Real-time document processing using LangGraph with AG-UI streaming",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTTP Streaming Endpoints
@app.post("/agent/run")
async def agent_run(request: RunRequest):
    """Main AG-UI streaming endpoint using pure LangGraph"""
    
    if not workflow_engine:
        raise HTTPException(status_code=503, detail="Workflow engine not initialized")
    
    async def generate():
        try:
            async for event in workflow_engine.run(request):
                event_data = event.model_dump()
                yield f"data: {json.dumps(event_data)}\n\n"
                
        except Exception as e:
            error_event = {
                "type": "RUN_ERROR",
                "data": {"error": str(e)},
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

# WebSocket endpoint (alternative streaming method)
@app.websocket("/agent/ws")
async def agent_websocket(websocket: WebSocket):
    """WebSocket streaming endpoint for bidirectional communication"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "run":
                request = RunRequest(
                    messages=[Message(role="user", content=data.get("content", ""))],
                    tools=data.get("tools", []),
                    state=data.get("state", {})
                )
                
                async for event in workflow_engine.run(request):
                    await websocket.send_json(event.model_dump())
                    
            elif data.get("type") == "resume":
                workflow_id = data.get("workflow_id")
                updated_data = data.get("updated_data", {})
                
                success = await workflow_engine.resume_workflow(workflow_id, updated_data)
                await websocket.send_json({
                    "type": "RESUME_RESPONSE",
                    "success": success,
                    "workflow_id": workflow_id
                })
                
            elif data.get("type") == "status":
                workflow_id = data.get("workflow_id")
                status = workflow_engine.get_workflow_status(workflow_id)
                await websocket.send_json({
                    "type": "STATUS_RESPONSE",
                    "workflow_id": workflow_id,
                    "status": status
                })
    
    except WebSocketDisconnect:
        print("[AG-UI] WebSocket client disconnected")
    except Exception as e:
        print(f"[AG-UI] WebSocket error: {e}")
        await websocket.close(code=1000)

# REST API Endpoints
@app.get("/api/workflows")
async def list_workflows():
    """List all workflows"""
    try:
        workflows = workflow_engine.db.get_all_workflows()
        return {"workflows": workflows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get specific workflow details"""
    try:
        status = workflow_engine.get_workflow_status(workflow_id)
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflows/{workflow_id}/approve")
async def approve_workflow(workflow_id: str, updated_data: Dict[str, Any] = None):
    """Approve workflow and optionally update data"""
    try:
        success = await workflow_engine.resume_workflow(workflow_id, updated_data)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to resume workflow")
        
        return {"success": True, "workflow_id": workflow_id, "message": "Workflow resumed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/pending")
async def get_pending_workflows():
    """Get workflows pending human review"""
    try:
        pending = workflow_engine.db.get_pending_reviews()
        return {"pending_workflows": pending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflows/{workflow_id}/events")
async def get_workflow_events(workflow_id: str):
    """Get all events for a workflow"""
    try:
        events = workflow_engine.db.get_workflow_events(workflow_id)
        return {"workflow_id": workflow_id, "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/status")
async def system_status():
    """Get system status and metrics"""
    try:
        active_workflows = workflow_engine.get_active_workflows()
        
        return {
            "status": "healthy",
            "active_workflows": len(active_workflows),
            "workflow_details": active_workflows,
            "server_type": "Pure LangGraph + AG-UI",
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "server_type": "Pure LangGraph + AG-UI",
            "version": "2.0.0"
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "server": "Pure LangGraph AG-UI Server",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    print("Starting Pure LangGraph + AG-UI Server...")
    print("Features:")
    print("- Real LangGraph workflow execution")
    print("- Native AG-UI event streaming from nodes")
    print("- Custom streaming checkpointer")
    print("- HTTP SSE and WebSocket support")
    print("- State persistence with SQLite")
    
    uvicorn.run(
        "ag_ui_server_pure_langgraph:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )