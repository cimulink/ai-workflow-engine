import sqlite3
from engine import create_workflow_graph, DocumentState, extract_data_node, validation_router

def debug_validation():
    """Debug the validation router logic."""
    # Create a test document with high amount that should trigger human review
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
    
    # Create the initial state for the document
    initial_state = DocumentState(
        document_id="debug-document-123",
        content=content,
        status="received",
        extracted_data={},
        workflow_history=[]
    )
    
    # Run only the extract_data node
    extracted_state = extract_data_node(initial_state)
    
    print("Extracted data:")
    print(extracted_state["extracted_data"])
    
    # Check what the validation router would return
    routing_decision = validation_router(extracted_state)
    print(f"Routing decision: {routing_decision}")
    
    # Check the total amount
    total_amount = extracted_state["extracted_data"].get("total_amount", 0)
    print(f"Total amount: {total_amount}")
    print(f"Total amount > 1000: {total_amount > 1000}")

if __name__ == "__main__":
    debug_validation()