from __future__ import annotations
import asyncio
import os
from typing import Any, Dict, List

from langgraph.graph import StateGraph, END

from .state import CallState
from .tools.providers import search_providers
from .adapters.receptionist_sim import simulate_receptionist_call, reserve_slot
from .tools.calendar import check_calendar_free, create_calendar_event
from .tools.scoring import score


def node_listen_user(state: CallState) -> CallState:
    """Optional speech-to-text hook (expects external STT to fill user_text)."""
    print("\n🔹 Executing Node: listen_user")
    if not state.get("use_speech"):
        user_text = state.get("user_text")
    transcript = state.get("transcript", []) + [f"[USER] {user_text}"]
    return {**state, "transcript": transcript}


def node_speak_user(state: CallState) -> CallState:
    """Optional text-to-speech hook using ElevenLabs."""
    print("\n🔹 Executing Node: speak_user")
    if not state.get("use_speech"):
        return state

    try:
        from dotenv import load_dotenv
        from elevenlabs.client import ElevenLabs
        from elevenlabs.play import play
    except Exception as e:
        return {**state, "error": f"ElevenLabs import failed: {e}"}

    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return {**state, "error": "Missing ELEVENLABS_API_KEY"}

    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    output_format = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")

    text = ""
    if state.get("result_text"):
        text = state["result_text"]
    elif state.get("result"):
        text = str(state["result"])
    else:
        text = "Your request is complete."

    elevenlabs = ElevenLabs(api_key=api_key)
    audio = elevenlabs.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id=model_id,
        output_format=output_format,
    )
    play(audio)
    return state


def node_pick_provider(state: CallState) -> CallState:
    """Pick the best provider based on specialty and distance."""
    print("\n🔹 Executing Node: pick_provider")
    specialty = state.get("specialty", "dentist")
    radius = float(state.get("radius_km", 5.0))

    # Use local search function
    matches = search_providers(specialty=specialty, radius_km=radius)
    
    if not matches:
        return {**state, "error": "No providers found in radius."}

    provider = sorted(matches, key=lambda p: float(p.get("distance_km", 999)))[0]
    print(f"✓ Selected: {provider.get('name', 'Unknown')}")
    return {
        **state, 
        "provider": provider, 
        "transcript": state.get("transcript", []) + [f"[SYS] Selected provider: {provider['name']}"]
    }

def node_call_provider(state: CallState) -> CallState:
    """Simulate receptionist call to get available slots."""
    print("\n🔹 Executing Node: call_provider")
    if state.get("error"):
        return state
    
    provider = state.get("provider")
    if not provider:
        return {**state, "error": "No provider selected"}
    
    constraint = state.get("time_window", "this week")
    res = simulate_receptionist_call(provider, constraint)
    transcript = state.get("transcript", []) + res["transcript"]
    return {**state, "proposed_slots": res["slots"], "transcript": transcript}


def node_choose_slot(state: CallState) -> CallState:
    """Choose first available slot that fits user's calendar."""
    print("\n🔹 Executing Node: choose_slot")
    if state.get("error"):
        return state
    
    slots = state.get("proposed_slots", [])
    if not slots:
        return {**state, "error": "Provider had no slots."}

    # Check each slot against calendar
    for s in slots:
        if check_calendar_free(s):
            return {
                **state, 
                "chosen_slot": s, 
                "calendar_ok": True,
                "transcript": state.get("transcript", []) + [f"[SYS] Calendar ok for {s['start']}"]
            }

    return {**state, "calendar_ok": False, "error": "No proposed slot fits calendar."}

def node_reserve_and_book(state: CallState) -> CallState:
    """Reserve slot with provider and create calendar event."""
    print("\n🔹 Executing Node: reserve_and_book")
    if state.get("error"):
        return state

    provider = state.get("provider")
    slot = state.get("chosen_slot")
    
    if not provider or not slot:
        return {**state, "error": "Missing provider or slot"}

    # Reserve the slot
    reservation_ok = reserve_slot(provider, slot)
    if not reservation_ok:
        return {**state, "reservation_ok": False, "error": "Reservation failed."}

    # Create calendar event
    event_id = create_calendar_event(
        title=f"{provider['specialty'].title()} appointment - {provider['name']}",
        slot=slot,
        location=provider.get("address", provider.get("name", ""))
    )
    
    # Score the option
    sc = score(provider, slot)

    result = {
        "provider": {
            "id": provider["id"], 
            "name": provider["name"], 
            "rating": provider.get("rating"), 
            "distance_km": provider.get("distance_km")
        },
        "slot": slot,
        "score": sc,
        "event_id": event_id,
    }
    
    transcript = state.get("transcript", []) + [f"[SYS] Reserved + created event: {event_id}"]
    return {
        **state, 
        "reservation_ok": True, 
        "event_id": event_id, 
        "result": result, 
        "transcript": transcript
    }

def node_done(state: CallState) -> CallState:
    """Finalize workflow result."""
    print("\n🔹 Executing Node: done")
    
    # Handle error case
    if state.get("error") and not state.get("result"):
        return {
            **state, 
            "result": {
                "status": "failed", 
                "error": state["error"], 
                "transcript": state.get("transcript", [])
            }
        }
    
    # Ensure result has status and transcript
    if state.get("result"):
        result = state["result"]
        result["status"] = "success"
        result["transcript"] = state.get("transcript", [])
        return {**state, "result": result}
    
    # Default result
    return {
        **state, 
        "result": {
            "status": "completed", 
            "transcript": state.get("transcript", [])
        }
    }


def build_graph_mcp():
    """Build and compile the LLM + MCP tool-calling graph."""
    from dotenv import load_dotenv
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langgraph.prebuilt import ToolNode

    load_dotenv()

    default_mcp_url = os.getenv("MCP_URL", "http://localhost:8000/mcp")
    llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    #default_openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    default_ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
    default_ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def get_mcp_client():
        return MultiServerMCPClient(
            {
                "callpilot": {
                    "url": default_mcp_url,
                    "transport": "http",
                }
            }
        )

    async def get_mcp_tools():
        client = await get_mcp_client()
        return await client.get_tools()

    tools = asyncio.run(get_mcp_tools())

    def node_init_messages(state: CallState) -> CallState:
        if state.get("messages"):
            return state

        specialty = state.get("specialty", "dentist")
        time_window = state.get("time_window", "this week")
        radius = state.get("radius_km", 5.0)
        location = state.get("user_location", "unknown")

        system = SystemMessage(
            content=(
                "You are CallPilot, an appointment-booking agent. "
                "Use the available tools to find providers, check openings, "
                "verify calendar availability, reserve a slot, and create a calendar event. "
                "Return a concise JSON summary when finished."
            )
        )
        user = HumanMessage(
            content=(
                "Book an appointment with these constraints:\n"
                f"- specialty: {specialty}\n"
                f"- time_window: {time_window}\n"
                f"- radius_km: {radius}\n"
                f"- user_location: {location}\n\n"
                "Use tools in this order if needed:\n"
                "1) search_providers_tool\n"
                "2) get_openings_tool\n"
                "3) check_calendar_free_tool\n"
                "4) reserve_slot_tool\n"
                "5) create_calendar_event_tool\n"
                "6) score_option_tool\n\n"
                "Finish by returning JSON with keys: provider, slot, score, event_id."
            )
        )
        return {**state, "messages": [system, user]}

    def node_agent(state: CallState) -> CallState:
        if "messages" not in state:
            state = node_init_messages(state)
        if llm_provider == "ollama":
            from langchain_ollama import ChatOllama

            model = ChatOllama(
                model=default_ollama_model,
                base_url=default_ollama_url,
                temperature=0.4,
            )
        else:
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(model=default_openai_model, temperature=0.4)
        model = model.bind_tools(tools)
        response = model.invoke(state["messages"])
        return {"messages": state.get("messages", []) + [response]}

    def node_finalize(state: CallState) -> CallState:
        last = state["messages"][-1]
        result_text = getattr(last, "content", "")
        return {**state, "result_text": result_text}

    def route_after_agent(state: CallState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return "finalize"

    g = StateGraph(CallState)
    g.add_node("listen_user", node_listen_user)
    g.add_node("init", node_init_messages)
    g.add_node("agent", node_agent)
    g.add_node("tools", ToolNode(tools))
    g.add_node("finalize", node_finalize)
    g.add_node("speak_user", node_speak_user)

    g.set_entry_point("listen_user")
    g.add_edge("listen_user", "init")
    g.add_edge("init", "agent")
    g.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "finalize": "finalize"},
    )
    g.add_edge("tools", "agent")
    g.add_edge("finalize", "speak_user")
    g.add_edge("speak_user", END)

    return g.compile()


def build_graph(use_mcp: bool | None = None):
    """Build and compile the appointment booking graph."""
    if use_mcp is None:
        use_mcp = os.getenv("USE_MCP", "").lower() in {"1", "true", "yes", "y"}
    if use_mcp:
        return build_graph_mcp()
