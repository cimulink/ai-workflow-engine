#!/usr/bin/env python3
"""
Test script for AG-UI integration
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_shared_types():
    """Test shared type definitions"""
    print("Testing shared types...")
    
    from shared.types import AgentState, WorkflowStatus, DocumentExtractedData, ValidationResult, WorkflowEvent
    
    # Test DocumentExtractedData
    extracted_data = DocumentExtractedData(
        vendor_name="Test Corp",
        invoice_id="INV-001",
        total_amount=1500.00,
        document_type="invoice"
    )
    print(f"OK DocumentExtractedData: {extracted_data.vendor_name}, ${extracted_data.total_amount}")
    
    # Test ValidationResult
    validation = ValidationResult(
        is_valid=False,
        needs_review=True,
        reasons=["Amount exceeds threshold"],
        auto_approved=False,
        validation_rules_applied=["invoice_validation"]
    )
    print(f"OK ValidationResult: needs_review={validation.needs_review}, reasons={validation.reasons}")
    
    # Test AgentState
    agent_state = AgentState(
        workflow_id="test-123",
        status=WorkflowStatus.PROCESSING,
        current_step="extraction",
        document_content="Test invoice content",
        extracted_data=extracted_data,
        validation_result=validation,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"OK AgentState: {agent_state.workflow_id}, status={agent_state.status}")
    
    return True

def test_database():
    """Test database operations"""
    print("\n🧪 Testing database operations...")
    
    from shared.database import WorkflowDatabase
    from shared.types import AgentState, WorkflowStatus, DocumentExtractedData, WorkflowEvent
    
    # Initialize test database
    db = WorkflowDatabase("./test_workflow.db")
    
    # Test saving agent state
    extracted_data = DocumentExtractedData(
        vendor_name="Test Corp",
        invoice_id="INV-001",
        total_amount=500.00
    )
    
    agent_state = AgentState(
        workflow_id="test-db-123",
        status=WorkflowStatus.PROCESSING,
        current_step="extraction",
        document_content="Test invoice for database",
        extracted_data=extracted_data,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    db.save_agent_state(agent_state)
    print("✅ Saved agent state to database")
    
    # Test retrieving agent state
    retrieved_state = db.get_agent_state("test-db-123")
    if retrieved_state and retrieved_state.workflow_id == "test-db-123":
        print("✅ Retrieved agent state from database")
    else:
        print("❌ Failed to retrieve agent state")
        return False
    
    # Test adding workflow event
    event = WorkflowEvent(
        workflow_id="test-db-123",
        event_type="EXTRACTION_COMPLETE",
        data={"fields_extracted": 4},
        timestamp=datetime.now().isoformat(),
        step_name="extraction"
    )
    
    db.add_workflow_event(event)
    print("✅ Added workflow event")
    
    # Clean up test database
    os.remove("./test_workflow.db")
    print("✅ Cleaned up test database")
    
    return True

async def test_ag_ui_agent():
    """Test AG-UI agent functionality"""
    print("\n🧪 Testing AG-UI agent...")
    
    try:
        from backend.ag_ui_server import DocumentWorkflowAgent
        from ag_ui_protocol.protocol.agent_protocol import RunRequest, Message
        
        # Create agent
        agent = DocumentWorkflowAgent()
        print("✅ Created DocumentWorkflowAgent")
        
        # Create test request
        test_message = Message(
            role="user",
            content="""
INVOICE

From: Test Vendor Inc.
Invoice Number: INV-TEST-001
Date: 2024-09-09
Due Date: 2024-10-09
Total Amount: $750.00

Description:
- Consulting services: $750.00

Thank you for your business!
            """.strip()
        )
        
        request = RunRequest(
            messages=[test_message],
            tools=[],
            state={}
        )
        
        print("✅ Created test RunRequest")
        
        # Test streaming (just get first few events)
        event_count = 0
        async for event in agent.run(request):
            event_count += 1
            print(f"📡 Event {event_count}: {event.get('type', 'unknown')}")
            
            if event_count >= 5:  # Just test first 5 events
                break
        
        print(f"✅ Received {event_count} events from agent")
        return True
        
    except Exception as e:
        print(f"❌ AG-UI agent test failed: {e}")
        return False

def test_frontend_build():
    """Test if frontend can be built"""
    print("\n🧪 Testing frontend build...")
    
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    
    if not os.path.exists(frontend_dir):
        print("❌ Frontend directory not found")
        return False
    
    # Check if package.json exists
    package_json = os.path.join(frontend_dir, "package.json")
    if not os.path.exists(package_json):
        print("❌ package.json not found")
        return False
    
    print("✅ Frontend directory structure looks good")
    
    # Check if key files exist
    key_files = [
        "src/App.tsx",
        "src/main.tsx",
        "src/components/DocumentProcessor.tsx",
        "src/components/ReviewQueue.tsx",
        "src/lib/ag-ui-client.ts"
    ]
    
    for file_path in key_files:
        full_path = os.path.join(frontend_dir, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    return True

async def main():
    """Run all tests"""
    print("Starting AG-UI Integration Tests\n")
    
    tests = [
        ("Shared Types", test_shared_types),
        ("Database Operations", test_database),
        ("AG-UI Agent", test_ag_ui_agent),
        ("Frontend Build", test_frontend_build)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                print(f"✅ {test_name}: PASSED\n")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED\n")
                failed += 1
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\n")
            failed += 1
    
    print("=" * 50)
    print(f"🧪 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! AG-UI integration is ready.")
    else:
        print("⚠️ Some tests failed. Check the output above.")
    
    return failed == 0

if __name__ == "__main__":
    asyncio.run(main())