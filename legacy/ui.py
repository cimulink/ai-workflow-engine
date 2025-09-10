import streamlit as st
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from engine import resume_workflow

# Configure Streamlit page
st.set_page_config(
    page_title="AI Workflow Engine - Review Queue",
    page_icon="📋",
    layout="wide"
)

class WorkflowDatabase:
    """Helper class to interact with the workflow database"""
    
    def __init__(self, db_path: str = "./checkpoints/workflow.db"):
        self.db_path = db_path
    
    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get all workflows pending human review"""
        try:
            from engine import create_workflow, setup_database
            
            # Use the LangGraph API to get workflow states
            workflow = create_workflow()
            checkpointer = setup_database()
            app = workflow.compile(checkpointer=checkpointer)
            
            # Get all thread IDs from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
            thread_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            pending_workflows = []
            
            for thread_id in thread_ids:
                try:
                    config = {"configurable": {"thread_id": thread_id}}
                    state = app.get_state(config)
                    
                    if state and hasattr(state, 'values') and isinstance(state.values, dict):
                        workflow_state = state.values
                        
                        if workflow_state.get('status') == 'pending_review':
                            pending_workflows.append({
                                'thread_id': thread_id,
                                'document_id': workflow_state.get('id', thread_id),
                                'status': workflow_state.get('status'),
                                'reason_for_review': workflow_state.get('reason_for_review', 'Unknown reason'),
                                'extracted_data': workflow_state.get('extracted_data', {}),
                                'content': workflow_state.get('content', ''),
                                'workflow_history': workflow_state.get('workflow_history', []),
                                'created_at': workflow_state.get('created_at', ''),
                                'updated_at': workflow_state.get('updated_at', '')
                            })
                
                except Exception as e:
                    # Skip threads that can't be loaded
                    continue
            
            return pending_workflows
            
        except Exception as e:
            st.error(f"Error accessing workflow states: {e}")
            return []
    
    def get_workflow_details(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed workflow information"""
        pending_reviews = self.get_pending_reviews()
        for workflow in pending_reviews:
            if workflow['thread_id'] == thread_id:
                return workflow
        return None

def display_review_queue():
    """Display the main review queue interface"""
    st.title("📋 AI Workflow Engine - Review Queue")
    st.markdown("---")
    
    db = WorkflowDatabase()
    pending_workflows = db.get_pending_reviews()
    
    if not pending_workflows:
        st.info("🎉 No documents pending review! All workflows are either completed or in progress.")
        st.markdown("### How to Submit Documents")
        st.code("python submit.py --sample")
        st.code("python submit.py \"Your document content here\"")
        st.code("python submit.py --file document.txt")
        return
    
    st.success(f"📋 {len(pending_workflows)} document(s) pending review")
    
    # Create columns for the layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Review Queue")
        
        # Display list of pending documents
        selected_doc = None
        for i, workflow in enumerate(pending_workflows):
            doc_id = workflow['document_id']
            reason = workflow['reason_for_review']
            created_at = workflow.get('created_at', 'Unknown')
            
            # Create a unique key for each button
            button_key = f"select_doc_{doc_id}_{i}"
            
            if st.button(
                f"📄 {doc_id}\n🔍 {reason[:50]}{'...' if len(reason) > 50 else ''}",
                key=button_key,
                help=f"Created: {created_at}"
            ):
                st.session_state.selected_document = doc_id
        
        # Handle selected document
        if 'selected_document' in st.session_state:
            selected_doc_id = st.session_state.selected_document
            selected_doc = next((w for w in pending_workflows if w['document_id'] == selected_doc_id), None)
    
    with col2:
        if selected_doc:
            display_document_review(selected_doc, db)
        else:
            st.info("👈 Select a document from the queue to review")

def display_document_review(workflow: Dict[str, Any], db: WorkflowDatabase):
    """Display the document review interface"""
    st.subheader(f"📄 Document Review: {workflow['document_id']}")
    
    # Document information
    with st.expander("📋 Document Information", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Document ID:** {workflow['document_id']}")
            st.write(f"**Status:** {workflow['status']}")
            st.write(f"**Created:** {workflow.get('created_at', 'Unknown')}")
        with col2:
            st.write(f"**Updated:** {workflow.get('updated_at', 'Unknown')}")
            st.write(f"**Thread ID:** {workflow['thread_id']}")
    
    # Reason for review
    st.error(f"⚠️ **Review Required:** {workflow['reason_for_review']}")
    
    # Original document content
    with st.expander("📄 Original Document Content", expanded=False):
        st.text_area(
            "Content:",
            value=workflow['content'],
            height=200,
            disabled=True,
            label_visibility="collapsed"
        )
    
    # Extracted data editing
    st.subheader("✏️ Extracted Data")
    st.markdown("Review and edit the extracted information below:")
    
    extracted_data = workflow.get('extracted_data', {})
    updated_data = {}
    
    # Create form for editing extracted data
    with st.form(key=f"edit_form_{workflow['document_id']}"):
        # Display extracted fields for editing
        for key, value in extracted_data.items():
            if key == "error":
                st.error(f"Extraction Error: {value}")
                continue
            
            # Determine input type based on field name and value
            if key in ["total_amount", "amount"]:
                # Numeric field
                try:
                    numeric_value = float(str(value).replace("$", "").replace(",", "")) if value else 0.0
                    updated_data[key] = st.number_input(
                        f"**{key.replace('_', ' ').title()}**",
                        value=numeric_value,
                        format="%.2f",
                        key=f"input_{key}_{workflow['document_id']}"
                    )
                except (ValueError, TypeError):
                    updated_data[key] = st.text_input(
                        f"**{key.replace('_', ' ').title()}**",
                        value=str(value) if value else "",
                        key=f"input_{key}_{workflow['document_id']}"
                    )
            else:
                # Text field
                updated_data[key] = st.text_input(
                    f"**{key.replace('_', ' ').title()}**",
                    value=str(value) if value else "",
                    key=f"input_{key}_{workflow['document_id']}"
                )
        
        # Add new field option
        st.markdown("**Add New Field:**")
        col1, col2 = st.columns(2)
        with col1:
            new_field_name = st.text_input("Field Name", key=f"new_field_name_{workflow['document_id']}")
        with col2:
            new_field_value = st.text_input("Field Value", key=f"new_field_value_{workflow['document_id']}")
        
        if new_field_name and new_field_value:
            updated_data[new_field_name] = new_field_value
        
        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            approve_submitted = st.form_submit_button(
                "✅ Approve & Resume",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            reject_submitted = st.form_submit_button(
                "❌ Reject",
                use_container_width=True
            )
        
        with col3:
            st.write("")  # Spacing
    
    # Handle form submissions
    if approve_submitted:
        handle_approval(workflow['document_id'], updated_data)
    elif reject_submitted:
        handle_rejection(workflow['document_id'])
    
    # Workflow history
    with st.expander("📜 Workflow History", expanded=False):
        for i, history_item in enumerate(workflow.get('workflow_history', [])):
            st.write(f"{i+1}. {history_item}")

def handle_approval(document_id: str, updated_data: Dict[str, Any]):
    """Handle workflow approval and resumption"""
    st.info(f"⏳ Approving and resuming workflow for document {document_id}...")
    
    try:
        # Resume the workflow with updated data
        result = resume_workflow(document_id, updated_data)
        
        if result:
            st.success(f"✅ Document {document_id} approved and processing resumed!")
            st.success("🔄 The workflow will continue automatically. Refreshing page...")
            
            # Clear the selected document and refresh
            if 'selected_document' in st.session_state:
                del st.session_state.selected_document
            
            # Auto-refresh the page after a short delay
            st.rerun()
        else:
            st.error(f"❌ Failed to resume workflow for document {document_id}")
    
    except Exception as e:
        st.error(f"❌ Error resuming workflow: {str(e)}")

def handle_rejection(document_id: str):
    """Handle workflow rejection"""
    st.warning(f"⚠️ Document {document_id} rejected - workflow stopped.")
    st.info("💡 In a production system, this would mark the workflow as rejected and notify relevant parties.")
    
    # Clear the selected document
    if 'selected_document' in st.session_state:
        del st.session_state.selected_document
    
    st.rerun()

def main():
    """Main Streamlit application"""
    # Add refresh button in sidebar
    with st.sidebar:
        st.title("🔧 Controls")
        
        if st.button("🔄 Refresh Queue", use_container_width=True):
            # Clear any selected document and refresh
            if 'selected_document' in st.session_state:
                del st.session_state.selected_document
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📖 Instructions")
        st.markdown("""
        1. **Select** a document from the queue
        2. **Review** the original content and extracted data
        3. **Edit** any incorrect information
        4. **Approve** to continue processing or **Reject** to stop
        """)
        
        st.markdown("---")
        st.markdown("### 📊 System Info")
        
        # Display database connection status
        try:
            db = WorkflowDatabase()
            pending_count = len(db.get_pending_reviews())
            st.success(f"🟢 Database Connected")
            st.info(f"📋 {pending_count} pending reviews")
        except Exception as e:
            st.error(f"🔴 Database Error: {str(e)}")
    
    # Main interface
    display_review_queue()
    
    # Auto-refresh every 30 seconds
    st.markdown(
        """
        <script>
        setTimeout(function(){
            window.location.reload();
        }, 30000);
        </script>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()