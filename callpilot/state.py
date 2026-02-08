"""State management for CallPilot agent workflow.

This module defines the state structure used throughout the LangGraph workflow.
The state is passed between nodes and accumulates information as the agent
progresses through the appointment booking process.
"""

from __future__ import annotations
from typing import TypedDict, Optional, List, Dict, Any

class CallState(TypedDict, total=False):
    """State object for the appointment booking workflow.
    
    This TypedDict contains all data that flows through the graph nodes.
    Using total=False allows nodes to populate fields incrementally.
    
    Attributes:
        specialty: Medical specialty requested (e.g., "dentist", "cardiology")
        time_window: Preferred time constraint (e.g., "this week afternoons")
        radius_km: Maximum distance from user location in kilometers
        user_location: User's location string (e.g., "Berlin", "Munich")

        provider: Dict[str, Any]  # Selected provider after matching
        
        proposed_slots: List[Dict[str, str]]  # Time slots offered by provider
                                               # Format: [{"start": ISO8601, "end": ISO8601}, ...]
        chosen_slot: Optional[Dict[str, str]]  # Final selected slot from proposed options
        
        calendar_ok: bool           # Whether chosen slot is free in user's calendar
        reservation_ok: bool        # Whether provider successfully reserved the slot
        event_id: Optional[str]     # Calendar event ID after booking
        
        transcript: List[str]       # Conversation log for debugging and display
        result: Dict[str, Any]      # Final booking result with all details
        messages: List[Any]         # LangChain messages for LLM + tool calling
        result_text: Optional[str]  # Final LLM summary (JSON string expected)
        use_speech: bool            # Enable ElevenLabs speech I/O
        user_text: Optional[str]    # External STT result (if use_speech)
        error: Optional[str]        # Error message if workflow fails
    """

    # Core request
    specialty: str
    time_window: str
    radius_km: float
    user_location: str

    # Provider selection + slots
    provider: Dict[str, Any]
    proposed_slots: List[Dict[str, str]]
    chosen_slot: Optional[Dict[str, str]]

    # Booking + calendar
    calendar_ok: bool
    reservation_ok: bool
    event_id: Optional[str]

    # Logging + result
    transcript: List[str]
    result: Dict[str, Any]

    # LLM/MCP fields
    messages: List[Any]
    result_text: Optional[str]

    # Speech I/O
    use_speech: bool
    user_text: Optional[str]

    # Extracted preferences from natural language
    preferred_provider: Optional[str]
    urgency: Optional[str]

    # Errors
    error: Optional[str]
