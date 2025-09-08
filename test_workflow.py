import sqlite3
import time
from engine import create_workflow_graph, DocumentState
from langgraph.checkpoint.sqlite import SqliteSaver
# Import the Command class for resuming workflows
from langgraph.types import Command

def test_workflow_full_cycle():
    """Test the full workflow cycle: submission -> processing -> human review -> resumption."""
    # Create a test document with high amount that will trigger human review
    document_id = f"test-document-{int(time.time())}"
    content = """
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
    
    # Initialize database
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    
    # Create documents table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            content TEXT,
            status TEXT DEFAULT 'received',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert test document
    cursor.execute("""
        INSERT OR REPLACE INTO documents (document_id, content, status)
        VALUES (?, ?, ?)
    """, (document_id, content, "received"))
    
    conn.commit()
    conn.close()
    
    print(f"Test document {document_id} created with status 'received'")
    
    # Run the initial workflow processing (this should pause for human review)
    workflow = create_workflow_graph()
    with SqliteSaver.from_conn_string("workflow.db") as checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        
        # Create the initial state for the document
        initial_state = DocumentState(
            document_id=document_id,
            content=content,
            status="received",
            extracted_data={},
            workflow_history=[]
        )
        
        # Process the document using stream to catch the interrupt
        config = {"configurable": {"thread_id": document_id}}
        result = None
        
        # Use stream instead of invoke to properly handle interrupts
        for chunk in app.stream(initial_state, config):
            if "__interrupt__" in chunk:
                print(f"Document {document_id} interrupted for human review")
                result = chunk
                break
            result = chunk
        
        if result and "__interrupt__" in result:
            print("Document correctly paused for human review")
            # Update document status to pending_review
            conn = sqlite3.connect("workflow.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE documents 
                SET status = 'pending_review' 
                WHERE document_id = ?
            """, (document_id,))
            conn.commit()
            conn.close()
            return True
        else:
            print(f"Initial workflow processing completed. Status: {result['status'] if result else 'unknown'}")
            # Update document status
            if result:
                conn = sqlite3.connect("workflow.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE documents 
                    SET status = ? 
                    WHERE document_id = ?
                """, (result['status'], document_id))
                conn.commit()
                conn.close()
            return False
    
    # Verify the document is in pending_review status
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM documents WHERE document_id = ?", (document_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] == "pending_review":
        print("Document correctly paused for human review")
        return True
    else:
        print(f"Document status is {row[0] if row else 'unknown'} instead of pending_review")
        return False

def test_workflow_resume():
    """Test that a workflow can be resumed after human approval."""
    # Find a document that is pending review
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    cursor.execute("SELECT document_id FROM documents WHERE status = 'pending_review' LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("No pending documents found for testing resume")
        return False
    
    document_id = row[0]
    print(f"Testing resume for document {document_id}")
    
    # Simulate human approval with corrected data (using amount under threshold)
    corrected_data = {
        "vendor_name": "Test Vendor Inc.",
        "invoice_id": "TEST-001",
        "due_date": "2023-12-31",
        "total_amount": 500.00  # Under the 1000 threshold
    }
    
    print("Simulating human approval with corrected data:")
    print(corrected_data)
    
    # Resume workflow with corrected data using Command
    workflow = create_workflow_graph()
    with SqliteSaver.from_conn_string("workflow.db") as checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        
        # Resume the workflow using Command(resume=...)
        config = {"configurable": {"thread_id": document_id}}
        
        # Create the human input data that will be passed to the interrupt
        human_input = {
            "extracted_data": corrected_data
        }
        
        # Resume the workflow with the human input
        final_state = app.invoke(Command(resume=human_input), config)
        
        # Update document status in database
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE documents 
            SET status = ? 
            WHERE document_id = ?
        """, (final_state['status'], document_id))
        conn.commit()
        conn.close()
        
        print(f"Workflow resumed and completed. Final status: {final_state['status']}")
        return final_state['status'] == 'finalized'

if __name__ == "__main__":
    print("Testing full workflow cycle...")
    if test_workflow_full_cycle():
        print("\nTesting workflow resumption...")
        if test_workflow_resume():
            print("\nAll tests passed!")
        else:
            print("\nWorkflow resumption test failed")
    else:
        print("\nFull workflow cycle test failed")