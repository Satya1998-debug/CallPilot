from __future__ import annotations

import os
import asyncio
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from callpilot.graph import build_graph, run_local_proposal, confirm_local_booking

app = FastAPI(title="CallPilot API", version="0.1.0")


async def _run_graph_async(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run the graph workflow asynchronously (supports both MCP and local modes)."""
    use_mcp = os.getenv("USE_MCP", "").lower() in {"1", "true", "yes", "y"}
    app_graph = build_graph(use_mcp=use_mcp)

    init_state: Dict[str, Any] = {
        "specialty": payload.get("specialty", "dentist"),
        "time_window": payload.get("time_window", "this week afternoons"),
        "radius_km": float(payload.get("radius_km", 5.0)),
        "user_location": payload.get("user_location", "Berlin"),
        "transcript": [],
        "use_speech": False,
        "user_text": payload.get("user_text"),
    }

    if use_mcp:
        # Use async invocation for MCP mode
        final_state = await app_graph.ainvoke(init_state)
    else:
        # Use sync invocation for local mode (run in executor to keep API async)
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, app_graph.invoke, init_state)
        if final_state is None:
            final_state = {}
            for value in app_graph.stream(init_state, stream_mode="values"):
                if value is not None:
                    final_state = value

    if isinstance(final_state, dict) and "result" in final_state:
        return final_state["result"]
    if isinstance(final_state, dict) and "result_text" in final_state:
        return {"result_text": final_state["result_text"], "best_option": final_state.get("best_option")}
    return final_state


def _run_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sync wrapper for backward compatibility."""
    return asyncio.run(_run_graph_async(payload))


class RunRequest(BaseModel):
    specialty: Optional[str] = Field(default="dentist")
    time_window: Optional[str] = Field(default="this week afternoons")
    radius_km: Optional[float] = Field(default=5.0)
    user_location: Optional[str] = Field(default="Berlin")
    user_text: Optional[str] = Field(default=None)


class RunResponse(BaseModel):
    result: Dict[str, Any]

class ProposeResponse(BaseModel):
    proposal: Dict[str, Any]
    state: Dict[str, Any]


class ConfirmRequest(BaseModel):
    provider: Dict[str, Any]
    slot: Dict[str, Any]
    specialty: Optional[str] = Field(default=None)
    transcript: Optional[list[str]] = Field(default_factory=list)


class ConfirmResponse(BaseModel):
    result: Dict[str, Any]


class ChatRequest(BaseModel):
    message: str = Field(description="User's chat message")
    use_mcp: Optional[bool] = Field(default=None, description="Force MCP mode")
    conversation_history: Optional[list[Dict[str, str]]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    message: str = Field(description="Assistant's response message")
    appointment: Optional[Dict[str, Any]] = Field(default=None, description="Appointment details if found")
    requires_confirmation: bool = Field(default=False, description="Whether user confirmation is needed")
    event_id: Optional[str] = Field(default=None, description="Calendar event ID if created")
    error: Optional[str] = Field(default=None, description="Error message if any")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
async def run_callpilot(req: RunRequest) -> RunResponse:
    """Run the full booking workflow and return the final result."""
    result = await _run_graph_async(req.model_dump())
    return RunResponse(result=result)


@app.post("/propose", response_model=ProposeResponse)
def propose_callpilot(req: RunRequest) -> ProposeResponse:
    init_state: Dict[str, Any] = {
        "specialty": req.specialty,
        "time_window": req.time_window,
        "radius_km": float(req.radius_km or 5.0),
        "user_location": req.user_location,
        "transcript": [],
        "use_speech": False,
        "user_text": req.user_text,
    }
    state = run_local_proposal(init_state)
    proposal = state.get("proposal", {})
    # Return minimal state needed for confirmation
    confirm_state = {
        "provider": state.get("provider"),
        "chosen_slot": state.get("chosen_slot"),
        "specialty": state.get("specialty"),
        "transcript": state.get("transcript", []),
    }
    return ProposeResponse(proposal=proposal, state=confirm_state)


@app.post("/confirm", response_model=ConfirmResponse)
async def confirm_callpilot(req: ConfirmRequest) -> ConfirmResponse:
    """Confirm and finalize a proposed appointment booking."""
    state: Dict[str, Any] = {
        "provider": req.provider,
        "chosen_slot": req.slot,
        "specialty": req.specialty or req.provider.get("specialty"),
        "transcript": req.transcript or [],
    }
    loop = asyncio.get_event_loop()
    final_state = await loop.run_in_executor(None, confirm_local_booking, state)
    result = final_state.get("result", final_state) if isinstance(final_state, dict) else {"result": final_state}
    return ConfirmResponse(result=result)


@app.post("/run_mcp")
async def run_mcp_workflow(req: RunRequest) -> Dict[str, Any]:
    """Run the MCP-based LLM agent workflow.
    
    This endpoint forces MCP mode regardless of the USE_MCP env variable.
    Returns the complete final state including messages, best_option, and event_id.
    """
    # Force MCP mode for this endpoint
    original_use_mcp = os.getenv("USE_MCP")
    os.environ["USE_MCP"] = "true"
    
    try:
        app_graph = build_graph(use_mcp=True)
        
        init_state: Dict[str, Any] = {
            "specialty": req.specialty,
            "time_window": req.time_window,
            "radius_km": float(req.radius_km or 5.0),
            "user_location": req.user_location,
            "transcript": [],
            "use_speech": False,
            "user_text": req.user_text,
        }
        
        final_state = await app_graph.ainvoke(init_state)
        
        # Extract relevant information
        return {
            "result_text": final_state.get("result_text", ""),
            "best_option": final_state.get("best_option", {}),
            "event_id": final_state.get("event_id"),
            "messages_count": len(final_state.get("messages", [])),
            "specialty": final_state.get("specialty"),
            "user_location": final_state.get("user_location"),
        }
    finally:
        # Restore original USE_MCP value
        if original_use_mcp is not None:
            os.environ["USE_MCP"] = original_use_mcp
        else:
            os.environ.pop("USE_MCP", None)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Handle chat messages directly from the UI.
    
    This endpoint processes user messages and returns structured responses.
    It automatically determines whether to use MCP or local workflow.
    """
    use_mcp_mode = req.use_mcp if req.use_mcp is not None else os.getenv("USE_MCP", "").lower() in {"1", "true", "yes", "y"}
    
    if use_mcp_mode:
        # MCP/LLM Agent Mode - full workflow
        try:
            original_use_mcp = os.getenv("USE_MCP")
            os.environ["USE_MCP"] = "true"
            
            app_graph = build_graph(use_mcp=True)
            
            init_state: Dict[str, Any] = {
                "transcript": [],
                "use_speech": False,
                "user_text": req.message,
            }
            
            final_state = await app_graph.ainvoke(init_state)
            
            # Extract response
            result_text = final_state.get("result_text", "I've processed your request.")
            best_option = final_state.get("best_option", {})
            event_id = final_state.get("event_id")
            
            appointment_data = None
            if isinstance(best_option, dict) and best_option.get("provider"):
                appointment_data = best_option
            
            # Restore original USE_MCP value
            if original_use_mcp is not None:
                os.environ["USE_MCP"] = original_use_mcp
            else:
                os.environ.pop("USE_MCP", None)
            
            return ChatResponse(
                message=result_text,
                appointment=appointment_data,
                requires_confirmation=False,  # MCP handles booking automatically
                event_id=event_id,
                error=None
            )
            
        except Exception as e:
            return ChatResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                error=str(e),
                requires_confirmation=False
            )
    else:
        # Local workflow mode - propose first, then confirm
        try:
            init_state: Dict[str, Any] = {
                "specialty": None,  # Will be extracted from message
                "time_window": None,
                "radius_km": 5.0,
                "user_location": "Berlin",
                "transcript": [],
                "use_speech": False,
                "user_text": req.message,
            }
            
            # Run proposal
            loop = asyncio.get_event_loop()
            state = await loop.run_in_executor(None, run_local_proposal, init_state)
            proposal = state.get("proposal", {})
            
            if proposal.get("error"):
                return ChatResponse(
                    message=f"I couldn't find an appointment: {proposal['error']}",
                    error=proposal['error'],
                    requires_confirmation=False
                )
            
            provider = proposal.get("provider", {})
            slot = proposal.get("slot", {})
            
            appointment_data = {
                "provider": provider,
                "slot": slot,
                "_state": {  # Internal state for confirmation
                    "provider": state.get("provider"),
                    "chosen_slot": state.get("chosen_slot"),
                    "specialty": state.get("specialty"),
                    "transcript": state.get("transcript", []),
                }
            }
            
            message = f"I found an appointment with {provider.get('name', 'a provider')} at {slot.get('start', 'an available time')}.\n\nWould you like me to book this appointment?"
            
            return ChatResponse(
                message=message,
                appointment=appointment_data,
                requires_confirmation=True,
                error=None
            )
            
        except Exception as e:
            return ChatResponse(
                message=f"I encountered an error: {str(e)}",
                error=str(e),
                requires_confirmation=False
            )

@app.get("/ping")
def ping():
    return {"ok": True}

@app.post("/chat/confirm")
async def chat_confirm(req: ConfirmRequest) -> ChatResponse:
    """Confirm and book an appointment from chat."""
    try:
        state: Dict[str, Any] = {
            "provider": req.provider,
            "chosen_slot": req.slot,
            "specialty": req.specialty or req.provider.get("specialty"),
            "transcript": req.transcript or [],
        }
        
        loop = asyncio.get_event_loop()
        final_state = await loop.run_in_executor(None, confirm_local_booking, state)
        result = final_state.get("result", final_state) if isinstance(final_state, dict) else {"result": final_state}
        
        event_id = result.get("event_id") if isinstance(result, dict) else None
        
        if event_id:
            message = f"✅ Appointment booked successfully!\n\nCalendar event ID: {event_id}"
        else:
            message = "✅ Appointment booked successfully!"
        
        return ChatResponse(
            message=message,
            appointment=result,
            requires_confirmation=False,
            event_id=event_id,
            error=None
        )
        
    except Exception as e:
        return ChatResponse(
            message=f"❌ Booking failed: {str(e)}",
            error=str(e),
            requires_confirmation=False
        )
        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
