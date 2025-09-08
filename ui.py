#!/usr/bin/env python3
"""
Streamlit UI for the Resilient AI Workflow Engine.
This UI allows human validators to review and approve documents pending review.
"""

import streamlit as st
import sqlite3
import json
import time
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path so we can import engine.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import create_workflow_graph, DocumentState
from langgraph.checkpoint.sqlite import SqliteSaver
# Import the Command class for resuming workflows
from langgraph.types import Command

# Initialize the workflow graph
@st.cache_resource
def init_workflow():
    workflow = create_workflow_graph()
    return workflow

def get_pending_documents() -> list:
    """Retrieve all documents with status 'pending_review' from the database."""
    try:
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        
        # Query the documents table for pending documents (not the checkpoints table)
        cursor.execute("SELECT document_id, content, status FROM documents WHERE status = 'pending_review'")
        rows = cursor.fetchall()
        
        pending_docs = []
        for row in rows:
            document_id, content, status = row
            pending_docs.append({
                "document_id": document_id,
                "reason": "Awaiting human review"
            })
        
        conn.close()
        return pending_docs
    except Exception as e:
        st.error(f"Error retrieving pending documents: {e}")
        return []

def get_document_details(document_id: str) -> Dict[str, Any]:
    """Retrieve the details of a specific document."""
    try:
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        
        # Query the documents table for the document content
        cursor.execute("SELECT content, status FROM documents WHERE document_id = ?", (document_id,))
        row = cursor.fetchone()
        
        if row:
            content, status = row
            # For this example, we'll return mock data with some real structure
            # In a real implementation, you would retrieve the actual extracted data from the checkpoint
            return {
                "document_id": document_id,
                "content": content,
                "status": status,
                "extracted_data": {
                    "vendor_name": "ABC Office Supplies Ltd.",
                    "invoice_id": "INV-2023-001",
                    "due_date": "2023-11-15",
                    "total_amount": 3672.00
                },
                "workflow_history": [
                    {"node": "intake", "message": "Document received"},
                    {"node": "extract_data", "message": "Data extracted"},
                    {"node": "validation_router", "message": "Routed to human review due to high amount"}
                ]
            }
        else:
            return {}
        
        conn.close()
    except Exception as e:
        st.error(f"Error retrieving document details: {e}")
        return {}

def update_document_state(document_id: str, updated_data: Dict[str, Any]) -> bool:
    """Update the document state with human-provided data and resume the workflow."""
    try:
        # Update the document in the database with the corrected data
        conn = sqlite3.connect("workflow.db")
        cursor = conn.cursor()
        
        # Update the document status to indicate it's being processed
        cursor.execute("""
            UPDATE documents 
            SET status = 'processing' 
            WHERE document_id = ?
        """, (document_id,))
        
        conn.commit()
        conn.close()
        
        # Resume the workflow with the human-provided data using Command
        workflow = init_workflow()
        with SqliteSaver.from_conn_string("workflow.db") as checkpointer:
            app = workflow.compile(checkpointer=checkpointer)
            
            # Resume the workflow using Command(resume=...)
            config = {"configurable": {"thread_id": document_id}}
            
            # Create the human input data that will be passed to the interrupt
            human_input = {
                "extracted_data": updated_data
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
            
            st.success(f"Document {document_id} updated with new data and workflow resumed! Final status: {final_state['status']}")
            return True
        
    except Exception as e:
        st.error(f"Error updating document state: {e}")
        # Reset status back to pending_review on error
        try:
            conn = sqlite3.connect("workflow.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE documents 
                SET status = 'pending_review' 
                WHERE document_id = ?
            """, (document_id,))
            conn.commit()
            conn.close()
        except:
            pass
        return False

def main():
    st.title("AI Workflow Engine - Human Review Dashboard")
    
    # Get pending documents
    pending_docs = get_pending_documents()
    
    if not pending_docs:
        st.info("No documents pending review at this time.")
        return
    
    # Display the list of pending documents
    st.subheader("Pending Documents for Review")
    
    # Create a selection box for documents
    doc_options = {doc["document_id"]: f"{doc['document_id']} - {doc['reason']}" for doc in pending_docs}
    selected_doc_id = st.selectbox("Select a document to review:", options=list(doc_options.keys()))
    
    if selected_doc_id:
        # Display document details
        doc_details = get_document_details(selected_doc_id)
        
        st.subheader(f"Review Document: {selected_doc_id}")
        
        # Display document status
        st.write(f"**Status:** {doc_details.get('status', 'Unknown')}")
        
        # Display original content
        st.write("### Original Document Content")
        st.text_area("Content", value=doc_details.get("content", ""), height=200, key="content", disabled=True)
        
        # Display extracted data
        st.write("### AI-Extracted Data")
        extracted_data = doc_details.get("extracted_data", {})
        
        # Create editable fields for the extracted data
        updated_data = {}
        for key, value in extracted_data.items():
            if key == "total_amount":
                updated_data[key] = st.number_input(f"{key.replace('_', ' ').title()}", value=float(value), key=key)
            else:
                updated_data[key] = st.text_input(f"{key.replace('_', ' ').title()}", value=str(value), key=key)
        
        # Display workflow history
        st.write("### Workflow History")
        history = doc_details.get("workflow_history", [])
        for item in history:
            st.text(f"{item['node']}: {item['message']}")
        
        # Approval button
        if st.button("Approve & Resume Workflow"):
            if update_document_state(selected_doc_id, updated_data):
                st.success("Document approved and workflow resumed!")
                # Refresh the page to show updated list
                st.rerun()
            else:
                st.error("Failed to approve document. Please try again.")

if __name__ == "__main__":
    main()