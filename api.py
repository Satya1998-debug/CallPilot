from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from callpilot.graph import build_graph, run_local_proposal, confirm_local_booking

app = FastAPI(title="CallPilot API", version="0.1.0")


def _run_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
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
        result_state = app_graph.ainvoke(init_state)
        # LangGraph returns a coroutine when using async; we keep API sync for now
        # so only allow non-MCP mode until async server is added.
        raise RuntimeError("USE_MCP requires async server; disable USE_MCP for now")

    final_state = app_graph.invoke(init_state)
    if final_state is None:
        final_state = {}
        for value in app_graph.stream(init_state, stream_mode="values"):
            if value is not None:
                final_state = value

    if isinstance(final_state, dict) and "result" in final_state:
        return final_state["result"]
    return final_state


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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run_callpilot(req: RunRequest) -> RunResponse:
    result = _run_graph(req.model_dump())
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
def confirm_callpilot(req: ConfirmRequest) -> ConfirmResponse:
    state: Dict[str, Any] = {
        "provider": req.provider,
        "chosen_slot": req.slot,
        "specialty": req.specialty or req.provider.get("specialty"),
        "transcript": req.transcript or [],
    }
    final_state = confirm_local_booking(state)
    result = final_state.get("result", final_state) if isinstance(final_state, dict) else {"result": final_state}
    return ConfirmResponse(result=result)
