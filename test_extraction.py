#!/usr/bin/env python3
"""Test the extraction node in isolation."""

import os
os.environ["USE_MCP"] = "true"
os.environ["USE_GOOGLE_APIS"] = "false"  # Use local JSON for simpler testing

from callpilot.graph import build_graph_mcp
import asyncio

async def test_extraction():
    """Test extraction node with natural language query."""
    
    # Test query with location and preferences
    test_state = {
        "user_text": "find me a dentist close to Alexanderplatz tomorrow morning",
        "transcript": [],
        "use_speech": False
    }
    
    print("="*60)
    print("Testing Extraction Node")
    print("="*60)
    print(f"User query: {test_state['user_text']}")
    print()
    
    # Build graph
    graph = build_graph_mcp()
    
    # Run workflow  
    final_state = await graph.ainvoke(test_state)
    
    print("="*60)
    print("Extracted State:")
    print("="*60)
    for key in ['specialty', 'time_window', 'radius_km', 'user_location', 'preferred_provider', 'urgency']:
        value = final_state.get(key, 'NOT SET')
        print(f"  {key}: {value}")
    print()
    
    # Show result
    if 'result_text' in final_state:
        print("="*60)
        print("Final Result:")
        print("="*60)
        print(final_state['result_text'])
    elif 'result' in final_state:
        import json
        print("="*60)
        print("Final Result:")
        print("="*60)
        print(json.dumps(final_state['result'], indent=2))

if __name__ == "__main__":
    asyncio.run(test_extraction())
