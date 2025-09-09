#!/usr/bin/env python3
"""
Debug-enabled document submission script for the AI Workflow Engine.
Provides detailed tracing of the submission and processing flow.
"""

import sys
import uuid
import os
from datetime import datetime
from engine import run_workflow
from debug.debug_config import set_debug_level, debug_summary

def debug_submit_document(content: str, document_id: str = None, debug_level: str = "DETAILED") -> str:
    """
    Submit a document for processing with comprehensive debugging.
    
    Args:
        content: The document content to process
        document_id: Optional custom document ID
        debug_level: Debug verbosity (BASIC, DETAILED, VERBOSE, TRACE)
        
    Returns:
        The document ID that was assigned
    """
    print("[DEBUG] DEBUG-ENABLED SUBMISSION")
    print("=" * 50)
    
    # Setup debugging
    debugger = set_debug_level(debug_level)
    print(f"Debug Level: {debug_level}")
    print(f"Logging: {'Enabled' if debugger else 'Disabled'}")
    
    if document_id is None:
        document_id = str(uuid.uuid4())[:8]
    
    print(f"Document ID: {document_id}")
    print(f"Content Length: {len(content)} characters")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-" * 50)
    
    try:
        # Run the workflow with full debugging
        result, app, config = run_workflow(content, document_id)
        
        print("\n" + "=" * 50)
        print("SUBMISSION RESULTS")
        print("=" * 50)
        
        if result:
            print(f"[SUCCESS] Document {document_id} submitted successfully!")
            
            # Extract the actual state from the result
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                reason = result.get('reason_for_review', 'N/A')
                extracted_data = result.get('extracted_data', {})
                history = result.get('workflow_history', [])
                
                print(f"[STATUS] Final Status: {status}")
                print(f"[REVIEW] Review Reason: {reason}")
                print(f"[DATA] Extracted Fields: {list(extracted_data.keys()) if extracted_data else 'None'}")
                print(f"[HISTORY] History Steps: {len(history)}")
                
                # Display extracted data summary
                if extracted_data and debug_level in ['VERBOSE', 'TRACE']:
                    print("\n[DATA] EXTRACTED DATA SUMMARY:")
                    for key, value in extracted_data.items():
                        print(f"  {key}: {value}")
                
                # Display workflow history
                if history and debug_level in ['VERBOSE', 'TRACE']:
                    print("\n[HISTORY] WORKFLOW HISTORY:")
                    for i, step in enumerate(history, 1):
                        print(f"  {i}. {step}")
                
                # Status-specific messages
                if status == 'pending_review':
                    print(f"\n[WARNING] HUMAN REVIEW REQUIRED")
                    print(f"Reason: {reason}")
                    print("Next step: Use 'streamlit run ui.py' to review and approve")
                elif status == 'finalized':
                    print(f"\n[SUCCESS] PROCESSING COMPLETED")
                    print("Document was automatically approved and finalized")
                elif status == 'error':
                    print(f"\n[ERROR] PROCESSING ERROR")
                    print("Check logs for error details")
                else:
                    print(f"\n[INFO] STATUS: {status}")
            else:
                print(f"Result type: {type(result)}")
        else:
            print(f"[ERROR] Error submitting document {document_id}")
        
    except Exception as e:
        print(f"\n[ERROR] SUBMISSION FAILED")
        print(f"Error: {str(e)}")
        if debug_level in ['VERBOSE', 'TRACE']:
            import traceback
            print("\nFull traceback:")
            traceback.print_exc()
    
    finally:
        # Print debug summary
        print("\n" + "=" * 50)
        debug_summary()
        print("=" * 50)
    
    return document_id

def main():
    """Debug CLI interface"""
    print("[DEBUG] AI Workflow Engine - Debug Submission Tool")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python debug_submit.py <content> [debug_level]")
        print("  python debug_submit.py --file <path> [debug_level]")
        print("  python debug_submit.py --sample [debug_level]")
        print("")
        print("Debug Levels:")
        print("  BASIC    - Basic flow information")
        print("  DETAILED - Step-by-step logging (default)")
        print("  VERBOSE  - Full state dumps and API calls")
        print("  TRACE    - Maximum verbosity with timing")
        print("")
        print("Examples:")
        print("  python debug_submit.py \"Invoice for $500\" VERBOSE")
        print("  python debug_submit.py --file invoice.txt TRACE")
        print("  python debug_submit.py --sample DETAILED")
        sys.exit(1)
    
    # Parse debug level
    debug_level = "DETAILED"  # default
    if len(sys.argv) >= 3 and sys.argv[-1].upper() in ['BASIC', 'DETAILED', 'VERBOSE', 'TRACE']:
        debug_level = sys.argv[-1].upper()
    
    # Handle different input methods
    if sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("[ERROR] Please specify file path: python debug_submit.py --file <path>")
            sys.exit(1)
        
        file_path = sys.argv[2]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[FILE] Loading content from: {file_path}")
        except FileNotFoundError:
            print(f"[ERROR] File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error reading file: {e}")
            sys.exit(1)
    
    elif sys.argv[1] == "--sample":
        print("[SAMPLE] Using sample invoice")
        content = """
LARGE INVOICE FOR DEBUG TESTING

From: Debug Testing Corp
Address: 123 Test Street, Debug City, DC 12345
Phone: (555) 123-DEBUG

Bill To: AI Workflow Engine
Address: 456 Engine Lane, Process Town, PT 67890

Invoice Number: DEBUG-2024-001
Date: September 8, 2024
Due Date: October 8, 2024

Description of Services:
- Debug testing services (50 hours @ $100/hour): $5,000.00
- Performance optimization: $1,500.00
- Documentation updates: $500.00

Subtotal: $7,000.00
Tax (8.25%): $577.50
Total Amount Due: $7,577.50

Payment Terms: Net 30 days
Payment Methods: Check, Wire Transfer

This is a test invoice designed to trigger human review
due to the large amount exceeding the $1000 threshold.
        """
    else:
        # Direct content submission
        content = " ".join(sys.argv[1:-1] if len(sys.argv) > 2 and sys.argv[-1].upper() in ['BASIC', 'DETAILED', 'VERBOSE', 'TRACE'] else sys.argv[1:])
    
    # Submit document with debugging
    debug_submit_document(content.strip(), debug_level=debug_level)

if __name__ == "__main__":
    main()