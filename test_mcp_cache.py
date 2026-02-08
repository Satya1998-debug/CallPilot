#!/usr/bin/env python3
"""Test MCP provider caching by simulating the correct workflow."""

import requests
import json

MCP_URL = "http://localhost:8000/mcp"

def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool via HTTP."""
    response = requests.post(
        MCP_URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
    )
    response.raise_for_status()
    result = response.json()
    return result.get("result", {}).get("content", [{}])[0].get("text", "{}")

print("="*60)
print("Testing MCP Provider Caching")
print("="*60)

# Step 1: Search for providers (this populates the cache)
print("\n📍 Step 1: Searching for providers...")
search_result = call_mcp_tool("search_providers_tool", {
    "specialty": "dentist",
    "radius_km": 5.0,
    "user_location": "Berlin"
})
search_data = json.loads(search_result)
providers = search_data.get("providers", [])
print(f"   Found {len(providers)} providers")

if not providers:
    print("❌ No providers found!")
    exit(1)

# Get the first provider's ID
provider_id = providers[0]["id"]
provider_name = providers[0]["name"]
print(f"   Selected provider: {provider_name} (ID: {provider_id})")

# Step 2: Get openings for the provider (should work with cached data)
print(f"\n📍 Step 2: Getting openings for {provider_id}...")
openings_result = call_mcp_tool("get_openings_tool", {
    "provider_id": provider_id
})
openings_data = json.loads(openings_result)
print(f"   Result: {openings_data}")

if "error" in openings_data:
    print(f"   ❌ ERROR: {openings_data['error']}")
    print("   Cache lookup failed!")
else:
    print(f"   ✅ SUCCESS: Found {len(openings_data.get('openings', []))} openings")
    print("   Cache is working!")

# Step 3: Test reserve_slot_tool with cached provider
if openings_data.get("openings"):
    slot = openings_data["openings"][0]
    print(f"\n📍 Step 3: Testing reserve_slot with cached provider...")
    reserve_result = call_mcp_tool("reserve_slot_tool", {
        "provider_id": provider_id,
        "start": slot["start"],
        "end": slot["end"]
    })
    reserve_data = json.loads(reserve_result)
    print(f"   Result: {reserve_data}")
    
    if "error" in reserve_data:
        print(f"   ❌ ERROR: {reserve_data['error']}")
    else:
        print(f"   ✅ SUCCESS: Reservation {'succeeded' if reserve_data.get('ok') else 'failed'}")

# Step 4: Test score_option_tool with cached provider
print(f"\n📍 Step 4: Testing score_option with cached provider...")
score_result = call_mcp_tool("score_option_tool", {
    "provider_id": provider_id,
    "start": slot["start"],
    "end": slot["end"]
})
score_data = json.loads(score_result)
print(f"   Result: {score_data}")

if "error" in score_data:
    print(f"   ❌ ERROR: {score_data['error']}")
else:
    print(f"   ✅ SUCCESS: Score = {score_data.get('score')}")

print("\n" + "="*60)
print("Test Complete!")
print("="*60)
