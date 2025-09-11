"""
Test script for Pure LangGraph + AG-UI integration
"""

import asyncio
import json
import aiohttp
from datetime import datetime

async def test_langgraph_streaming():
    """Test the pure LangGraph streaming implementation"""
    
    # Test document content
    test_document = """
    INVOICE
    From: Test Corp
    Invoice #: INV-2024-001
    Due Date: 2024-12-15
    Total Amount: $750.00
    
    Services provided:
    - Consulting services: $500.00
    - Processing fee: $250.00
    """
    
    # Prepare request
    request_data = {
        "messages": [
            {
                "role": "user",
                "content": test_document
            }
        ],
        "tools": [],
        "state": {}
    }
    
    print("Testing Pure LangGraph + AG-UI Integration")
    print("="*60)
    print(f"Test document: {test_document[:100]}...")
    print(f"Starting workflow at: {datetime.now().isoformat()}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8000/agent/run',
                json=request_data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                if response.status != 200:
                    print(f"❌ HTTP Error: {response.status}")
                    print(await response.text())
                    return
                
                print("Streaming events from Pure LangGraph:")
                print("-" * 40)
                
                event_count = 0
                workflow_id = None
                
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    
                    if line_text.startswith('data: '):
                        event_json = line_text[6:]  # Remove 'data: ' prefix
                        
                        try:
                            event = json.loads(event_json)
                            event_count += 1
                            
                            # Track workflow ID
                            if not workflow_id and event.get('workflow_id'):
                                workflow_id = event['workflow_id']
                            
                            # Print event info
                            event_type = event.get('type', 'UNKNOWN')
                            timestamp = event.get('timestamp', '')[:19]  # Trim microseconds
                            
                            print(f"[{event_count:2d}] {timestamp} | {event_type}")
                            
                            # Show important event data
                            if event_type == "RUN_STARTED":
                                print(f"     START - Workflow ID: {event.get('workflow_id')}")
                                print(f"     Agent: {event.get('data', {}).get('agent_name')}")
                            
                            elif event_type == "TEXT_MESSAGE_CHUNK":
                                content = event.get('data', {}).get('content', '')
                                if content.strip():
                                    print(f"     MSG: {content.strip()}")
                            
                            elif event_type == "TOOL_CALL_CHUNK":
                                tool_name = event.get('data', {}).get('tool_name', 'unknown')
                                print(f"     TOOL: {tool_name}")
                                
                                # Try to parse and show extracted data
                                args = event.get('data', {}).get('arguments', '{}')
                                try:
                                    extracted = json.loads(args)
                                    field_count = len([v for v in extracted.values() if v is not None])
                                    print(f"     DATA: Extracted {field_count} fields")
                                    
                                    # Show key fields
                                    for key, value in extracted.items():
                                        if value and key in ['vendor_name', 'invoice_id', 'total_amount']:
                                            print(f"        - {key}: {value}")
                                            
                                except json.JSONDecodeError:
                                    print(f"     DATA: {args[:50]}...")
                            
                            elif event_type == "GENERATIVE_UI":
                                component = event.get('data', {}).get('component', 'Unknown')
                                print(f"     UI: Component: {component}")
                                
                            elif event_type == "HUMAN_INPUT_REQUIRED":
                                reasons = event.get('data', {}).get('reasons', [])
                                print(f"     REVIEW: Human review needed: {len(reasons)} reasons")
                                for reason in reasons[:3]:  # Show first 3 reasons
                                    print(f"        - {reason}")
                            
                            elif event_type == "RUN_FINISHED":
                                status = event.get('data', {}).get('status', 'unknown')
                                print(f"     FINISH: Workflow completed with status: {status}")
                            
                            elif event_type == "RUN_ERROR":
                                error = event.get('data', {}).get('error', 'Unknown error')
                                print(f"     ERROR: {error}")
                                
                        except json.JSONDecodeError as e:
                            print(f"ERROR: Failed to parse event: {e}")
                            print(f"Raw line: {line_text[:100]}...")
                
                print()
                print("="*60)
                print(f"SUCCESS: Streaming completed!")
                print(f"Total events received: {event_count}")
                print(f"Workflow ID: {workflow_id}")
                print(f"Completed at: {datetime.now().isoformat()}")
                
                # Test workflow status endpoint
                if workflow_id:
                    print()
                    print("Testing workflow status endpoint...")
                    async with session.get(f'http://localhost:8000/api/workflows/{workflow_id}') as status_response:
                        if status_response.status == 200:
                            status_data = await status_response.json()
                            print(f"SUCCESS: Workflow status retrieved successfully")
                            
                            langgraph_state = status_data.get('langgraph_state', {})
                            if langgraph_state:
                                print(f"   - LangGraph Status: {langgraph_state.get('status', 'unknown')}")
                                print(f"   - Current Step: {langgraph_state.get('current_step', 'unknown')}")
                                print(f"   - Human Review Required: {langgraph_state.get('human_review_required', False)}")
                        else:
                            print(f"ERROR: Status endpoint error: {status_response.status}")
                
    except Exception as e:
        print(f"ERROR: Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_langgraph_streaming())