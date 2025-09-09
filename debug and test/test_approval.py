#!/usr/bin/env python3
"""
Test approval workflow functionality
"""

from engine import run_workflow, resume_workflow, create_workflow, setup_database

def test_resume():
    """Test resuming a workflow"""
    # First create a workflow that needs review
    large_invoice = """
INVOICE #99999
From: Test Resume Corp
Due: 2024-12-31
Total: $9,999.00
Services: Testing
    """
    
    print("Step 1: Creating workflow that requires review...")
    result, app, config = run_workflow(large_invoice, "test_resume")
    
    if result and isinstance(result, dict):
        status = result.get('status')
        reason = result.get('reason_for_review')
        print(f"Initial status: {status}")
        print(f"Review reason: {reason}")
        
        if status == 'pending_review':
            print("\nStep 2: Testing resume workflow...")
            
            # Test data corrections
            updated_data = {
                "total_amount": 500.00,  # Reduce amount to pass validation
                "vendor_name": "Test Resume Corp (Corrected)"
            }
            
            print(f"Applying corrections: {updated_data}")
            
            try:
                resumed_result = resume_workflow("test_resume", updated_data)
                if resumed_result:
                    print("[SUCCESS] Resume workflow succeeded!")
                    if isinstance(resumed_result, dict):
                        final_status = resumed_result.get('status', 'unknown')
                        print(f"Final status: {final_status}")
                    else:
                        print(f"Resume result type: {type(resumed_result)}")
                else:
                    print("[ERROR] Resume workflow returned None")
            except Exception as e:
                print(f"[ERROR] Resume workflow failed with exception: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[ERROR] Expected pending_review, got {status}")
    else:
        print("[ERROR] Failed to create initial workflow")

if __name__ == "__main__":
    test_resume()