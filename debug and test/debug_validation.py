#!/usr/bin/env python3
"""
Debug script to test validation workflow
"""

from engine import run_workflow, create_workflow, setup_database

def test_large_invoice():
    large_invoice = """
INVOICE #12345
From: Big Corp Ltd
Due: 2024-10-30
Total: $5,500.00
Services: Consulting
    """
    
    print("Testing large invoice validation...")
    print(f"Invoice content: {large_invoice.strip()}")
    
    result, app, config = run_workflow(large_invoice, "debug_large")
    
    print(f"\nWorkflow result type: {type(result)}")
    print(f"Result: {result}")
    
    # Check final state using app.get_state
    if app and config:
        try:
            final_state = app.get_state(config)
            print(f"\nFinal state from get_state:")
            print(f"  Type: {type(final_state)}")
            if hasattr(final_state, 'values'):
                print(f"  Values: {final_state.values}")
                if isinstance(final_state.values, dict):
                    status = final_state.values.get('status', 'unknown')
                    reason = final_state.values.get('reason_for_review', 'none')
                    extracted = final_state.values.get('extracted_data', {})
                    print(f"  Status: {status}")
                    print(f"  Review reason: {reason}")
                    print(f"  Extracted data: {extracted}")
        except Exception as e:
            print(f"Error getting final state: {e}")

if __name__ == "__main__":
    test_large_invoice()