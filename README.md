# Resilient AI Workflow Engine

A production-ready reference implementation for building resilient, enterprise-grade AI workflows using LangGraph. This project demonstrates how to architect stateful, asynchronous, and fault-tolerant systems with seamless "human-in-the-loop" (HITL) capabilities.

## 🎯 Overview

This is not another AI chatbot demo. It's a **production-ready pattern** for developers building mission-critical AI systems where accuracy, auditability, and recovery from failure are paramount.

### Key Features

- ✅ **Persistent Checkpointing**: SQLite-based state management that survives crashes
- 🔄 **Workflow Interruption & Resumption**: Seamless human-in-the-loop integration  
- 🛡️ **Fault Tolerance**: Complete workflow recovery after system restarts
- 🎛️ **Human Review Interface**: Streamlit-based UI for document validation
- 📊 **Structured Data Extraction**: LLM-powered document processing with validation
- 🏗️ **Modular Architecture**: Clean separation of concerns for easy extension

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenRouter API key

### Installation

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd ai-workflow-engine
   pip install -r requirements.txt
   ```

2. **Configure API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

3. **Test the system**:
   ```bash
   python test_workflow.py
   ```

4. **Submit documents**:
   ```bash
   # Submit sample invoice
   python submit.py --sample
   
   # Submit custom content
   python submit.py "Invoice from Acme Corp for $500"
   
   # Submit from file
   python submit.py --file invoice.txt
   ```

5. **Review queue UI**:
   ```bash
   streamlit run ui.py
   ```

## 📋 Use Cases

### Invoice Processing
- **Automatic Approval**: Invoices under $1,000 with complete data
- **Human Review**: Large amounts, missing fields, or validation failures
- **Data Extraction**: Vendor name, invoice ID, due date, total amount

### Customer Support Tickets  
- **Automatic Routing**: Standard inquiries processed automatically
- **Escalation**: Irate customers or security issues flagged for review
- **Data Extraction**: Sentiment, topic, urgency, customer details

## 🏗️ Architecture & Flow Diagrams

### System Architecture Overview

```mermaid
graph TB
    subgraph "Input Layer"
        CLI[submit.py<br/>CLI Submission]
        FILE[File Input<br/>sample_invoice.txt]
        SAMPLE[Sample Data<br/>--sample flag]
    end
    
    subgraph "Processing Engine"
        ENGINE[engine.py<br/>LangGraph Workflow]
        OPENROUTER[OpenRouter API<br/>DeepSeek Model]
        ENGINE -.-> OPENROUTER
    end
    
    subgraph "Persistence Layer"
        DB[(workflow.db<br/>SQLite Checkpoints)]
        FILES[Output Files<br/>output_*.json]
    end
    
    subgraph "Human Interface"
        UI[ui.py<br/>Streamlit Dashboard]
        QUEUE[Review Queue<br/>Pending Documents]
        UI --> QUEUE
    end
    
    CLI --> ENGINE
    FILE --> CLI
    SAMPLE --> CLI
    
    ENGINE <--> DB
    ENGINE --> FILES
    
    UI <--> DB
    UI --> ENGINE
    
    classDef input fill:#e1f5fe
    classDef processing fill:#f3e5f5
    classDef storage fill:#e8f5e8
    classDef interface fill:#fff3e0
    
    class CLI,FILE,SAMPLE input
    class ENGINE,OPENROUTER processing
    class DB,FILES storage
    class UI,QUEUE interface
```

### LangGraph Workflow Node Structure

```mermaid
graph TD
    START([Document Submitted]) --> INTAKE[intake_node<br/>Initialize State]
    
    INTAKE --> EXTRACT[extract_data_node<br/>LLM Processing<br/>OpenRouter API]
    
    EXTRACT --> VALIDATE{validation_router<br/>Business Rules Check}
    
    VALIDATE -->|Pass Validation<br/>Amount < $1000<br/>All Required Fields| FINALIZE[finalize_node<br/>Save Results<br/>Mark Complete]
    
    VALIDATE -->|Fail Validation<br/>Amount > $1000<br/>Missing Fields<br/>Security Issues| REVIEW[await_human_review_node<br/>Set Status: pending_review<br/>INTERRUPT WORKFLOW]
    
    FINALIZE --> END1([Workflow Complete<br/>Status: finalized])
    
    REVIEW --> INTERRUPT{{SYSTEM PAUSE<br/>Human Intervention Required}}
    
    INTERRUPT --> HUMAN[Human Reviews via UI<br/>Edits/Corrects Data<br/>Clicks 'Approve & Resume']
    
    HUMAN --> RESUME[resume_workflow<br/>Update State<br/>Continue Processing]
    
    RESUME --> VALIDATE2{validation_router<br/>Re-check Rules}
    
    VALIDATE2 -->|Now Passes| FINALIZE2[finalize_node<br/>Complete Processing]
    VALIDATE2 -->|Still Fails| REVIEW2[await_human_review_node<br/>Back to Review]
    
    FINALIZE2 --> END2([Workflow Complete<br/>Status: finalized])
    REVIEW2 --> INTERRUPT
    
    classDef startend fill:#c8e6c9
    classDef process fill:#bbdefb
    classDef decision fill:#ffe0b2
    classDef interrupt fill:#ffcdd2
    classDef human fill:#f8bbd9
    
    class START,END1,END2 startend
    class INTAKE,EXTRACT,FINALIZE,FINALIZE2,RESUME process
    class VALIDATE,VALIDATE2 decision
    class REVIEW,REVIEW2,INTERRUPT interrupt
    class HUMAN human
```

### Data Flow & State Transitions

```mermaid
stateDiagram-v2
    [*] --> received : Document Submitted
    received --> processing : intake_node()
    processing --> processing : extract_data_node()
    
    processing --> pending_review : validation_router()<br/>❌ Fails validation
    processing --> finalized : validation_router()<br/>✅ Passes validation
    
    pending_review --> pending_review : Human reviewing<br/>in Streamlit UI
    pending_review --> processing : resume_workflow()<br/>with corrections
    
    finalized --> [*] : Workflow Complete
    
    note right of pending_review
        INTERRUPT POINT
        - System pauses execution
        - State persisted to SQLite
        - Human intervention required
        - Resume via UI approval
    end note
    
    note right of processing
        BUSINESS RULES
        • Amount > $1000 → Review
        • Missing required fields → Review  
        • Irate customer → Review
        • Security topics → Review
    end note
```

### End-to-End System Flow

```mermaid
sequenceDiagram
    participant User
    participant Submit as submit.py
    participant Engine as engine.py
    participant OpenRouter as OpenRouter API
    participant DB as workflow.db
    participant UI as ui.py (Streamlit)
    participant Human as Human Reviewer
    
    %% Document Submission Flow
    User->>Submit: python submit.py --file invoice.txt
    Submit->>Engine: run_workflow(content, doc_id)
    
    %% Initial Processing
    Engine->>DB: Save initial state (received)
    Engine->>Engine: intake_node() → status: processing
    Engine->>OpenRouter: Extract structured data from document
    OpenRouter-->>Engine: {vendor, invoice_id, amount, etc.}
    Engine->>DB: Update state with extracted_data
    
    %% Validation Decision
    Engine->>Engine: validation_router() checks business rules
    
    alt Amount < $1000 & Complete Data
        Engine->>Engine: finalize_node() → status: finalized
        Engine->>DB: Save final state
        Engine-->>Submit: Workflow complete
        Submit-->>User: ✅ Document processed automatically
    else Amount > $1000 OR Missing Data OR Security Issue
        Engine->>Engine: await_human_review_node()
        Engine->>DB: Set status: pending_review
        Engine->>Engine: INTERRUPT workflow
        Engine-->>Submit: Workflow paused for review
        Submit-->>User: ⚠️ Document requires human review
    end
    
    %% Human Review Process
    User->>UI: streamlit run ui.py
    UI->>DB: Query pending workflows
    DB-->>UI: List of documents needing review
    UI-->>Human: Display review queue
    
    Human->>UI: Select document for review
    UI->>DB: Get workflow details
    DB-->>UI: Document content + extracted data + reason
    UI-->>Human: Show document review interface
    
    Human->>UI: Edit data & click "Approve & Resume"
    UI->>Engine: resume_workflow(doc_id, corrected_data)
    
    %% Resume Processing
    Engine->>DB: Update state with corrections
    Engine->>Engine: validation_router() re-check rules
    
    alt Corrected Data Passes Validation
        Engine->>Engine: finalize_node() → status: finalized
        Engine->>DB: Save final state
        Engine-->>UI: Workflow completed
        UI-->>Human: ✅ Document approved & finalized
    else Still Fails Validation
        Engine->>Engine: await_human_review_node()
        Engine->>DB: Keep status: pending_review
        Engine-->>UI: Still needs review
        UI-->>Human: Document returned to queue
    end
```

### Component Interaction Details

```mermaid
graph LR
    subgraph "submit.py - Document Submission"
        SUBMIT_CLI[Command Line Interface]
        SUBMIT_FILE[File Reader]
        SUBMIT_SAMPLE[Sample Generator]
        SUBMIT_LOGIC[Submission Logic]
    end
    
    subgraph "engine.py - Core Workflow"
        PROCESSOR[DocumentProcessor Class]
        NODES[Workflow Nodes]
        ROUTER[Validation Router]
        GRAPH[LangGraph StateGraph]
        CHECKPOINTER[SQLite Checkpointer]
    end
    
    subgraph "ui.py - Human Interface" 
        STREAMLIT[Streamlit Framework]
        QUEUE_UI[Review Queue Display]
        EDIT_UI[Document Edit Interface]
        APPROVAL[Approval Actions]
    end
    
    subgraph "External Services"
        OPENROUTER_API[OpenRouter API<br/>DeepSeek Model]
        SQLITE_DB[(SQLite Database<br/>Persistent Storage)]
    end
    
    SUBMIT_CLI --> SUBMIT_LOGIC
    SUBMIT_FILE --> SUBMIT_LOGIC
    SUBMIT_SAMPLE --> SUBMIT_LOGIC
    SUBMIT_LOGIC --> GRAPH
    
    PROCESSOR --> NODES
    NODES --> ROUTER
    ROUTER --> GRAPH
    GRAPH <--> CHECKPOINTER
    CHECKPOINTER <--> SQLITE_DB
    
    NODES --> OPENROUTER_API
    OPENROUTER_API --> NODES
    
    STREAMLIT --> QUEUE_UI
    QUEUE_UI <--> SQLITE_DB
    EDIT_UI <--> SQLITE_DB
    APPROVAL --> GRAPH
    
    classDef submission fill:#e3f2fd
    classDef core fill:#f1f8e9
    classDef interface fill:#fff8e1
    classDef external fill:#fce4ec
    
    class SUBMIT_CLI,SUBMIT_FILE,SUBMIT_SAMPLE,SUBMIT_LOGIC submission
    class PROCESSOR,NODES,ROUTER,GRAPH,CHECKPOINTER core
    class STREAMLIT,QUEUE_UI,EDIT_UI,APPROVAL interface
    class OPENROUTER_API,SQLITE_DB external
```

### Components

1. **submit.py**: Command-line document submission script with file/sample support
2. **engine.py**: Core LangGraph workflow with OpenRouter integration and state management
3. **ui.py**: Streamlit interface for human review, editing, and workflow approval
4. **workflow.db**: SQLite database for persistent checkpointing and crash recovery

## 🔄 Workflow States

- **received**: Document submitted to system
- **processing**: AI extraction in progress  
- **pending_review**: Paused for human validation
- **finalized**: Processing completed successfully
- **error**: Unrecoverable processing error

## 🧪 Testing & Validation

The system includes comprehensive test scenarios:

```bash
python test_workflow.py
```

Tests cover:
- ✅ Automatic approval (small invoices)
- ⚠️ Human review triggers (large amounts, missing data)
- 🎭 Customer sentiment analysis (irate customers)
- 🔄 Workflow resumption after corrections
- 💾 Crash recovery simulation

## 🛡️ Resilience Features

### Crash Recovery
If the engine process crashes:
1. All workflow state persists in SQLite
2. Restart the engine with `python engine.py`
3. Use the UI to resume any pending workflows
4. No data or progress is lost

### Human Intervention
Documents requiring review are automatically paused:
- Missing or invalid data fields
- Business rule violations (amount thresholds)
- Sentiment analysis flags (irate customers)
- Security-related topics

### State Management
- Complete workflow history tracking
- Atomic state updates with rollback capability
- Thread-safe concurrent processing support
- Audit trail for compliance requirements

## 📊 Success Metrics

- **Time-to-Run**: Complete setup in under 20 minutes
- **Resilience**: Survives engine crashes with full recovery
- **Clarity**: Backend engineers can understand LangGraph concepts immediately  
- **Extensibility**: Easy to adapt for new use cases

## 🔮 Future Enhancements (V2)

- **API Layer**: FastAPI integration for service-oriented architecture
- **Database Options**: PostgreSQL, Redis backend support
- **Containerization**: Docker Compose for one-click deployment
- **Observability**: LangSmith integration for detailed tracing
- **Authentication**: User management and role-based access
- **Batch Processing**: Bulk document processing capabilities

## 🤝 Contributing

This project serves as a reference implementation and learning resource. Contributions that improve clarity, add test cases, or extend functionality are welcome.

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ to bridge the gap between AI demos and production systems.**