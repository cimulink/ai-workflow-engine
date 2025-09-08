# Resilient AI Workflow Engine

A production-ready reference implementation for building resilient, enterprise-grade AI workflows using LangGraph with human-in-the-loop capabilities.

## Overview

This project demonstrates how to build a robust AI workflow engine that can handle long-running processes, recover from failures, and incorporate human review when needed. It's designed for mission-critical tasks where accuracy and reliability are paramount.

## Features

- **Stateful Workflows**: Built with LangGraph for robust state management
- **Persistent Checkpointing**: Automatic state persistence to SQLite database using SqliteSaver
- **Fault Tolerance**: Graceful recovery from system crashes
- **Human-in-the-Loop**: Streamlit UI for human review and approval
- **Modular Architecture**: Clean separation of concerns for easy maintenance

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  submit.py      │    │   engine.py      │    │    ui.py        │
│ (Submission     │───▶│ (Workflow Engine)│◀──▶│ (Review UI)     │
│  Script)        │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  workflow.db    │
                        │ (SQLite DB)     │
                        └─────────────────┘
```

## Prerequisites

- Python 3.8+
- OpenRouter API key (set as `OPENROUTER_API_KEY` environment variable)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd resilient-ai-workflow-engine
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set your OpenRouter API key:
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```
   On Windows:
   ```cmd
   set OPENROUTER_API_KEY=your-api-key-here
   ```

5. Optionally, specify which model to use (default is openai/gpt-3.5-turbo):
   ```bash
   export OPENROUTER_MODEL="anthropic/claude-3-haiku"
   ```

## Usage

### 1. Submit Documents

Submit documents for processing:
```bash
# Submit content directly
python submit.py --content "Sample invoice content here"

# Or submit content from a file
python submit.py --file path/to/document.txt
```

### 2. Run the Workflow Engine

Process submitted documents:
```bash
python engine.py
```

The engine will process all documents that have been submitted but not yet processed.

**Note**: The engine uses SqliteSaver for persistent checkpointing, which is implemented as a context manager. This ensures that workflow state is properly saved to the database after each step.

### 3. Check Document Status

Check the status of documents in the workflow:
```bash
# Check all documents
python check_status.py

# Check specific document
python check_status.py document-id-here
```

### 4. Review Documents (Human-in-the-Loop)

Start the Streamlit UI for human review:
```bash
streamlit run ui.py
```

Navigate to the provided URL in your browser to review and approve documents that require human validation.

## How It Works

1. **Document Submission**: Documents are submitted via the `submit.py` script which stores them in the database with a "received" status.

2. **Workflow Engine**: The `engine.py` script processes documents with "received" status by running them through the LangGraph workflow.

3. **Workflow Processing**: The workflow processes documents through a series of nodes:
   - Intake Node: Receives and initializes the document
   - Extract Data Node: Uses an LLM to extract structured data
   - Validation Router: Determines if human review is needed
   - Await Human Review Node: Pauses workflow for human intervention (if needed)
   - Finalize Node: Completes the workflow

4. **State Persistence**: After each step, the workflow state is saved to the database using LangGraph's SqliteSaver with proper context manager usage.

5. **Conditional Routing**: Documents are automatically routed based on business rules:
   - If all fields are extracted with high confidence and total amount < $1000, the workflow finalizes automatically
   - Otherwise, the workflow pauses for human review

6. **Human Review**: The Streamlit UI displays documents pending review, allowing users to correct data and approve/resume workflows.

7. **Fault Tolerance**: If the engine crashes, it can be restarted and will resume processing from the last saved checkpoint.

### End-to-End Workflow Diagram

```mermaid
graph TD
    A[Document Submission<br/>submit.py] --> B[Store in Database]
    B --> C[Workflow Engine<br/>engine.py]
    C --> D[Intake Node]
    D --> E[Extract Data Node]
    E --> F[Validation Router]
    F -->|All fields present AND total ≤ $1000| G[Finalize Node]
    F -->|Missing fields OR total > $1000| H[Await Human Review Node]
    H -->|Workflow Paused & State Saved| I[Human Reviews in UI<br/>ui.py]
    I -->|Approve & Resume| J[Workflow Resumes]
    J --> G
    G --> K[Workflow Finalized]
    
    subgraph Database
        L[(workflow.db<br/>State Persistence)]
    end
    
    D -.-> L
    E -.-> L
    F -.-> L
    G -.-> L
    H -.-> L
    
    style H fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#ff9,stroke:#333,stroke-width:2px
```

### Detailed Node Interactions

```mermaid
graph LR
    A[Intake Node] --> B[Extract Data Node]
    B --> C[Validation Router]
    C -->|Pass| D[Finalize Node]
    C -->|Fail| E[Await Human Review]
    E -.-> F((Human Review UI))
    F -.-> G[Resume Workflow]
    G --> D
    
    subgraph Workflow Engine
        A
        B
        C
        D
        E
    end
    
    subgraph External Interaction
        F
    end
    
    style Workflow Engine fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    style External Interaction fill:#f1f8e9,stroke:#33691e,stroke-width:2px
```

### Complete System Architecture with Data Flow

```mermaid
graph TB
    subgraph "User Interface"
        A[submit.py<br/>Document Submission]
        B[ui.py<br/>Human Review Interface]
        C[check_status.py<br/>Status Checking]
    end
    
    subgraph "Core Engine"
        D[engine.py<br/>LangGraph Workflow]
    end
    
    subgraph "Persistence Layer"
        E[(workflow.db<br/>SQLite Database)]
        E1[(Documents Table)]
        E2[(Checkpoints Table)]
        E --> E1
        E --> E2
    end
    
    A -- "1. Submit Document" --> E1
    D -- "2. Process Pending<br/>Documents" --> E1
    D -- "3. Save State" --> E2
    D -- "4. Pause for Review" --> B
    B -- "5. Resume with<br/>Corrected Data" --> D
    D -- "6. Finalize<br/>Workflow" --> E1
    D -- "7. Update State" --> E2
    C -- "Query Status" --> E
    
    style A fill:#e3f2fd,stroke:#1976d2
    style B fill:#fff3e0,stroke:#f57c00
    style C fill:#fce4ec,stroke:#c2185b
    style D fill:#f3e5f5,stroke:#7b1fa2
    style E fill:#e8f5e8,stroke:#388e3c
```

## Project Structure

```
resilient-ai-workflow-engine/
├── engine.py           # Core workflow engine
├── submit.py           # Document submission script
├── ui.py               # Streamlit review interface
├── check_status.py     # Document status checking script
├── workflow.db         # SQLite database (created on first run)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── README.md           # This file
└── sample_invoice.txt  # Sample document for testing
```

## Customization

To adapt this engine for your specific use case:

1. Modify the `DocumentState` schema in `engine.py` to match your document structure
2. Update the data extraction logic to reflect your needs
3. Adjust the business rules in `validation_router` function
4. Customize the Streamlit UI in `ui.py` for your review process

## Success Metrics

- **Time-to-Run**: Set up and run the entire workflow in under 20 minutes
- **Resilience**: Recover from engine crashes without losing workflow state
- **Clarity**: Understand core concepts through well-documented code
- **Extensibility**: Adapt the engine for new use cases with minimal changes

## Future Considerations

- API-driven architecture with FastAPI
- Alternative persistence backends (PostgreSQL, Redis)
- Docker containerization
- Integration with LangSmith for observability

## License

This project is open-source and available under the MIT License.