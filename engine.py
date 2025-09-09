import os
import json
import uuid
import sqlite3
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import requests
from dotenv import load_dotenv

# Import debug configuration
from debug.debug_config import (
    debug_step, debug_state_change, debug_api_call, 
    debug_validation, debug_dump_state, debug_timing, 
    debug_error, get_debugger
)

load_dotenv()

class WorkflowState(TypedDict):
    id: str
    content: str
    status: str  # received, processing, pending_review, finalized, error
    extracted_data: Optional[Dict[str, Any]]
    workflow_history: List[str]
    reason_for_review: Optional[str]
    created_at: str
    updated_at: str

class DocumentProcessor:
    def __init__(self):
        # Use OpenRouter API with ChatOpenAI wrapper
        self.llm = ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free"),
            temperature=0,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
    
    def intake_node(self, state: WorkflowState) -> WorkflowState:
        """Initialize workflow state for a new document"""
        start_time = datetime.now()
        debug_step("INTAKE_NODE", f"Initializing document {state['id']}")
        debug_dump_state(state, "Initial State")
        
        current_time = start_time.isoformat()
        old_status = state.get("status", "unknown")
        
        state["status"] = "processing"
        state["workflow_history"].append(f"Document received at {current_time}")
        state["updated_at"] = current_time
        
        debug_state_change(old_status, "processing", "Document intake completed")
        debug_timing("Intake Node", start_time)
        debug_dump_state(state, "State After Intake")
        
        print(f"Processing document {state['id']}")
        return state
    
    def extract_data_node(self, state: WorkflowState) -> WorkflowState:
        """Extract structured data from document using LLM"""
        start_time = datetime.now()
        debug_step("EXTRACT_DATA_NODE", f"Processing document {state['id']} with LLM")
        
        current_time = start_time.isoformat()
        
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
            messages = [
                SystemMessage(content=extraction_prompt),
                HumanMessage(content=f"Document content:\n{state['content']}")
            ]
            
            debug_api_call("OpenRouter", "chat_completion", 
                         {"model": "deepseek", "content_length": len(state['content'])})
            
            api_start = datetime.now()
            response = self.llm.invoke(messages)
            debug_timing("OpenRouter API Call", api_start)
            
            debug_api_call("OpenRouter", "chat_completion_response", 
                         response_data={"response_length": len(response.content)})
            
            # Try to parse JSON from response
            try:
                extracted_data = json.loads(response.content)
                debug_step("JSON_PARSE", "Successfully parsed LLM response as JSON")
            except json.JSONDecodeError:
                debug_step("JSON_PARSE_FALLBACK", "Direct JSON parsing failed, trying regex extraction")
                # If direct JSON parsing fails, try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    debug_step("JSON_PARSE_SUCCESS", "Regex extraction successful")
                else:
                    extracted_data = {"error": "Failed to parse LLM response as JSON"}
                    debug_step("JSON_PARSE_FAILED", "All JSON parsing attempts failed", "ERROR")
            
            state["extracted_data"] = extracted_data
            state["workflow_history"].append(f"Data extracted at {current_time}")
            state["updated_at"] = current_time
            
            debug_dump_state(extracted_data, "Extracted Data")
            debug_timing("Complete Data Extraction", start_time)
            
            print(f"Extracted data for document {state['id']}: {extracted_data}")
            
        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            debug_error(e, f"Document {state['id']} extraction failed")
            
            state["extracted_data"] = {"error": error_msg}
            state["workflow_history"].append(f"Extraction failed at {current_time}: {error_msg}")
            state["status"] = "error"
            debug_state_change("processing", "error", f"Extraction failed: {error_msg}")
            
            print(f"Error extracting data from document {state['id']}: {error_msg}")
        
        return state
    
    def validation_router(self, state: WorkflowState) -> str:
        """Route workflow based on validation rules (routing only - no state modification)"""
        debug_step("VALIDATION_ROUTER", f"Checking business rules for document {state['id']}")
        
        extracted_data = state.get("extracted_data", {})
        debug_dump_state(extracted_data, "Data Being Validated")
        
        # Track validation rules and results for debugging
        rules_checked = []
        rule_results = []
        reasons = []
        
        # Basic data validation
        if not extracted_data or "error" in extracted_data:
            rules_checked.append("Data Presence Check")
            rule_results.append(False)
            reasons.append("Missing or invalid data")
            debug_step("VALIDATION_FAIL", "No valid extracted data found", "WARNING")
            debug_validation(state['id'], rules_checked, rule_results)
            print(f"Document {state['id']} requires review: Missing or invalid data")
            return "await_human_review"
        
        # Invoice processing rules
        if "total_amount" in extracted_data:
            debug_step("VALIDATION_TYPE", "Processing as invoice document")
            
            # Vendor name check
            rules_checked.append("Vendor Name Present")
            has_vendor = bool(extracted_data.get("vendor_name"))
            rule_results.append(has_vendor)
            if not has_vendor:
                reasons.append("Missing vendor name")
            
            # Invoice ID check
            rules_checked.append("Invoice ID Present")
            has_invoice_id = bool(extracted_data.get("invoice_id"))
            rule_results.append(has_invoice_id)
            if not has_invoice_id:
                reasons.append("Missing invoice ID")
            
            # Amount threshold check
            rules_checked.append("Amount Under $1000")
            amount = extracted_data.get("total_amount")
            if amount:
                try:
                    numeric_amount = float(str(amount).replace("$", "").replace(",", ""))
                    amount_ok = numeric_amount <= 1000
                    rule_results.append(amount_ok)
                    debug_step("AMOUNT_CHECK", f"Amount ${numeric_amount} vs $1000 threshold")
                    if not amount_ok:
                        reasons.append("Amount exceeds $1000 threshold")
                except (ValueError, TypeError):
                    rule_results.append(False)
                    reasons.append("Invalid amount format")
                    debug_step("AMOUNT_CHECK_ERROR", f"Could not parse amount: {amount}", "ERROR")
            else:
                rule_results.append(True)  # No amount means no threshold issue
        
        # Customer support rules
        elif "sentiment" in extracted_data:
            debug_step("VALIDATION_TYPE", "Processing as customer support ticket")
            
            # Sentiment check
            rules_checked.append("Customer Sentiment Acceptable")
            sentiment = extracted_data.get("sentiment", "").lower()
            sentiment_ok = sentiment != "irate"
            rule_results.append(sentiment_ok)
            if not sentiment_ok:
                reasons.append("Customer sentiment is irate")
            
            # Security topic check
            rules_checked.append("Non-Security Topic")
            topic = extracted_data.get("topic", "").lower()
            security_ok = not ("security" in topic or "vulnerability" in topic)
            rule_results.append(security_ok)
            if not security_ok:
                reasons.append("Security-related issue")
        
        # Generic validation
        else:
            debug_step("VALIDATION_TYPE", "Processing as generic document")
            rules_checked.append("All Fields Complete")
            
            empty_fields = []
            for key, value in extracted_data.items():
                if value is None or value == "":
                    empty_fields.append(key)
            
            fields_complete = len(empty_fields) == 0
            rule_results.append(fields_complete)
            if not fields_complete:
                reasons.extend([f"Missing or empty field: {field}" for field in empty_fields])
        
        # Log validation results
        debug_validation(state['id'], rules_checked, rule_results)
        
        # Determine routing decision
        if reasons:
            reason_text = "; ".join(reasons)
            debug_step("VALIDATION_RESULT", f"FAILED - {reason_text}", "WARNING")
            print(f"Document {state['id']} requires review: {reason_text}")
            return "await_human_review"
        
        debug_step("VALIDATION_RESULT", "PASSED - All rules satisfied", "INFO")
        print(f"Document {state['id']} passed validation, proceeding to finalize")
        return "finalize"
    
    def await_human_review_node(self, state: WorkflowState) -> WorkflowState:
        """Interrupt workflow for human review"""
        current_time = datetime.now().isoformat()
        
        # Calculate the reason for review
        extracted_data = state.get("extracted_data", {})
        reasons = []
        
        if not extracted_data or "error" in extracted_data:
            reasons.append("Missing or invalid extracted data")
        else:
            # Check for missing critical fields
            if "total_amount" in extracted_data:
                # Invoice processing rules
                if not extracted_data.get("vendor_name"):
                    reasons.append("Missing vendor name")
                if not extracted_data.get("invoice_id"):
                    reasons.append("Missing invoice ID")
                if extracted_data.get("total_amount") and float(str(extracted_data["total_amount"]).replace("$", "").replace(",", "")) > 1000:
                    reasons.append("Amount exceeds $1000 threshold")
            
            elif "sentiment" in extracted_data:
                # Customer support rules
                sentiment = extracted_data.get("sentiment", "").lower()
                topic = extracted_data.get("topic", "").lower()
                
                if sentiment == "irate":
                    reasons.append("Customer sentiment is irate")
                if "security" in topic or "vulnerability" in topic:
                    reasons.append("Security-related issue")
            
            else:
                # Generic validation - check for null/empty critical fields
                for key, value in extracted_data.items():
                    if value is None or value == "":
                        reasons.append(f"Missing or empty field: {key}")
        
        reason_text = "; ".join(reasons) if reasons else "Unknown validation issue"
        
        state["status"] = "pending_review"
        state["reason_for_review"] = reason_text
        state["workflow_history"].append(f"Workflow paused for human review at {current_time}: {reason_text}")
        state["updated_at"] = current_time
        
        print(f"Document {state['id']} requires human review: {reason_text}")
        
        # This node will be interrupted - execution stops here
        return state
    
    def finalize_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow"""
        current_time = datetime.now().isoformat()
        
        state["status"] = "finalized"
        state["workflow_history"].append(f"Workflow finalized at {current_time}")
        state["updated_at"] = current_time
        
        # Write results to file
        output_file = f"output_{state['id']}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "document_id": state["id"],
                "extracted_data": state["extracted_data"],
                "workflow_history": state["workflow_history"],
                "finalized_at": current_time
            }, f, indent=2)
        
        print(f"Document {state['id']} processing completed. Results saved to {output_file}")
        return state

def create_workflow():
    """Create and compile the LangGraph workflow"""
    processor = DocumentProcessor()
    
    # Create the state graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("intake", processor.intake_node)
    workflow.add_node("extract_data", processor.extract_data_node)
    workflow.add_node("await_human_review", processor.await_human_review_node)
    workflow.add_node("finalize", processor.finalize_node)
    
    # Set entry point
    workflow.set_entry_point("intake")
    
    # Add edges
    workflow.add_edge("intake", "extract_data")
    workflow.add_conditional_edges(
        "extract_data",
        processor.validation_router,
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
        processor.validation_router,
        {
            "await_human_review": "await_human_review",  # Still needs review
            "finalize": "finalize"  # Can now finalize
        }
    )
    
    return workflow

def setup_database():
    """Initialize SQLite database for checkpointing"""
    os.makedirs("./checkpoints", exist_ok=True)
    db_path = "./checkpoints/workflow.db"
    
    # Initialize the SqliteSaver with proper connection
    try:
        # Create a connection and pass it to SqliteSaver
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
    except Exception as e:
        print(f"Warning: Database setup issue: {e}")
        try:
            # Fallback to in-memory database
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            checkpointer = SqliteSaver(conn)
        except Exception as e2:
            print(f"Error: Cannot initialize checkpointer: {e2}")
            raise
    
    return checkpointer

def run_workflow(document_content: str, document_id: str = None):
    """Run the workflow for a document"""
    workflow_start = datetime.now()
    
    if document_id is None:
        document_id = str(uuid.uuid4())
    
    debug_step("WORKFLOW_START", f"Starting workflow for document {document_id}")
    debug_step("DOCUMENT_INFO", f"Content length: {len(document_content)} chars")
    
    # Setup
    debug_step("SETUP_WORKFLOW", "Creating workflow graph and checkpointer")
    setup_start = datetime.now()
    
    workflow = create_workflow()
    checkpointer = setup_database()
    
    # Compile with checkpointer
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["await_human_review"]
    )
    
    debug_timing("Workflow Setup", setup_start)
    debug_step("SETUP_COMPLETE", "Workflow compiled with SQLite checkpointer")
    
    # Initialize state
    initial_state = WorkflowState(
        id=document_id,
        content=document_content,
        status="received",
        extracted_data=None,
        workflow_history=[],
        reason_for_review=None,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    debug_dump_state(initial_state, "Initial Workflow State")
    
    # Run workflow
    config = {"configurable": {"thread_id": document_id}}
    debug_step("WORKFLOW_EXECUTION", f"Starting workflow stream with config: {config}")
    
    try:
        result = None
        final_state = None
        step_count = 0
        
        execution_start = datetime.now()
        for state in app.stream(initial_state, config):
            step_count += 1
            result = state
            debug_step("WORKFLOW_STEP", f"Step {step_count}: {list(state.keys())}")
            print(f"Current state: {list(state.keys())}")
        
        debug_timing("Workflow Execution", execution_start)
        debug_step("WORKFLOW_STREAM_COMPLETE", f"Completed {step_count} workflow steps")
        
        # Get the final state after workflow completion/interruption
        debug_step("STATE_RETRIEVAL", "Retrieving final state from checkpointer")
        try:
            checkpoint = app.get_state(config)
            if checkpoint and hasattr(checkpoint, 'values'):
                final_state = checkpoint.values
                debug_step("STATE_SUCCESS", "Retrieved state from checkpoint")
            else:
                final_state = result
                debug_step("STATE_FALLBACK", "Using stream result as final state")
        except Exception as state_error:
            debug_error(state_error, "Error retrieving final state")
            final_state = result
        
        debug_dump_state(final_state, "Final Workflow State")
        debug_timing("Complete Workflow", workflow_start)
        
        return final_state, app, config
        
    except Exception as e:
        debug_error(e, f"Workflow execution failed for document {document_id}")
        print(f"Error running workflow: {e}")
        return None, app, config

def resume_workflow(document_id: str, updated_data: Dict[str, Any] = None):
    """Resume a paused workflow with updated data"""
    print(f"Resuming workflow for document {document_id}")
    
    workflow = create_workflow()
    checkpointer = setup_database()
    
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_after=["await_human_review"]
    )
    
    config = {"configurable": {"thread_id": document_id}}
    
    # Get current state
    current_state = app.get_state(config)
    if not current_state:
        print(f"No workflow found for document {document_id}")
        return None
    
    # Update state with corrected data if provided
    if updated_data:
        try:
            new_state = current_state.values.copy()
            if "extracted_data" in new_state and isinstance(new_state["extracted_data"], dict):
                new_state["extracted_data"].update(updated_data)
            
            new_state["workflow_history"].append(f"Human review completed at {datetime.now().isoformat()}")
            new_state["updated_at"] = datetime.now().isoformat()
            
            # Update the state in the checkpointer
            app.update_state(config, new_state)
            print(f"Updated workflow state with corrections: {list(updated_data.keys())}")
        except Exception as e:
            print(f"Error updating state: {e}")
            return None
    
    # Resume workflow
    try:
        result = None
        for state in app.stream(None, config):
            result = state
            print(f"Resumed workflow step: {list(state.keys())}")
        
        # Get final state
        final_state = app.get_state(config)
        if final_state and hasattr(final_state, 'values'):
            final_status = final_state.values.get('status', 'unknown')
            print(f"Workflow resumed successfully, final status: {final_status}")
            return final_state.values
        
        return result
        
    except Exception as e:
        print(f"Error resuming workflow: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    sample_invoice = """
    INVOICE
    From: Acme Corp
    Invoice #: INV-2024-001
    Due Date: 2024-10-15
    Total Amount: $1,250.00
    
    Services provided:
    - Consulting services: $1,000.00
    - Processing fee: $250.00
    """
    
    print("Starting workflow engine...")
    result, app, config = run_workflow(sample_invoice)
    
    if result:
        print(f"Workflow completed with status: {result}")
    else:
        print("Workflow execution failed")