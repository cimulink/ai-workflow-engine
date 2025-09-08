import sqlite3
import time
from engine import submit_document

def create_test_document():
    """Create a test document that will require human review."""
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
    
    # Submit the document
    document_id = submit_document(content)
    print(f"Test document {document_id} submitted for processing")
    return document_id

def check_document_status(document_id):
    """Check the status of a document."""
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM documents WHERE document_id = ?", (document_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return row[0]
    return None

if __name__ == "__main__":
    # Create a test document
    document_id = create_test_document()
    
    # Wait a moment for processing
    time.sleep(2)
    
    # Check the status
    status = check_document_status(document_id)
    print(f"Document status: {status}")
    
    if status == "received":
        print("Document is ready to be processed by the engine")
    else:
        print(f"Document has unexpected status: {status}")