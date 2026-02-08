from __future__ import annotations
import json
import os
import asyncio
from callpilot.graph import build_graph


def main(export_png: bool = False, use_speech: bool = False):
    use_mcp = os.getenv("USE_MCP", "").lower() in {"1", "true", "yes", "y"}
    app = build_graph(use_mcp=use_mcp)

    if export_png:
        from callpilot.viz import save_graph_png
        path = save_graph_png(app)
        print(f"[OK] Saved graph to: {path}")

    user_text = None
    if not use_speech:
        try:
            user_text = input("Enter your request: ").strip()
        except EOFError:
            user_text = None

    init_state = {
        "specialty": "dentist",
        "time_window": "this week afternoons",
        "radius_km": 5.0,
        "user_location": "Berlin",
        "transcript": [],
        "use_speech": use_speech,
        "user_text": user_text,
    }

    print("="*60)
    print("🚀 CallPilot Agent - Starting Workflow Execution")
    print("="*60)
    print("📋 Workflow sequence: pick_provider → call_provider → choose_slot → reserve_and_book → done")
    print("="*60)

    print(f"\n[DEBUG] Initial state keys: {list(init_state.keys())}")
    
    # Run workflow and get final state
    if use_mcp:
        final_state = asyncio.run(app.ainvoke(init_state))
    else:
        final_state = app.invoke(init_state)
        if final_state is None:
            # Fallback for older langgraph versions
            final_state = {}
            for value in app.stream(init_state, stream_mode="values"):
                if value is not None:
                    final_state = value
    print(f"[DEBUG] Final state type: {type(final_state)}")
    
    print("\n" + "="*60)
    print("✅ Workflow Complete - Final Result:")
    print("="*60)
    
    if final_state is None:
        print("ERROR: Graph returned None")
        return
    
    if isinstance(final_state, dict):
        # Extract the actual state from the event wrapper (if present)
        state_data = final_state
        if len(final_state) == 1:
            only_value = list(final_state.values())[0]
            if only_value is not None:
                state_data = only_value
        if state_data and "branch:to:done" in state_data:
            # Fallback: run the local nodes directly to recover final result
            from callpilot.graph import (
                node_pick_provider,
                node_call_provider,
                node_choose_slot,
                node_reserve_and_book,
                node_done,
            )
            state_data = init_state
            for fn in (
                node_pick_provider,
                node_call_provider,
                node_choose_slot,
                node_reserve_and_book,
                node_done,
            ):
                state_data = fn(state_data)
        if not state_data:
            print("ERROR: Empty final state")
            return
        if "result" in state_data:
            print(json.dumps(state_data["result"], indent=2))
        elif "result_text" in state_data:
            print(state_data["result_text"])
        else:
            print(json.dumps(state_data, indent=2))
    else:
        print(f"Unexpected output type: {type(final_state)}")
        print(final_state)
