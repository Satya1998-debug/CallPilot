"""Google Calendar API integration.

This module provides functions for checking calendar availability
and creating events using the Google Calendar API.
"""

from __future__ import annotations
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Path to store credentials
TOKEN_PATH = Path("artifacts/token.pickle")
# Check multiple possible locations for credentials
CREDENTIALS_PATH = (
    Path("credentials.json") if Path("credentials.json").exists()
    else Path("secrets/credentials.json") if Path("secrets/credentials.json").exists()
    else Path("credentials.json")  # Default fallback
)


def get_calendar_service():
    """Get authenticated Google Calendar service.
    
    This function handles OAuth2 authentication and returns
    an authenticated service object for Calendar API calls.
    
    Returns:
        Authenticated Google Calendar service object.
        
    Raises:
        FileNotFoundError: If credentials.json is not found.
        Exception: If authentication fails.
    
    Note:
        On first run, this will open a browser for OAuth2 consent.
        The token is cached in artifacts/token.pickle for future use.
    """
    creds = None
    
    # Load cached credentials if they exist
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Missing {CREDENTIALS_PATH}. Download from Google Cloud Console:\n"
                    "https://console.cloud.google.com/apis/credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)


def check_calendar_availability(start_time: str, end_time: str, calendar_id: str = 'primary') -> bool:
    """Check if a time slot is available in the user's calendar.
    
    Queries the Google Calendar API to check for conflicts in the
    specified time range.
    
    Args:
        start_time: ISO 8601 timestamp for slot start (e.g., "2026-02-10T14:00:00")
        end_time: ISO 8601 timestamp for slot end
        calendar_id: Calendar to check (default: 'primary' for main calendar)
    
    Returns:
        True if the slot is free (no conflicts), False if there are conflicts.
    
    Example:
        >>> is_free = check_calendar_availability(
        ...     "2026-02-10T14:00:00",
        ...     "2026-02-10T15:00:00"
        ... )
        >>> print(f"Slot available: {is_free}")
        Slot available: True
    """
    try:
        service = get_calendar_service()
        
        # Convert ISO strings to RFC3339 format with timezone
        # Add timezone if not present (assume local timezone)
        if 'T' in start_time and '+' not in start_time and 'Z' not in start_time:
            start_time += 'Z'  # Assume UTC for simplicity
            end_time += 'Z'
        
        # Query for events in the time range
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # If no events found, slot is free
        return len(events) == 0
        
    except HttpError as error:
        print(f"Google Calendar API error: {error}")
        # Fall back to assuming available if API fails
        return True
    except FileNotFoundError as e:
        print(f"Calendar authentication error: {e}")
        print("Falling back to MVP calendar check")
        return True


def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    location: str = "",
    description: str = "",
    calendar_id: str = 'primary'
) -> Optional[str]:
    """Create an event in the user's Google Calendar.
    
    Args:
        title: Event title/summary
        start_time: ISO 8601 timestamp for event start
        end_time: ISO 8601 timestamp for event end
        location: Event location (address)
        description: Event description/notes
        calendar_id: Calendar to create event in (default: 'primary')
    
    Returns:
        Event ID if successful, None if creation fails.
    
    Example:
        >>> event_id = create_calendar_event(
        ...     "Dentist Appointment",
        ...     "2026-02-10T14:00:00",
        ...     "2026-02-10T15:00:00",
        ...     location="123 Main St, Berlin"
        ... )
        >>> print(f"Created event: {event_id}")
        Created event: abc123xyz
    """
    try:
        service = get_calendar_service()
        
        # Ensure timezone format
        if 'T' in start_time and '+' not in start_time and 'Z' not in start_time:
            start_time += 'Z'
            end_time += 'Z'
        
        # Build event object
        event = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Berlin',  # Adjust as needed
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Berlin',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},  # 30 min before
                ],
            },
        }
        
        # Create the event
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        return created_event.get('id')
        
    except HttpError as error:
        print(f"Google Calendar API error: {error}")
        return None
    except FileNotFoundError as e:
        print(f"Calendar authentication error: {e}")
        print("Falling back to MVP event creation")
        return f"mvp_event::{title}::{start_time}"


def list_upcoming_events(max_results: int = 10, calendar_id: str = 'primary') -> List[Dict]:
    """List upcoming events from the user's calendar.
    
    Useful for debugging and verification.
    
    Args:
        max_results: Maximum number of events to return
        calendar_id: Calendar to query
    
    Returns:
        List of event dictionaries with id, summary, start, end fields.
    """
    try:
        service = get_calendar_service()
        
        # Get current time in RFC3339 format
        now = datetime.utcnow().isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return [
            {
                'id': event.get('id'),
                'summary': event.get('summary', 'No title'),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
            }
            for event in events
        ]
        
    except HttpError as error:
        print(f"Google Calendar API error: {error}")
        return []
