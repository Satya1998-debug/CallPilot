"""Calendar availability and event management.

This module provides functions for checking calendar availability
and creating calendar events. Currently uses MVP stubs that will
be replaced with Google Calendar API integration.
"""

from __future__ import annotations
from typing import Dict

# MVP: Hard-coded busy slots for testing
# TODO: Replace with Google Calendar API queries
BUSY = [
    {"start": "2026-02-10T15:00:00", "end": "2026-02-10T16:00:00"},
]

def check_calendar_free(slot: Dict[str, str]) -> bool:
    """Check if a time slot is available in the user's calendar.
    
    Compares the proposed slot against known busy periods using
    ISO 8601 timestamp string comparison (works for same timezone).
    
    Args:
        slot: Dictionary with 'start' and 'end' ISO 8601 timestamps
              Example: {"start": "2026-02-10T14:00:00", "end": "2026-02-10T14:30:00"}
    
    Returns:
        True if the slot doesn't overlap with any busy periods,
        False if there's a conflict.
    
    Note:
        This is an MVP implementation. Production version should use
        Google Calendar API to query actual availability.
    """
    s, e = slot["start"], slot["end"]
    
    # Check for overlap with each busy block
    # Slots don't overlap if: end <= busy_start OR start >= busy_end
    for b in BUSY:
        if not (e <= b["start"] or s >= b["end"]):
            return False  # Found an overlap
    return True

def create_calendar_event(title: str, slot: Dict[str, str], location: str) -> str:
    """Create a calendar event for the booked appointment.
    
    Args:
        title: Event title (e.g., "Dentist appointment - Dr. Smith")
        slot: Time slot dictionary with 'start' and 'end' timestamps
        location: Event location/address
    
    Returns:
        Event ID string that can be used to reference the created event.
    
    Note:
        MVP implementation returns a demo ID. Production version will
        use Google Calendar API to create actual calendar events.
    """
    # TODO: Replace with Google Calendar API event creation
    return f"demo_event::{title}::{slot['start']}"
