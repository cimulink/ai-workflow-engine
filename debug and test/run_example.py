#!/usr/bin/env python3
"""
Example script demonstrating the full AI Workflow Engine functionality
"""

import time
from engine import run_workflow, resume_workflow

def main():
    print("=== AI Workflow Engine Demo ===")
    print()
    
    # Example 1: Small invoice (auto-approved)
    print("1. Testing small invoice (should auto-approve)...")
    small_invoice = "INVOICE #001 from Quick Service Co for $800 web development"
    
    result, _, _ = run_workflow(small_invoice, "demo_small")
    if result and isinstance(result, dict):
        status = result.get('status')
        print(f"   Result: {status}")
        if status == 'finalized':
            print("   [SUCCESS] Small invoice processed automatically!")
        else:
            print(f"   [WARNING] Unexpected status: {status}")
    print()
    
    # Example 2: Large invoice (requires review)
    print("2. Testing large invoice (should require review)...")
    large_invoice = """
    INVOICE #002
    From: Enterprise Solutions Inc
    Due Date: 2024-12-01
    Total Amount: $15,000.00
    
    Services:
    - Enterprise software implementation: $12,000
    - Training and support: $3,000
    """
    
    result, _, _ = run_workflow(large_invoice, "demo_large")
    if result and isinstance(result, dict):
        status = result.get('status')
        reason = result.get('reason_for_review')
        print(f"   Result: {status}")
        print(f"   Review reason: {reason}")
        
        if status == 'pending_review':
            print("   [SUCCESS] Large invoice flagged for human review!")
            
            # Example 3: Resume workflow with corrections
            print("\n3. Testing workflow resumption with corrections...")
            corrected_data = {
                "total_amount": 800.00,  # Reduce amount to pass threshold
                "notes": "Amount corrected after review"
            }
            
            print(f"   Applying corrections: {corrected_data}")
            resumed_result = resume_workflow("demo_large", corrected_data)
            
            if resumed_result and isinstance(resumed_result, dict):
                final_status = resumed_result.get('status')
                print(f"   Final result: {final_status}")
                if final_status == 'finalized':
                    print("   [SUCCESS] Workflow resumed and completed!")
                else:
                    print(f"   [WARNING] Unexpected final status: {final_status}")
            else:
                print("   [ERROR] Failed to resume workflow")
        else:
            print(f"   [ERROR] Unexpected status: {status}")
    print()
    
    print("=== Demo Complete ===")
    print("\nNext steps:")
    print("1. Run 'streamlit run ui.py' to see the review interface")
    print("2. Submit more documents with 'python submit.py --sample'")
    print("3. Use the UI to approve/edit documents requiring review")

if __name__ == "__main__":
    main()