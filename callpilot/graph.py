from __future__ import annotations
import asyncio
from io import BytesIO
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from langgraph.graph import StateGraph, END
import json

import requests
from .state import CallState
from .tools.providers import search_providers
from .adapters.receptionist_sim import simulate_receptionist_call, reserve_slot
from .tools.calendar import check_calendar_free, create_calendar_event
from .tools.scoring import score

# Cache for MCP graph to avoid rebuilding
_mcp_graph_cache = None


def node_listen_user(state: CallState) -> CallState:
    """Optional speech-to-text hook (expects external STT to fill user_text)."""
    print("\n🔹 Executing Node: listen_user")
    if not state.get("use_speech"):
        try:
            user_text = input("Enter your request: ").strip()
            user_text = user_text.strip()  # Remove extra quotes if present
        except EOFError:
            user_text = None
    else:
        # seech to-text is expected to fill "user_text" in the state, so we just read it here
        load_dotenv()
        elevenlabs = ElevenLabs(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        )
        audio_url = ("https://storage.googleapis.com/eleven-public-cdn/audio/marketing/nicole.mp3")
        response = requests.get(audio_url)
        audio_data = BytesIO(response.content)
        transcription = elevenlabs.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v2", # Model to use
            tag_audio_events=True, # Tag audio events like laughter, applause, etc.
            language_code="eng", # Language of the audio file. If set to None, the model will detect the language automatically.
            diarize=True, # Whether to annotate who is speaking
        )
        user_text = transcription.text.strip()

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
    user_location = state.get("user_location", "Berlin")

    # Use local search function with user location
    matches = search_providers(
        specialty=specialty,
        radius_km=radius,
        user_location=user_location
    )
    
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
    global _mcp_graph_cache
    
    # Return cached graph if available
    if _mcp_graph_cache is not None:
        return _mcp_graph_cache
    
    from dotenv import load_dotenv
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_mcp_adapters.client import MultiServerMCPClient
    from langgraph.prebuilt import ToolNode

    load_dotenv()

    default_mcp_url = os.getenv("MCP_URL", "http://localhost:8000/mcp")
    llm_provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    # default_openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    default_ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
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

    # Handle async initialization properly - avoid nested event loop issues
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, use nest_asyncio or create task
        import nest_asyncio
        nest_asyncio.apply()
        tools = asyncio.run(get_mcp_tools())
    except RuntimeError:
        # No event loop running, safe to use asyncio.run
        tools = asyncio.run(get_mcp_tools())

    def node_extract_preferences(state: CallState) -> CallState:
        """Extract appointment preferences from user's natural language query.
        
        Uses LLM to parse user input and extract structured information like:
        - Medical specialty (if not already set)
        - Time preferences and constraints
        - Distance/location preferences
        - Specific provider names
        - Other booking preferences
        """
        print("\n🔹 Executing Node: extract_preferences")
        user_text = state.get("user_text", "")
        
        # Skip extraction if no user text
        if not user_text or not user_text.strip():
            # Set defaults if not already set
            updates = {}
            if not state.get("specialty"):
                updates["specialty"] = "dentist"
            if not state.get("time_window"):
                updates["time_window"] = "this week"
            if not state.get("radius_km"):
                updates["radius_km"] = 5.0
            if not state.get("user_location"):
                updates["user_location"] = "Berlin"
            if updates:
                return {**state, **updates}
            return state
        
        # Initialize LLM for extraction
        if llm_provider == "ollama":
            from langchain_ollama import ChatOllama
            extraction_model = ChatOllama(
                model=default_ollama_model,
                base_url=default_ollama_url,
                temperature=0.1,  # Low temperature for consistent extraction
            )
        # else:
        #     from langchain_openai import ChatOpenAI
        #     extraction_model = ChatOpenAI(model=default_openai_model, temperature=0.1)
        
        # Create extraction prompt
        extraction_prompt = f"""You are extracting structured appointment preferences from a user's request.

        User Query: "{user_text}"

        Current state (do NOT overwrite if already set):
        - Specialty: {state.get('specialty', 'NOT SET')}
        - Time window: {state.get('time_window', 'NOT SET')}
        - Radius (km): {state.get('radius_km', 'NOT SET')}
        - User location: {state.get('user_location', 'NOT SET')}

        Rules:
        - Return ONLY valid JSON. No prose, no markdown, no explanations.
        - Use null when the user did not specify the field.
        - Keep user wording for time_window when possible (e.g., "next Tuesday morning").
        - Convert distance to kilometers if stated in miles (mi -> km), otherwise use numeric km.
        - If user asks for "near me/nearby/close", set location_preference accordingly and radius_km to 3.0.
        - If a specific provider/practice name is mentioned, put it in provider_name verbatim.

        Output JSON schema:
        {{
        "specialty": "string or null",
        "time_window": "string or null",
        "radius_km": "number or null",
        "location_preference": "string or null",
        "provider_name": "string or null",
        "urgency": "string or null"
        }}
        """

        try:
            response = extraction_model.invoke(extraction_prompt)
            content = response.content.strip()
            
            # Extract JSON from response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
                
                # Update state with extracted values (only if not already set)
                updates = {}
                
                if extracted.get("specialty") and not state.get("specialty"):
                    updates["specialty"] = extracted["specialty"]
                
                if extracted.get("time_window") and not state.get("time_window"):
                    updates["time_window"] = extracted["time_window"]
                
                if extracted.get("radius_km") and not state.get("radius_km"):
                    try:
                        updates["radius_km"] = float(extracted["radius_km"])
                    except (ValueError, TypeError):
                        pass
                
                if extracted.get("location_preference"):
                    # Use location preference to adjust radius if "close" mentioned
                    loc_pref = extracted["location_preference"].lower()
                    if "close" in loc_pref or "near" in loc_pref or "nearby" in loc_pref:
                        updates["radius_km"] = min(state.get("radius_km", 5.0), 3.0)
                
                if extracted.get("provider_name"):
                    updates["preferred_provider"] = extracted["provider_name"]
                
                if extracted.get("urgency"):
                    updates["urgency"] = extracted["urgency"]
                
                # Set defaults for missing required fields
                if not updates.get("specialty") and not state.get("specialty"):
                    updates["specialty"] = "dentist"
                if not updates.get("time_window") and not state.get("time_window"):
                    updates["time_window"] = "this week"
                if not updates.get("radius_km") and not state.get("radius_km"):
                    updates["radius_km"] = 5.0
                if not updates.get("user_location") and not state.get("user_location"):
                    updates["user_location"] = "Berlin"
                
                if updates:
                    print(f"✓ Extracted preferences: {updates}")
                    return {**state, **updates}
            
        except Exception as e:
            print(f"⚠️  Preference extraction failed: {e}")
        
        # Fallback: set defaults if extraction failed
        updates = {}
        if not state.get("specialty"):
            updates["specialty"] = "dentist"
        if not state.get("time_window"):
            updates["time_window"] = "this week"
        if not state.get("radius_km"):
            updates["radius_km"] = 5.0
        if not state.get("user_location"):
            updates["user_location"] = "Berlin"
        
        if updates:
            print(f"✓ Using defaults: {updates}")
            return {**state, **updates}
        
        return state

    def node_init_messages(state: CallState) -> CallState:
        if state.get("messages"):
            return state

        specialty = state.get("specialty", "dentist")
        time_window = state.get("time_window", "this week")
        radius = state.get("radius_km", 5.0)
        location = state.get("user_location", "unknown")
        preferred_provider = state.get("preferred_provider")
        urgency = state.get("urgency")

        system = SystemMessage(
            content=(
                "You are CallPilot, an AI appointment-booking assistant. "
                "Your job is to help users book appointments. "
                "Use the relevant tools to search for providers first."
                "From there, find available appointment slots, "
                "check them against the user's calendar, call tools for checking availability, reserve the best option, "
                "then score and select the best option. "
            )
        )
        
        # Build constraints string with optional preferences
        constraints = (
            f"- specialty: {specialty}\n"
            f"- time_window: {time_window}\n"
            f"- radius_km: {radius}\n"
            f"- user_location: {location}\n"
        )
        if preferred_provider:
            constraints += f"- preferred_provider: {preferred_provider} (prioritize this provider if available)\n"
        if urgency:
            constraints += f"- urgency: {urgency} (consider when selecting slots)\n"
        
        user = HumanMessage(
            content=(
                "Book an appointment with these constraints:\n"
                f"{constraints}\n"
                "  1. Search for providers matching the specialty\n"
                "  2. Find available appointment slots\n"
                "  3. Check which slots are free in the calendar\n"
                "  4. Reserve the best matching appointment\n"
                "  5. Return complete appointment details\n"
                "\n"
                "After receiving the result, return a JSON summary with:\n"
                "  - provider_name, address, rating\n"
                "  - appointment_time (slot start)\n"
                "  - score\n"
                "\n"
                "The calendar event will be created automatically - you don't need to create it."
            )
        )
        return {**state, "messages": [system, user]}

    def node_agent(state: CallState) -> CallState:
        # Initialize model
        if llm_provider == "ollama":
            from langchain_ollama import ChatOllama
            model = ChatOllama(
                model=default_ollama_model,
                base_url=default_ollama_url,
                temperature=0.4,
            )
        
        model = model.bind_tools(tools)
        
        # Initialize messages if this is the first call
        if "messages" not in state or not state["messages"]:
            sys_prompt = f"""You are CallPilot, an AI appointment-booking assistant.

            Current booking request:
            - specialty: {state.get("specialty") or "dentist"}
            - time_window: {state.get("time_window") or "this week"}
            - radius_km: {state.get("radius_km") or 5.0}
            - user_location: {state.get("user_location") or "Berlin"}

            Your job:
            - Use the available tools to find providers and book appointments.
            - Never invent data - always use tools to get real information.
            - Call tools in this order:
            1) search_providers_tool - find matching providers
            2) get_openings_tool - get available slots for providers
            3) check_calendar_free_tool - verify slot availability (optional)
            4) reserve_slot_tool - reserve the chosen slot
            5) score_option_tool - score the appointment

            After completing all tool calls, return a JSON summary with this exact schema:
            {{
            "provider": {{"id": "...", "name": "...", "address": "...", "rating": 0, "distance_km": 0}},
            "slot": {{"start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS"}},
            "score": 0
            }}

            If no valid appointment is found, return a dummy appointment with the schema above."""
                        
            user_prompt = f"""Please book an appointment with these requirements:
            - Specialty: {state.get("specialty") or "dentist"}
            - Time window: {state.get("time_window") or "this week"}
            - Maximum distance: {state.get("radius_km") or 5.0} km from {state.get("user_location") or "Berlin"}

            Use the tools to complete this booking."""
                        
            state["messages"] = [
                SystemMessage(content=sys_prompt),
                HumanMessage(content=user_prompt)
            ]
        
        # Use existing messages (contains tool results from previous iterations)
        messages = state["messages"]
        
        # Invoke model with full conversation history
        resp = model.invoke(messages)
        
        # Debug: log tool calls if present
        if hasattr(resp, 'tool_calls') and resp.tool_calls:
            print(f"🔧 Agent requesting {len(resp.tool_calls)} tool call(s):")
            for tc in resp.tool_calls:
                print(f"   - {tc.get('name', 'unknown')} with args: {tc.get('args', {})}")
        
        # Append response to message history
        state["messages"] = messages + [resp]

        # Try to parse JSON summary from the response content
        summary = None
        try:
            summary = json.loads(resp.content)
        except Exception:
            # fallback: keep raw content, you can add a "repair json" step later
            summary = {"raw": resp.content}

        state["best_option"] = summary
        return state

    def node_finalize(state: CallState) -> CallState:
        last = state["messages"][-1]
        result_text = getattr(last, "content", "")
        return {**state, "result_text": result_text}


    def check_calendar_free_tool(start: str, end: str) -> dict:
        """Check if a time slot is free in the user's calendar.
        
        Verifies if the proposed appointment time conflicts with existing events.
        Uses Google Calendar API when configured, otherwise uses MVP stub data.
        
        Args:
            start: Slot start time as ISO 8601 timestamp (e.g., "2026-02-10T14:00:00")
            end: Slot end time as ISO 8601 timestamp
        
        Returns:
            {"free": True if available, False if busy}
        """
        ok = check_calendar_free({"start": start, "end": end})
        return ok

    def node_create_calendar_event(state: CallState) -> CallState:
        """Automatically create calendar event after LLM finds best appointment.
        
        Extracts appointment details from tool results and creates calendar event.
        This runs automatically - not an LLM-callable tool.
        """
        print("\n🔹 Executing Node: create_calendar_event")
        
        appointment_details = state.get("best_option", {})
        
        # Check if we have valid appointment details
        has_valid_appointment = (
            appointment_details and 
            isinstance(appointment_details, dict) and
            appointment_details.get("provider") and 
            appointment_details.get("slot")
        )
        
        if not has_valid_appointment:
            print("⚠️  No valid appointment found - creating dummy appointment")
            # Create dummy appointment as fallback
            from datetime import datetime, timedelta
            
            # Generate a dummy slot for tomorrow at 10 AM
            tomorrow = datetime.now() + timedelta(days=1)
            dummy_start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
            dummy_end = dummy_start + timedelta(minutes=30)
            
            appointment_details = {
                "provider": {
                    "id": "dummy_provider_1",
                    "name": "General Medical Clinic",
                    "address": "Berlin, Germany",
                    "rating": 0,
                    "distance_km": 0
                },
                "slot": {
                    "start": dummy_start.isoformat(),
                    "end": dummy_end.isoformat()
                },
                "score": 0
            }
            state["best_option"] = appointment_details
            print(f"   Dummy appointment: {appointment_details['provider']['name']} at {dummy_start.strftime('%Y-%m-%d %H:%M')}")
        
        start = appointment_details.get("slot", {}).get("start")
        end = appointment_details.get("slot", {}).get("end")
        
        if start and end:
            ok = check_calendar_free_tool(start, end)
            
            if ok:
                print(f"✓ Slot is free in calendar: {start} to {end}")
            else:
                print(f"⚠️  Slot is NOT free in calendar: {start} to {end}")
            
            # Extract details
            provider = appointment_details["provider"]
            slot = appointment_details["slot"]
            
            # Create calendar event regardless of calendar availability
            title = f"{state.get('specialty', 'Medical').title()} Appointment - {provider['name']}"
            location = provider.get("address", "")
            
            event_id = create_calendar_event(
                title=title,
                slot=slot,
                location=location
            )
            
            print(f"✓ Calendar event created: {event_id}")
        else:
            print("⚠️  Invalid slot times, cannot create calendar event")
            event_id = None
        
        # Update state with event_id
        return {**state, "event_id": event_id}

    def route_after_agent(state: CallState) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return "finalize"

    g = StateGraph(CallState)
    g.add_node("listen_user", node_listen_user)
    g.add_node("extract_preferences", node_extract_preferences)
    # g.add_node("init", node_init_messages)
    g.add_node("agent", node_agent)
    g.add_node("tools", ToolNode(tools))
    g.add_node("finalize", node_finalize)
    g.add_node("create_event", node_create_calendar_event)
    g.add_node("speak_user", node_speak_user)

    g.set_entry_point("listen_user")
    g.add_edge("listen_user", "extract_preferences")
    g.add_edge("extract_preferences", "agent")
    # g.add_edge("init", "agent")
    g.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "finalize": "finalize"},
    )
    g.add_edge("tools", "agent")
    g.add_edge("finalize", "create_event")
    g.add_edge("create_event", "speak_user")
    g.add_edge("speak_user", END)

    # Cache the compiled graph
    _mcp_graph_cache = g.compile()
    return _mcp_graph_cache


def build_graph(use_mcp: bool | None = None):
    """Build and compile the appointment booking graph."""
    if use_mcp is None:
        use_mcp = os.getenv("USE_MCP", "").lower() in {"1", "true", "yes", "y"}
    if use_mcp:
        return build_graph_mcp()
    return build_graph_local()


def build_graph_local():
    """Build and compile the local (non-LLM) appointment booking graph."""
    g = StateGraph(CallState)
    g.add_node("pick_provider", node_pick_provider)
    g.add_node("call_provider", node_call_provider)
    g.add_node("choose_slot", node_choose_slot)
    g.add_node("reserve_and_book", node_reserve_and_book)
    g.add_node("done", node_done)

    g.set_entry_point("pick_provider")
    g.add_edge("pick_provider", "call_provider")
    g.add_edge("call_provider", "choose_slot")
    g.add_edge("choose_slot", "reserve_and_book")
    g.add_edge("reserve_and_book", "done")
    g.add_edge("done", END)

    return g.compile()


def run_local_proposal(init_state: CallState) -> CallState:
    """Run the local flow up to a proposed slot (no booking)."""
    state = node_pick_provider(init_state)
    state = node_call_provider(state)
    state = node_choose_slot(state)

    proposal = {
        "provider": state.get("provider"),
        "slot": state.get("chosen_slot"),
        "calendar_ok": state.get("calendar_ok"),
        "error": state.get("error"),
        "transcript": state.get("transcript", []),
    }
    return {**state, "proposal": proposal}


def confirm_local_booking(state: CallState) -> CallState:
    """Finalize booking and calendar event for a proposed slot."""
    state = node_reserve_and_book(state)
    state = node_done(state)
    return state
