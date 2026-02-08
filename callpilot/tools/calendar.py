"""Calendar availability and event management.

This module provides functions for checking calendar availability
and creating calendar events. Can use either Google Calendar API
or MVP stubs based on configuration.
"""

from __future__ import annotations
from typing import Dict

from ..config import settings

# MVP: Hard-coded busy slots for testing
# Used when use_google_apis is False
BUSY = [
    {"start": "2026-02-10T15:00:00", "end": "2026-02-10T16:00:00"},
]


def check_calendar_free(slot: Dict[str, str]) -> bool:
    """Check if a time slot is available in the user's calendar.
    
    Uses Google Calendar API if configured, otherwise falls back to
    MVP stub with hard-coded busy periods.
    
    Args:
        slot: Dictionary with 'start' and 'end' ISO 8601 timestamps
              Example: {"start": "2026-02-10T14:00:00", "end": "2026-02-10T14:30:00"}
    
    Returns:
        True if the slot doesn't overlap with any busy periods,
        False if there's a conflict.
    """
    if settings.use_google_apis:
        try:
            from ..integrations.google_calendar import check_calendar_availability
            return check_calendar_availability(slot["start"], slot["end"])
        except Exception as e:
            print(f"Google Calendar API error, falling back to MVP: {e}")
            # Fall through to MVP implementation
    
    # MVP implementation
    s, e = slot["start"], slot["end"]
    
    # Check for overlap with each busy block
    # Slots don't overlap if: end <= busy_start OR start >= busy_end
    for b in BUSY:
        if not (e <= b["start"] or s >= b["end"]):
            return False  # Found an overlap
    return True


def create_calendar_event(title: str, slot: Dict[str, str], location: str) -> str:
    """Create a calendar event for the booked appointment.
    
    Uses Google Calendar API if configured, otherwise returns
    a demo event ID.
    
    Args:
        title: Event title (e.g., "Dentist appointment - Dr. Smith")
        slot: Time slot dictionary with 'start' and 'end' timestamps
        location: Event location/address
    
    Returns:
        Event ID string that can be used to reference the created event.
    """
    if settings.use_google_apis:
        try:
            from ..integrations.google_calendar import create_calendar_event as google_create_event
            event_id = google_create_event(
                title=title,
                start_time=slot["start"],
                end_time=slot["end"],
                location=location,
                description=f"Appointment booked via CallPilot"
            )
            if event_id:
                return event_id
            # Fall through to MVP if creation failed
        except Exception as e:
            print(f"Google Calendar API error, falling back to MVP: {e}")
            # Fall through to MVP implementation
    
    # MVP implementation
    return f"demo_event::{title}::{slot['start']}"

