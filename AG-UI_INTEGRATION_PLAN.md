# AI Workflow Engine → AG-UI Integration Plan

## Project Overview

**Current State**: A production-ready AI workflow engine built with LangGraph that processes documents with human-in-the-loop capabilities using a Streamlit UI.

**Target State**: Transform the existing workflow engine into a modern, real-time AI agent interface using AG-UI protocol, providing seamless streaming interactions and rich UI components.

## Current Architecture Analysis

### Existing Components
- **engine.py**: Core LangGraph workflow with SQLite checkpointing
- **ui.py**: Streamlit-based review interface for human intervention
- **submit.py**: CLI document submission tool
- **Workflow States**: `received` → `processing` → `pending_review` → `finalized`

### Current Limitations
1. **Batch Processing**: Documents are processed as complete units
2. **Static UI**: Streamlit interface requires manual refresh
3. **Limited Interaction**: No real-time streaming or progressive updates
4. **Separation of Concerns**: UI and processing engine are completely separate
5. **No Tool Integration**: Limited to document processing workflows

## AG-UI Integration Strategy

### Phase 1: Foundation Setup
**Goal**: Establish AG-UI infrastructure alongside existing system

#### 1.1 AG-UI Installation & Setup
```bash
# Install AG-UI TypeScript SDK
cd ai-workflow-engine
npx create-ag-ui-app frontend
cd frontend && npm install

# Install Python AG-UI SDK
pip install ag-ui-protocol
```

#### 1.2 Project Structure Transformation
```
ai-workflow-engine/
├── backend/
│   ├── engine.py              # Legacy LangGraph engine
│   ├── ag_ui_server.py        # New AG-UI server implementation
│   ├── workflow_agent.py      # AG-UI compatible agent
│   └── models/
│       ├── workflow_state.py  # Shared state models
│       └── events.py          # AG-UI event definitions
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DocumentProcessor.tsx
│   │   │   ├── ReviewQueue.tsx
│   │   │   └── WorkflowViewer.tsx
│   │   ├── lib/
│   │   │   └── ag-ui-client.ts
│   │   └── App.tsx
│   └── package.json
├── legacy/
│   ├── ui.py                  # Keep existing Streamlit UI
│   └── submit.py              # Keep existing CLI tool
└── shared/
    ├── database.py            # Shared SQLite operations
    └── types.py              # Common type definitions
```

### Phase 2: AG-UI Server Implementation
**Goal**: Create an AG-UI compatible server that wraps the existing LangGraph workflow

#### 2.1 AG-UI Server Architecture
```python
# backend/ag_ui_server.py
from fastapi import FastAPI
from ag_ui_protocol import AgentServer, AgentProtocol
from typing import AsyncGenerator
import asyncio

class DocumentWorkflowAgent(AgentProtocol):
    def __init__(self):
        self.legacy_processor = DocumentProcessor()  # From engine.py
        
    async def run(self, messages, tools, state) -> AsyncGenerator:
        """Stream workflow execution as AG-UI events"""
        
        # Emit RUN_STARTED
        yield self.create_event("RUN_STARTED", {
            "run_id": str(uuid.uuid4()),
            "agent_name": "Document Workflow Agent"
        })
        
        # Process document with streaming updates
        document_content = self.extract_document_content(messages)
        document_id = str(uuid.uuid4())[:8]
        
        # Stream intake phase
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": f"📄 Processing document {document_id}...\n"
        })
        
        # Initialize state
        state = await self.initialize_workflow_state(document_content, document_id)
        
        # Stream data extraction
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": "🤖 Extracting structured data using AI...\n"
        })
        
        extracted_data = await self.stream_data_extraction(document_content, state)
        
        # Stream validation
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": "✅ Validating extracted data...\n"
        })
        
        validation_result = await self.validate_data(extracted_data)
        
        if validation_result.needs_review:
            # Create interactive review UI
            yield self.create_review_ui_component(extracted_data, validation_result.reasons)
            
            # Wait for human input
            yield self.create_event("HUMAN_INPUT_REQUIRED", {
                "document_id": document_id,
                "reason": validation_result.reasons
            })
            
            # Workflow will pause here until human interaction
            
        else:
            # Auto-approve and finalize
            yield self.create_event("TEXT_MESSAGE_CHUNK", {
                "content": "✅ Document approved automatically. Finalizing...\n"
            })
            
            await self.finalize_workflow(state)
            
        yield self.create_event("RUN_FINISHED", {"status": "completed"})
```

#### 2.2 Streaming Data Extraction
```python
async def stream_data_extraction(self, content: str, state: dict):
    """Stream the data extraction process with real-time updates"""
    
    # Stream LLM processing
    async for chunk in self.stream_llm_extraction(content):
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": f"Processing: {chunk.partial_data}...\n"
        })
    
    # Final extracted data
    extracted_data = await self.complete_extraction(content)
    
    # Emit structured data as a tool result
    yield self.create_event("TOOL_CALL_CHUNK", {
        "tool_call_id": "extract_data",
        "tool_name": "document_extractor",
        "parent_message_id": state["message_id"],
        "arguments": json.dumps(extracted_data)
    })
    
    return extracted_data
```

#### 2.3 Interactive Review Components
```python
def create_review_ui_component(self, extracted_data: dict, reasons: list):
    """Create AG-UI component for human review"""
    
    return self.create_event("GENERATIVE_UI", {
        "component": "DocumentReview",
        "props": {
            "extractedData": extracted_data,
            "reviewReasons": reasons,
            "onApprove": {"action": "approve_document"},
            "onReject": {"action": "reject_document"},
            "onUpdate": {"action": "update_document_data"}
        }
    })
```

### Phase 3: Frontend Implementation
**Goal**: Create a modern, real-time UI using AG-UI client

#### 3.1 React Components Architecture
```typescript
// frontend/src/components/DocumentProcessor.tsx
import { useAgent } from '@ag-ui/client'
import { useState } from 'react'

interface DocumentProcessorProps {
  onWorkflowComplete: (result: any) => void
}

export function DocumentProcessor({ onWorkflowComplete }: DocumentProcessorProps) {
  const [document, setDocument] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  
  const { sendMessage, messages, isRunning, state } = useAgent({
    agentUrl: 'http://localhost:8000/agent',
    onRunFinished: (result) => {
      setIsProcessing(false)
      onWorkflowComplete(result)
    }
  })
  
  const handleSubmit = async () => {
    setIsProcessing(true)
    await sendMessage({
      role: 'user',
      content: document
    })
  }
  
  return (
    <div className="document-processor">
      <div className="input-section">
        <textarea
          value={document}
          onChange={(e) => setDocument(e.target.value)}
          placeholder="Paste your document content here..."
          className="document-input"
          rows={10}
        />
        <button 
          onClick={handleSubmit}
          disabled={!document || isProcessing}
          className="submit-btn"
        >
          {isProcessing ? 'Processing...' : 'Process Document'}
        </button>
      </div>
      
      <div className="processing-stream">
        {messages.map((message, idx) => (
          <div key={idx} className="message">
            {message.content}
          </div>
        ))}
      </div>
      
      <div className="workflow-state">
        {state && (
          <pre>{JSON.stringify(state, null, 2)}</pre>
        )}
      </div>
    </div>
  )
}
```

#### 3.2 Real-time Review Interface
```typescript
// frontend/src/components/ReviewQueue.tsx
import { useAgentSubscriber } from '@ag-ui/client'

export function ReviewQueue() {
  const [pendingReviews, setPendingReviews] = useState([])
  
  const subscriber = useAgentSubscriber({
    onGenerativeUI: ({ component, props }) => {
      if (component === 'DocumentReview') {
        setPendingReviews(prev => [...prev, props])
      }
    },
    
    onHumanInputRequired: ({ document_id, reason }) => {
      // Show notification that review is needed
      showNotification(`Document ${document_id} needs review: ${reason}`)
    }
  })
  
  const handleApprove = async (documentId: string, updatedData: any) => {
    await fetch(`/api/workflows/${documentId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updatedData)
    })
    
    // Remove from pending reviews
    setPendingReviews(prev => 
      prev.filter(review => review.documentId !== documentId)
    )
  }
  
  return (
    <div className="review-queue">
      <h2>Review Queue ({pendingReviews.length})</h2>
      
      {pendingReviews.map(review => (
        <DocumentReviewCard
          key={review.documentId}
          review={review}
          onApprove={handleApprove}
          onReject={(id) => handleReject(id)}
        />
      ))}
    </div>
  )
}
```

#### 3.3 Document Review Card Component
```typescript
// frontend/src/components/DocumentReviewCard.tsx
interface DocumentReviewCardProps {
  review: {
    documentId: string
    extractedData: Record<string, any>
    reviewReasons: string[]
    originalContent: string
  }
  onApprove: (id: string, data: any) => void
  onReject: (id: string) => void
}

export function DocumentReviewCard({ review, onApprove, onReject }: DocumentReviewCardProps) {
  const [editedData, setEditedData] = useState(review.extractedData)
  
  return (
    <div className="review-card">
      <div className="card-header">
        <h3>Document {review.documentId}</h3>
        <div className="review-reasons">
          {review.reviewReasons.map(reason => (
            <span key={reason} className="reason-badge">
              {reason}
            </span>
          ))}
        </div>
      </div>
      
      <div className="card-content">
        <div className="original-content">
          <h4>Original Document</h4>
          <pre>{review.originalContent}</pre>
        </div>
        
        <div className="extracted-data">
          <h4>Extracted Data</h4>
          {Object.entries(editedData).map(([key, value]) => (
            <div key={key} className="data-field">
              <label>{key.replace('_', ' ').toUpperCase()}</label>
              <input
                value={value || ''}
                onChange={(e) => 
                  setEditedData(prev => ({ ...prev, [key]: e.target.value }))
                }
              />
            </div>
          ))}
        </div>
      </div>
      
      <div className="card-actions">
        <button 
          onClick={() => onApprove(review.documentId, editedData)}
          className="approve-btn"
        >
          Approve & Continue
        </button>
        <button 
          onClick={() => onReject(review.documentId)}
          className="reject-btn"
        >
          Reject
        </button>
      </div>
    </div>
  )
}
```

### Phase 4: Enhanced Features
**Goal**: Add advanced AG-UI capabilities for richer interactions

#### 4.1 Tool-based Generative UI
```python
# Advanced workflow with interactive tools
class EnhancedWorkflowAgent(AgentProtocol):
    
    async def create_data_validation_tool(self, extracted_data: dict):
        """Create interactive validation tool"""
        
        yield self.create_event("TOOL_CALL_CHUNK", {
            "tool_call_id": "validate_data",
            "tool_name": "interactive_validator",
            "parent_message_id": self.current_message_id,
            "arguments": json.dumps({
                "data": extracted_data,
                "validation_rules": self.get_validation_rules(),
                "ui_component": {
                    "type": "DataValidator",
                    "props": {
                        "fields": extracted_data,
                        "rules": self.get_validation_rules(),
                        "onValidate": {"action": "validate_field"},
                        "onCorrect": {"action": "correct_field"}
                    }
                }
            })
        })
    
    async def create_progress_tracker(self, workflow_steps: list):
        """Create real-time progress tracking"""
        
        for i, step in enumerate(workflow_steps):
            yield self.create_event("GENERATIVE_UI", {
                "component": "ProgressTracker",
                "props": {
                    "currentStep": i,
                    "totalSteps": len(workflow_steps),
                    "stepName": step.name,
                    "status": step.status,
                    "estimatedTime": step.estimated_time
                }
            })
            
            # Execute the actual step
            await self.execute_workflow_step(step)
```

#### 4.2 Agentic Document Processing
```python
class AgenticDocumentProcessor:
    """AI agent that can make decisions and request human input dynamically"""
    
    async def process_document_intelligently(self, document: str):
        """Process document with dynamic decision making"""
        
        # Analyze document type first
        document_type = await self.classify_document(document)
        
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": f"📋 Detected document type: {document_type}\n"
        })
        
        # Choose processing strategy based on type
        if document_type == "invoice":
            await self.process_invoice_workflow(document)
        elif document_type == "contract":
            await self.process_contract_workflow(document)
        elif document_type == "support_ticket":
            await self.process_support_workflow(document)
        else:
            # Ask human for guidance
            yield self.create_event("GENERATIVE_UI", {
                "component": "DocumentTypeSelector",
                "props": {
                    "document": document,
                    "suggestedTypes": ["invoice", "contract", "support_ticket", "other"],
                    "onSelect": {"action": "set_document_type"}
                }
            })
```

#### 4.3 Multi-Agent Coordination
```python
class WorkflowOrchestrator:
    """Coordinates multiple specialized agents"""
    
    def __init__(self):
        self.agents = {
            "extractor": DataExtractionAgent(),
            "validator": ValidationAgent(), 
            "reviewer": HumanReviewAgent(),
            "finalizer": FinalizationAgent()
        }
    
    async def run_coordinated_workflow(self, document: str):
        """Run workflow with multiple coordinating agents"""
        
        # Start with extraction agent
        extraction_result = await self.agents["extractor"].extract(document)
        
        yield self.create_event("TEXT_MESSAGE_CHUNK", {
            "content": f"🤖 Extraction agent completed. Found {len(extraction_result.fields)} fields.\n"
        })
        
        # Validation agent reviews extraction
        validation_result = await self.agents["validator"].validate(extraction_result)
        
        if validation_result.needs_human_review:
            # Human review agent takes over
            review_result = await self.agents["reviewer"].request_review(
                extraction_result, validation_result.issues
            )
            
            # Wait for human input through AG-UI
            corrected_data = await self.wait_for_human_correction()
            
            # Re-validate with corrected data
            validation_result = await self.agents["validator"].validate(corrected_data)
        
        # Finalizer agent completes the process
        final_result = await self.agents["finalizer"].finalize(validation_result.data)
        
        yield self.create_event("RUN_FINISHED", {
            "result": final_result,
            "agents_used": ["extractor", "validator", "reviewer", "finalizer"]
        })
```

### Phase 5: Advanced Integration Features

#### 5.1 Real-time Collaboration
```typescript
// Multiple users can collaborate on document reviews
export function CollaborativeReview() {
  const { state, sendMessage } = useAgent()
  const [collaborators, setCollaborators] = useState([])
  
  // Real-time updates from other reviewers
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/collaborate')
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data)
      
      if (update.type === 'field_updated') {
        // Show real-time field updates from other users
        showFieldUpdate(update.field, update.value, update.user)
      }
    }
  }, [])
  
  return (
    <div className="collaborative-review">
      <div className="collaborators">
        {collaborators.map(user => (
          <UserAvatar key={user.id} user={user} />
        ))}
      </div>
      
      <div className="document-review">
        <FieldEditor
          onFieldChange={(field, value) => {
            // Broadcast changes to other users
            broadcastFieldChange(field, value)
            // Update local state
            updateField(field, value)
          }}
        />
      </div>
    </div>
  )
}
```

#### 5.2 Audit Trail & Analytics
```python
class WorkflowAnalytics:
    """Track and analyze workflow performance"""
    
    async def track_workflow_metrics(self, workflow_id: str, event: str, data: dict):
        """Track detailed workflow analytics"""
        
        await self.analytics_db.insert({
            "workflow_id": workflow_id,
            "event": event,
            "timestamp": datetime.utcnow(),
            "data": data,
            "user_id": self.current_user_id
        })
        
        # Real-time dashboard updates
        yield self.create_event("ANALYTICS_UPDATE", {
            "metric": event,
            "value": data,
            "workflow_id": workflow_id
        })
    
    async def generate_performance_dashboard(self):
        """Create real-time performance dashboard"""
        
        metrics = await self.get_workflow_metrics()
        
        yield self.create_event("GENERATIVE_UI", {
            "component": "PerformanceDashboard",
            "props": {
                "metrics": {
                    "total_processed": metrics.total_documents,
                    "avg_processing_time": metrics.avg_time,
                    "human_review_rate": metrics.review_rate,
                    "error_rate": metrics.error_rate,
                    "top_failure_reasons": metrics.failure_reasons
                },
                "charts": {
                    "processing_time_trend": metrics.time_series,
                    "document_type_breakdown": metrics.type_breakdown
                }
            }
        })
```

## Implementation Timeline

### Week 1-2: Foundation Setup
- [ ] Install AG-UI SDKs (TypeScript & Python)
- [ ] Set up project structure
- [ ] Create basic AG-UI server wrapper
- [ ] Implement simple streaming for existing workflow

### Week 3-4: Core AG-UI Integration
- [ ] Convert LangGraph workflow to AG-UI compatible events
- [ ] Implement streaming data extraction
- [ ] Create basic React frontend
- [ ] Add real-time progress tracking

### Week 5-6: Interactive Components
- [ ] Build document review components
- [ ] Implement human-in-the-loop via AG-UI
- [ ] Add generative UI for dynamic interactions
- [ ] Create tool-based validation interface

### Week 7-8: Advanced Features
- [ ] Multi-agent coordination
- [ ] Real-time collaboration features
- [ ] Analytics and performance tracking
- [ ] Advanced error handling and recovery

### Week 9-10: Integration & Testing
- [ ] Comprehensive testing of AG-UI workflow
- [ ] Performance optimization
- [ ] UI/UX refinements
- [ ] Documentation and deployment preparation

## Migration Strategy

### Parallel Operation
- Keep existing Streamlit UI operational during development
- Run AG-UI server alongside existing engine.py
- Gradual migration of features from Streamlit to AG-UI
- Shared database layer ensures consistency

### Feature Parity Checklist
- [ ] Document submission and processing
- [ ] Human review queue management
- [ ] Data extraction and validation
- [ ] Workflow state persistence
- [ ] Error handling and recovery
- [ ] Performance monitoring

### Backward Compatibility
- Maintain existing CLI tools (submit.py)
- Keep database schema compatible
- Provide migration path for existing workflows
- Support both interfaces during transition period

## Expected Benefits

### User Experience Improvements
1. **Real-time Processing**: See documents being processed in real-time
2. **Interactive Reviews**: Edit and validate data inline with immediate feedback
3. **Progressive Enhancement**: Rich UI components that adapt to workflow needs
4. **Collaborative Features**: Multiple reviewers can work simultaneously

### Developer Experience Benefits
1. **Modern Architecture**: Event-driven, streaming-first design
2. **Better Debugging**: Real-time visibility into workflow execution
3. **Extensibility**: Easy to add new agents and tools
4. **Type Safety**: Full TypeScript support on frontend

### Operational Improvements  
1. **Reduced Latency**: Streaming responses feel more responsive
2. **Better Resource Usage**: Event-driven processing
3. **Enhanced Monitoring**: Real-time analytics and metrics
4. **Scalability**: AG-UI protocol designed for production scale

## Risk Mitigation

### Technical Risks
- **Learning Curve**: AG-UI is relatively new - allocate time for learning
- **Integration Complexity**: Converting LangGraph to AG-UI events may be challenging
- **Performance**: Streaming may introduce latency - benchmark carefully

### Mitigation Strategies
- Start with simple use cases and gradually add complexity
- Maintain existing system as fallback during development
- Create comprehensive test suite for workflow integrity
- Performance test with realistic document volumes

## Success Metrics

### Functionality Metrics
- [ ] 100% feature parity with existing system
- [ ] Sub-2 second time to first response
- [ ] Real-time streaming of workflow progress
- [ ] Interactive human review completion

### Performance Metrics
- [ ] <500ms response time for document submission
- [ ] Support for 10+ concurrent document processing
- [ ] 99.9% workflow completion rate
- [ ] Zero data loss during migration

### User Experience Metrics
- [ ] Reduced time spent in review queue
- [ ] Improved user satisfaction scores
- [ ] Decreased training time for new users
- [ ] Higher adoption rate compared to Streamlit UI

This plan transforms your existing LangGraph-based workflow engine into a modern, real-time AI agent interface while preserving all existing functionality and adding powerful new capabilities through the AG-UI protocol.