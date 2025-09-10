#!/usr/bin/env python3
"""
Document submission script for the AI Workflow Engine.
This script allows users to submit documents for processing.
"""

import sys
import uuid
from datetime import datetime
from engine import run_workflow

def submit_document(content: str, document_id: str = None) -> str:
    """
    Submit a document for processing.
    
    Args:
        content: The document content to process
        document_id: Optional custom document ID
        
    Returns:
        The document ID that was assigned
    """
    if document_id is None:
        document_id = str(uuid.uuid4())[:8]  # Use shorter ID for readability
    
    print(f"Submitting document with ID: {document_id}")
    print(f"Content preview: {content[:100]}{'...' if len(content) > 100 else ''}")
    print("-" * 50)
    
    # Run the workflow
    result, app, config = run_workflow(content, document_id)
    
    if result:
        print(f"\nDocument {document_id} submitted successfully!")
        
        # The result should now be the final state directly
        final_state = result
        if isinstance(final_state, dict):
            status = final_state.get('status', 'unknown')
            print(f"Current status: {status}")
            
            # Check if it needs human review
            if status == 'pending_review':
                reason = final_state.get('reason_for_review', 'Unknown reason')
                print(f"[WARNING] Document requires human review: {reason}")
                print("Please check the review UI to approve and continue processing.")
            elif status == 'finalized':
                print("[SUCCESS] Document processing completed automatically!")
            else:
                print(f"[INFO] Document status: {status}")
        else:
            print(f"[INFO] Workflow completed, final result: {type(final_state)}")
    else:
        print(f"[ERROR] Error submitting document {document_id}")
    
    return document_id

def submit_from_file(file_path: str) -> str:
    """Submit document content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        document_id = f"file_{uuid.uuid4().hex[:8]}"
        return submit_document(content, document_id)
    
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error reading file: {e}")
        sys.exit(1)

def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python submit.py <content>           # Submit text content")
        print("  python submit.py --file <path>       # Submit file content")
        print("  python submit.py --sample            # Submit sample invoice")
        print("\nExamples:")
        print("  python submit.py \"Invoice from Acme Corp for $500\"")
        print("  python submit.py --file invoice.txt")
        print("  python submit.py --sample")
        sys.exit(1)
    
    if sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("[ERROR] Please specify file path: python submit.py --file <path>")
            sys.exit(1)
        submit_from_file(sys.argv[2])
    
    elif sys.argv[1] == "--sample":
        sample_invoice = """
INVOICE

From: Acme Consulting Services
Address: 123 Business St, Corporate City, CC 12345
Phone: (555) 123-4567

Bill To: ABC Corporation
Address: 456 Client Ave, Customer Town, CT 67890

Invoice Number: INV-2024-001
Date: September 8, 2024
Due Date: October 8, 2024

Description of Services:
- Strategic consulting services (40 hours @ $75/hour): $3,000.00
- Project management fee: $500.00
- Travel expenses: $250.00

Subtotal: $3,750.00
Tax (8.5%): $318.75
Total Amount Due: $4,068.75

Payment Terms: Net 30 days
Payment Methods: Check, Wire Transfer, ACH

Thank you for your business!
        """
        submit_document(sample_invoice.strip(), "sample_invoice")
    
    else:
        # Submit the provided content
        content = " ".join(sys.argv[1:])
        submit_document(content)

if __name__ == "__main__":
    main()