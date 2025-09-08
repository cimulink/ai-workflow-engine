import sqlite3
import uuid
import json
import time
import os
from typing import Annotated, TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langgraph.types import interrupt, Command

# Load environment variables
load_dotenv()

# Define the state schema
class DocumentState(TypedDict):
    document_id: str
    content: str
    status: str  # received, processing, pending_review, finalized, error
    extracted_data: Dict[str, Any]
    workflow_history: list

# Initialize the LLM with OpenRouter
# You'll need to set OPENROUTER_API_KEY in your environment variables
# You can also specify which model to use via OPENROUTER_MODEL environment variable
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
openrouter_model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

# Configure the LLM to use OpenRouter
llm = ChatOpenAI(
    model=openrouter_model,
    openai_api_key=openrouter_api_key,
    openai_api_base="https://openrouter.ai/api/v1",
    temperature=0
)

# Define the nodes
def intake_node(state: DocumentState) -> DocumentState:
    """Intake node that receives raw document content and initializes the workflow state."""
    print(f"Intake node processing document {state['document_id']}")
    
    # Update status and history
    state["status"] = "processing"
    state["workflow_history"].append({
        "node": "intake",
        "timestamp": time.time(),
        "message": f"Document {state['document_id']} received and initialized"
    })
    
    return state

def extract_data_node(state: DocumentState) -> DocumentState:
    """Extract data node that uses an LLM to extract structured data from the document."""
    print(f"Extract data node processing document {state['document_id']}")
    
    # Create a prompt for data extraction
    prompt = PromptTemplate.from_template("""
    Extract the following information from the invoice document:
    - Vendor name
    - Invoice ID
    - Due date
    - Total amount
    
    Document content:
    {content}
    
    Provide the output in JSON format with keys: vendor_name, invoice_id, due_date, total_amount.
    """)
    
    # Create a chain with the prompt and LLM
    chain = prompt | llm
    
    # Get the response from the LLM
    response = chain.invoke({"content": state["content"]})
    
    # Parse the response (in a real implementation, you would use a more robust parser)
    try:
        # For demonstration, we'll create mock data
        # In a real implementation, you would parse the LLM response
        extracted_data = {
            "vendor_name": "ABC Office Supplies Ltd.",
            "invoice_id": "INV-2023-001",
            "due_date": "2023-11-15",
            "total_amount": 3672.00
        }
        state["extracted_data"] = extracted_data
    except Exception as e:
        state["status"] = "error"
        state["workflow_history"].append({
            "node": "extract_data",
            "timestamp": time.time(),
            "message": f"Error extracting data: {str(e)}"
        })
        return state
    
    state["workflow_history"].append({
        "node": "extract_data",
        "timestamp": time.time(),
        "message": "Data extracted successfully",
        "data": state["extracted_data"]
    })
    
    return state

def validation_router(state: DocumentState) -> str:
    """Validation router that determines the next node based on extracted data."""
    print(f"Validation router processing document {state['document_id']}")
    
    extracted_data = state.get("extracted_data", {})
    
    # Business rules:
    # 1. If any field is missing, route to human review
    # 2. If total_amount > 1000, route to human review
    # 3. Otherwise, finalize
    
    missing_fields = []
    for field in ["vendor_name", "invoice_id", "due_date", "total_amount"]:
        if not extracted_data.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        state["workflow_history"].append({
            "node": "validation_router",
            "timestamp": time.time(),
            "message": f"Missing fields detected: {missing_fields}",
            "routing_decision": "pending_review"
        })
        return "pending_review"
    
    total_amount = extracted_data.get("total_amount", 0)
    if total_amount > 1000:
        state["workflow_history"].append({
            "node": "validation_router",
            "timestamp": time.time(),
            "message": f"Total amount {total_amount} exceeds threshold of 1000",
            "routing_decision": "pending_review"
        })
        return "pending_review"
    
    state["workflow_history"].append({
        "node": "validation_router",
        "timestamp": time.time(),
        "message": "Validation passed",
        "routing_decision": "finalize"
    })
    return "finalize"

def await_human_review_node(state: DocumentState) -> DocumentState:
    """Node that pauses the workflow for human review using LangGraph's interrupt feature."""
    print(f"Awaiting human review for document {state['document_id']}")
    
    state["status"] = "pending_review"
    state["workflow_history"].append({
        "node": "await_human_review",
        "timestamp": time.time(),
        "message": "Workflow paused for human review"
    })
    
    # Use LangGraph's interrupt function to pause the workflow
    # This will surface the data for human review
    human_input = interrupt({
        "document_id": state["document_id"],
        "content": state["content"],
        "extracted_data": state["extracted_data"],
        "reason": "Document requires human review due to business rules"
    })
    
    # When resumed, the human_input will contain the reviewed/edited data
    # Update the state with the human-provided data
    if human_input and "extracted_data" in human_input:
        state["extracted_data"] = human_input["extracted_data"]
    
    # Update status to indicate human review is completed
    state["status"] = "processing"
    state["workflow_history"].append({
        "node": "await_human_review",
        "timestamp": time.time(),
        "message": "Human review completed",
        "human_input": human_input
    })
    
    return state

def human_review_completed_node(state: DocumentState) -> DocumentState:
    """Node that processes the workflow after human review is completed."""
    print(f"Processing document after human review {state['document_id']}")
    
    state["status"] = "processing"
    state["workflow_history"].append({
        "node": "human_review_completed",
        "timestamp": time.time(),
        "message": "Human review completed, continuing to finalize"
    })
    
    return state

def finalize_node(state: DocumentState) -> DocumentState:
    """Finalize node that completes the workflow."""
    print(f"Finalizing document {state['document_id']}")
    
    state["status"] = "finalized"
    state["workflow_history"].append({
        "node": "finalize",
        "timestamp": time.time(),
        "message": "Workflow finalized successfully",
        "final_data": state["extracted_data"]
    })
    
    # In a real implementation, you would save the data to a file or database
    print(f"Finalized data: {state['extracted_data']}")
    
    return state

# Create the graph
def create_workflow_graph():
    """Create and compile the workflow graph."""
    # Create the graph
    workflow = StateGraph(DocumentState)
    
    # Add nodes
    workflow.add_node("intake", intake_node)
    workflow.add_node("extract_data", extract_data_node)
    workflow.add_node("await_human_review", await_human_review_node)
    workflow.add_node("human_review_completed", human_review_completed_node)
    workflow.add_node("finalize", finalize_node)
    
    # Add edges
    workflow.add_edge("intake", "extract_data")
    workflow.add_conditional_edges(
        "extract_data",
        validation_router,
        {
            "pending_review": "await_human_review",
            "finalize": "finalize"
        }
    )
    # After human review, we go to human_review_completed, then to finalize
    workflow.add_edge("await_human_review", "human_review_completed")
    workflow.add_edge("human_review_completed", "finalize")
    workflow.add_edge("finalize", END)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    return workflow

# Add a table for storing submitted documents
def initialize_database():
    """Initialize the database with required tables."""
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    
    # Create the checkpoints table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints_v2 (
            thread_id TEXT PRIMARY KEY,
            checkpoint BLOB,
            metadata BLOB,
            created_at TEXT,
            parent_checkpoint TEXT
        )
    """)
    
    # Create a table for storing submitted documents
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            content TEXT,
            status TEXT DEFAULT 'received',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Function to submit a new document
def submit_document(content: str) -> str:
    """Submit a new document to the workflow."""
    # Create a unique document ID
    document_id = str(uuid.uuid4())
    
    # Initialize the database
    initialize_database()
    
    # Store the document in the database
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (document_id, content, status)
        VALUES (?, ?, ?)
    """, (document_id, content, "received"))
    conn.commit()
    conn.close()
    
    print(f"Document {document_id} submitted successfully")
    print("Start the engine with 'python engine.py' to process this document.")
    
    return document_id

# Main function to run the engine
def run_engine():
    """Run the workflow engine."""
    # Initialize the database
    initialize_database()
    
    # Create the workflow graph
    workflow = create_workflow_graph()
    
    # Create a SqliteSaver checkpointer using context manager
    with SqliteSaver.from_conn_string("workflow.db") as checkpointer:
        # Compile the graph with the checkpointer
        app = workflow.compile(checkpointer=checkpointer)
        
        print("Workflow engine started. Listening for new documents...")
        print(f"Using OpenRouter with model: {openrouter_model}")
        
        # Process only documents with "received" status (not those pending human review)
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT document_id, content FROM documents 
            WHERE status = 'received'
        """)
        pending_documents = cursor.fetchall()
        conn.close()
        
        if not pending_documents:
            print("No pending documents found.")
            return app
        
        print(f"Processing {len(pending_documents)} pending documents...")
        
        # Process each pending document
        for document_id, content in pending_documents:
            print(f"Processing document {document_id}...")
            
            # Create the initial state for the document
            initial_state = DocumentState(
                document_id=document_id,
                content=content,
                status="received",
                extracted_data={},
                workflow_history=[]
            )
            
            # Process the document
            config = {"configurable": {"thread_id": document_id}}
            try:
                final_state = app.invoke(initial_state, config)
                print(f"Document {document_id} processed successfully. Final status: {final_state['status']}")
                
                # Update document status
                conn = sqlite3.connect("workflow.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE documents 
                    SET status = ? 
                    WHERE document_id = ?
                """, (final_state['status'], document_id))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error processing document {document_id}: {e}")
                # Update document status to error
                conn = sqlite3.connect("workflow.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE documents 
                    SET status = 'error' 
                    WHERE document_id = ?
                """, (document_id,))
                conn.commit()
                conn.close()
        
        return app

def run_example_document():
    """Run an example document through the workflow."""
    # Create an example document
    example_content = """
    INV-2023-001
    Date: 2023-10-15
    Vendor: ABC Office Supplies Ltd.
    Due Date: 2023-11-15
    
    Items:
    - Office chairs (10) @ $150.00 = $1,500.00
    - Desks (5) @ $200.00 = $1,000.00
    - Filing cabinets (3) @ $300.00 = $900.00
    
    Subtotal: $3,400.00
    Tax: $272.00
    Total: $3,672.00
    
    Payment terms: Net 30 days
    """
    
    # Submit and process the example document
    document_id = submit_document(example_content)
    print(f"Example document submitted with ID: {document_id}")
    
    # Run the engine to process the document
    run_engine()
    
    return document_id

if __name__ == "__main__":
    # Run the engine when the script is executed directly
    run_engine()
