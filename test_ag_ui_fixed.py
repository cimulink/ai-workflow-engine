#!/usr/bin/env python3
"""
Test AG-UI integration with the fixed implementation
"""

import asyncio
import json
from backend.ag_ui_server_fixed import DocumentWorkflowAgent, RunRequest, Message

async def test_agent_workflow():
    print("Testing AG-UI Document Workflow Agent...")
    
    agent = DocumentWorkflowAgent()
    
    # Create test message
    test_message = Message(
        role="user",
        content="""
INVOICE

From: Test Company Inc.
Invoice Number: INV-2024-001
Date: 2024-09-09
Due Date: 2024-10-09
Total Amount: $750.00

Description:
- Consulting services: $750.00

Thank you for your business!
        """.strip()
    )
    
    # Create run request
    request = RunRequest(
        messages=[test_message],
        tools=[],
        state={}
    )
    
    print("Starting workflow stream...")
    event_count = 0
    
    try:
        async for event in agent.run(request):
            event_count += 1
            print(f"Event {event_count}: {event.type}")
            if event.type == "TEXT_MESSAGE_CHUNK":
                print(f"  Content: {event.data.get('content', '').strip()}")
            elif event.type == "TOOL_CALL_CHUNK":
                print(f"  Tool: {event.data.get('tool_name')}")
            elif event.type == "RUN_FINISHED":
                print(f"  Final Status: {event.data.get('status')}")
                break
            
            # Limit output for testing
            if event_count >= 10:
                print("  ... (limiting output for test)")
                break
                
    except Exception as e:
        import traceback
        print(f"Error during workflow execution: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False
    
    print(f"Completed! Processed {event_count} events")
    return True

async def main():
    print("AG-UI Fixed Implementation Test")
    print("=" * 40)
    
    success = await test_agent_workflow()
    
    if success:
        print("\nOK: AG-UI integration test passed!")
        print("\nTo start the system:")
        print("1. Backend: python start_backend.py")
        print("2. Frontend: python start_frontend.py")
        print("3. Open: http://localhost:3000")
    else:
        print("\nERROR: AG-UI integration test failed!")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())