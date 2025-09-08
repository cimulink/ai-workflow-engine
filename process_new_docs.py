import sqlite3
from engine import create_workflow_graph, DocumentState
from langgraph.checkpoint.sqlite import SqliteSaver

def process_new_documents():
    """Process only new documents up to the point of human review."""
    # Create the workflow graph
    workflow = create_workflow_graph()
    
    # Create a SqliteSaver checkpointer using context manager
    with SqliteSaver.from_conn_string("workflow.db") as checkpointer:
        # Compile the graph with the checkpointer
        app = workflow.compile(checkpointer=checkpointer)
        
        print("Processing new documents...")
        
        # Process only documents with "received" status
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT document_id, content FROM documents 
            WHERE status = 'received'
        """)
        pending_documents = cursor.fetchall()
        conn.close()
        
        if not pending_documents:
            print("No new documents found.")
            return
        
        print(f"Processing {len(pending_documents)} new documents...")
        
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
            
            # Use stream instead of invoke to properly handle interrupts
            result = None
            try:
                # Stream the results to catch the interrupt
                for chunk in app.stream(initial_state, config):
                    if "__interrupt__" in chunk:
                        print(f"Document {document_id} interrupted for human review")
                        result = chunk
                        break
                    result = chunk
                
                if result and "__interrupt__" in result:
                    print(f"Document {document_id} paused for human review")
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
                else:
                    print(f"Document {document_id} processed. Final status: {result['status'] if result else 'unknown'}")
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

if __name__ == "__main__":
    process_new_documents()