"""Simulated receptionist phone call adapter.

This module simulates calling a provider's office to negotiate and book
an appointment. In production, this would be replaced with ElevenLabs
Conversational AI making actual phone calls.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

def simulate_receptionist_call(provider: Dict[str, Any], constraint: str) -> Dict[str, Any]:
    """Simulate a phone call with a provider's receptionist.
    
    Creates a fake conversation transcript and returns available appointment
    slots from the provider's opening list. This is an MVP stub that will
    be replaced with real ElevenLabs voice agent integration.
    
    Args:
        provider: Provider dictionary containing:
                 - name: Provider/practice name
                 - openings: List of available time slots
        constraint: User's scheduling constraint (e.g., "this week afternoons")
    
    Returns:
        Dictionary with:
        - ok: Boolean indicating if call was successful
        - slots: List of available time slots (up to 3)
        - transcript: List of conversation lines for logging
    
    Example:
        >>> provider = {"name": "Mitte Dental", "openings": [...]}
        >>> result = simulate_receptionist_call(provider, "this week")
        >>> print(result['ok'])
        True
        >>> print(len(result['slots']))
        3
    
    Note:
        Production implementation will use ElevenLabs WebSocket API
        to conduct actual voice conversations with provider offices.
    """
    openings: List[Dict[str, str]] = provider.get("openings", [])
    
    # Build simulated conversation transcript
    transcript = [
        f"[CALL] Calling {provider['name']}...",
        "[RECEP] Hello, how can I help?",
        f"[AGENT] I'd like to book an appointment. Constraint: {constraint}",
    ]
    
    # Check if provider has any availability
    if not openings:
        transcript.append("[RECEP] Sorry, no availability.")
        return {"ok": False, "slots": [], "transcript": transcript}
    
    # Return top 3 available slots (MVP: just take first 3 from list)
    slots = openings[:3]
    transcript.append(f"[RECEP] We can do: {', '.join(s['start'] for s in slots)}")
    transcript.append("[AGENT] Great, let me confirm one moment.")
    
    return {"ok": True, "slots": slots, "transcript": transcript}

def reserve_slot(provider: Dict[str, Any], slot: Dict[str, str]) -> bool:
    """Reserve a time slot with the provider.
    
    Args:
        provider: Provider dictionary
        slot: Time slot to reserve
    
    Returns:
        True if reservation successful, False otherwise.
    
    Note:
        MVP always returns True. Production version would make an actual
        API call or phone call to confirm the reservation.
    """
    # TODO: Replace with actual provider API/phone call integration
    return True
