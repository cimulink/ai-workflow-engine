#!/usr/bin/env python3
"""
Test script to demonstrate the AI Workflow Engine functionality.
This script tests various scenarios including automatic processing and human review.
"""

import os
import time
import uuid
from datetime import datetime
from engine import run_workflow, resume_workflow, setup_database

def test_automatic_approval():
    """Test a document that should be approved automatically"""
    print("🧪 Test 1: Automatic Approval (Small Invoice)")
    print("=" * 60)
    
    small_invoice = """
    INVOICE
    From: Small Business Inc.
    Invoice #: INV-2024-SMALL
    Due Date: 2024-10-15
    Total Amount: $500.00
    
    Services provided:
    - Web design consultation: $500.00
    """
    
    document_id = f"test_auto_{uuid.uuid4().hex[:8]}"
    
    print(f"Submitting document: {document_id}")
    result, app, config = run_workflow(small_invoice, document_id)
    
    if result:
        final_state = result[list(result.keys())[0]]
        print(f"✅ Final Status: {final_state.get('status')}")
        print(f"📊 Extracted Data: {final_state.get('extracted_data')}")
        
        if final_state.get('status') == 'finalized':
            print("🎉 SUCCESS: Document processed automatically!")
        else:
            print("⚠️  Document requires human review")
    else:
        print("❌ FAILED: Error processing document")
    
    print()
    return document_id

def test_human_review_required():
    """Test a document that requires human review"""
    print("🧪 Test 2: Human Review Required (Large Invoice)")
    print("=" * 60)
    
    large_invoice = """
    INVOICE
    From: Enterprise Solutions Corp
    Invoice #: INV-2024-LARGE
    Due Date: 2024-10-30
    Total Amount: $5,000.00
    
    Services provided:
    - Enterprise software license: $4,500.00
    - Implementation services: $500.00
    """
    
    document_id = f"test_review_{uuid.uuid4().hex[:8]}"
    
    print(f"Submitting document: {document_id}")
    result, app, config = run_workflow(large_invoice, document_id)
    
    if result:
        final_state = result[list(result.keys())[0]]
        print(f"📋 Final Status: {final_state.get('status')}")
        print(f"🔍 Review Reason: {final_state.get('reason_for_review')}")
        print(f"📊 Extracted Data: {final_state.get('extracted_data')}")
        
        if final_state.get('status') == 'pending_review':
            print("✅ SUCCESS: Document correctly flagged for human review!")
        else:
            print("❌ UNEXPECTED: Document should require human review")
    else:
        print("❌ FAILED: Error processing document")
    
    print()
    return document_id

def test_customer_support_ticket():
    """Test a customer support ticket scenario"""
    print("🧪 Test 3: Customer Support Ticket (Irate Customer)")
    print("=" * 60)
    
    support_ticket = """
    Customer Support Ticket
    
    From: angry.customer@email.com
    Subject: Your service is terrible!
    
    I am absolutely furious with your service! This is the third time this month 
    that your system has been down, and I'm losing money because of it. 
    
    This is completely unacceptable and I demand immediate action. I've been a 
    customer for 5 years and this is the worst service I've ever experienced.
    
    Fix this NOW or I'm canceling my account and telling everyone I know to 
    avoid your company!
    
    Customer: John Angry
    Account: Premium Business
    Priority: URGENT
    """
    
    document_id = f"test_support_{uuid.uuid4().hex[:8]}"
    
    print(f"Submitting ticket: {document_id}")
    result, app, config = run_workflow(support_ticket, document_id)
    
    if result:
        final_state = result[list(result.keys())[0]]
        print(f"📋 Final Status: {final_state.get('status')}")
        print(f"🔍 Review Reason: {final_state.get('reason_for_review')}")
        print(f"📊 Extracted Data: {final_state.get('extracted_data')}")
        
        if final_state.get('status') == 'pending_review':
            print("✅ SUCCESS: Irate customer ticket flagged for human review!")
        else:
            print("⚠️  Ticket processed automatically - check extraction logic")
    else:
        print("❌ FAILED: Error processing ticket")
    
    print()
    return document_id

def test_resume_workflow():
    """Test resuming a workflow after human review"""
    print("🧪 Test 4: Workflow Resumption")
    print("=" * 60)
    
    # First, create a document that requires review
    invoice_with_issues = """
    INVOICE
    From: Incomplete Corp
    Invoice #: 
    Due Date: 2024-11-01
    Total Amount: $2,500.00
    
    Services provided:
    - Consulting services
    """
    
    document_id = f"test_resume_{uuid.uuid4().hex[:8]}"
    
    print(f"Step 1: Submitting document with missing data: {document_id}")
    result, app, config = run_workflow(invoice_with_issues, document_id)
    
    if result:
        final_state = result[list(result.keys())[0]]
        if final_state.get('status') == 'pending_review':
            print("✅ Document correctly paused for review")
            print(f"🔍 Review needed: {final_state.get('reason_for_review')}")
            
            # Simulate human corrections
            print("\nStep 2: Simulating human review corrections...")
            corrected_data = {
                "invoice_id": "INV-2024-CORRECTED",
                "vendor_name": "Incomplete Corp (Corrected)"
            }
            
            print(f"📝 Applying corrections: {corrected_data}")
            
            # Resume the workflow
            print("Step 3: Resuming workflow...")
            resume_result = resume_workflow(document_id, corrected_data)
            
            if resume_result:
                resumed_state = resume_result[list(resume_result.keys())[0]]
                print(f"✅ Resumed Status: {resumed_state.get('status')}")
                print(f"📊 Final Data: {resumed_state.get('extracted_data')}")
                
                if resumed_state.get('status') == 'finalized':
                    print("🎉 SUCCESS: Workflow resumed and completed!")
                else:
                    print("⚠️  Workflow still pending after corrections")
            else:
                print("❌ FAILED: Could not resume workflow")
        else:
            print("❌ UNEXPECTED: Document should have required review")
    else:
        print("❌ FAILED: Error in initial workflow")
    
    print()
    return document_id

def test_crash_recovery():
    """Demonstrate crash recovery capability"""
    print("🧪 Test 5: Crash Recovery Simulation")
    print("=" * 60)
    
    print("This test demonstrates that workflow state is persisted to SQLite.")
    print("In a real scenario, if the engine crashes, workflows can be resumed.")
    
    # Show current database state
    checkpointer = setup_database()
    
    print("📊 Current database contains persistent workflow states.")
    print("💡 To test crash recovery:")
    print("   1. Submit a document that requires review")
    print("   2. Kill the engine process")
    print("   3. Restart and use the UI to resume workflows")
    print("   4. All state will be recovered from SQLite")
    
    print()

def main():
    """Run all tests"""
    print("🚀 AI Workflow Engine Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    # Ensure we have OpenRouter API key
    if not os.getenv('OPENROUTER_API_KEY'):
        print("❌ ERROR: OPENROUTER_API_KEY environment variable not set")
        print("Please set your OpenRouter API key in .env file:")
        print("   OPENROUTER_API_KEY=your-api-key-here")
        return
    
    # Run tests
    test_results = []
    
    try:
        # Test 1: Automatic approval
        test_results.append(test_automatic_approval())
        time.sleep(2)
        
        # Test 2: Human review required
        test_results.append(test_human_review_required())
        time.sleep(2)
        
        # Test 3: Customer support ticket
        test_results.append(test_customer_support_ticket())
        time.sleep(2)
        
        # Test 4: Workflow resumption
        test_results.append(test_resume_workflow())
        time.sleep(2)
        
        # Test 5: Crash recovery info
        test_crash_recovery()
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
    
    # Summary
    print("📋 Test Summary")
    print("=" * 60)
    print(f"✅ {len(test_results)} test scenarios executed")
    print(f"📁 Generated document IDs: {test_results}")
    print("\n🎯 Next Steps:")
    print("1. Check output_*.json files for finalized documents")
    print("2. Run 'streamlit run ui.py' to see pending reviews")
    print("3. Use the UI to approve/edit documents requiring review")
    print("\n💡 Tips:")
    print("- Set OPENROUTER_API_KEY in .env file")
    print("- Check ./checkpoints/workflow.db for persistent state")
    print("- Use 'python submit.py --help' for submission options")

if __name__ == "__main__":
    main()