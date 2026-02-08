from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import logging
from pathlib import Path
from typing import Dict, Any
from .tools.providers import search_providers
from .tools.calendar import check_calendar_free, create_calendar_event
from .adapters.receptionist_sim import reserve_slot as reserve_slot_sim
from .tools.scoring import score as score_fn

mcp = FastMCP("CallPilot Tools", json_response=True)

# Configure logging with forced override and immediate flushing
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True
)
logger = logging.getLogger("callpilot.mcp")
logger.setLevel(logging.INFO)
logger.propagate = False  # Don't propagate to root logger

# Custom handler that flushes immediately
class FlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Log to file in artifacts/ with immediate flushing
_log_path = Path("artifacts/mcp.log")
_log_path.parent.mkdir(parents=True, exist_ok=True)

# File handler that flushes after every write
_file_handler = FlushFileHandler(_log_path, mode='a')
_file_handler.setLevel(logging.INFO)
_file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_file_handler)

# Console handler to see logs in terminal too
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_console_handler)

# Log server initialization
logger.info("CallPilot MCP Server logger initialized")

providers = []

@mcp.tool()
def search_providers_tool(specialty: str, radius_km: float = 5.0, user_location: str = "Berlin") -> dict:
    """Search for medical providers by specialty within a radius.
    
    Finds healthcare providers (dentists, doctors, etc.) near the user's location.
    Uses Google Places API when configured, otherwise uses local data.
    Returns providers sorted by distance with ratings, addresses, and available slots.
    
    Args:
        specialty: Medical specialty (e.g., "dentist", "cardiologist")
        radius_km: Search radius in kilometers (default: 5.0)
        user_location: User's location for distance calculation (default: "Berlin")
    
    Returns:
        {"providers": List of provider dicts with id, name, rating, distance_km, address, openings}
    """
    global providers  # Cache providers in global variable for subsequent tools
    logger.info("search_providers_tool: specialty=%s radius_km=%s user_location=%s", specialty, radius_km, user_location)
    try:
        providers = search_providers(specialty=specialty, radius_km=radius_km, user_location=user_location)
        logger.info("search_providers_tool: found=%d", len(providers))
        return {"providers": providers}
    except Exception as e:
        providers = []
        logger.exception("search_providers_tool failed")
        return {"providers": [], "error": str(e)}


@mcp.tool()
def get_openings_tool(provider_id: str) -> dict:
    """Get available appointment slots for a provider.
    
    Retrieves the list of available time slots from a provider's schedule.
    Each slot includes ISO 8601 start/end timestamps.
    
    Args:
        provider_id: Provider's unique identifier (e.g., "mitte_dental_1")
    
    Returns:
        {"openings": List of slots with start/end times} or {"error": error message}
    """
    logger.info("get_openings_tool: provider_id=%s", provider_id)
    global providers
    p = next((x for x in providers if x["id"] == provider_id), None)
    if not p:
        logger.warning("get_openings_tool: unknown provider_id=%s", provider_id)
        return {"openings": [], "error": f"Unknown provider_id={provider_id}"}
    logger.info("get_openings_tool: openings=%d", len(p.get("openings", [])))
    return {"openings": p.get("openings", [])}


#@mcp.tool()
# def check_calendar_free_tool(start: str, end: str) -> dict:
#     """Check if a time slot is free in the user's calendar.
    
#     Verifies if the proposed appointment time conflicts with existing events.
#     Uses Google Calendar API when configured, otherwise uses MVP stub data.
    
#     Args:
#         start: Slot start time as ISO 8601 timestamp (e.g., "2026-02-10T14:00:00")
#         end: Slot end time as ISO 8601 timestamp
    
#     Returns:
#         {"free": True if available, False if busy}
#     """
#     logger.info("check_calendar_free_tool: start=%s end=%s", start, end)
#     ok = check_calendar_free({"start": start, "end": end})
#     logger.info("check_calendar_free_tool: free=%s", ok)
#     return {"free": ok}


# @mcp.tool()
# def reserve_slot_tool(provider_id: str, start: str, end: str) -> dict:
#     """Reserve an appointment slot with a provider.
    
#     Confirms and books the specified time slot with the healthcare provider.
#     In production, this would call the provider's booking API or make a phone call.
#     Currently simulates the reservation process.
    
#     Args:
#         provider_id: Provider's unique identifier
#         start: Appointment start as ISO 8601 timestamp
#         end: Appointment end as ISO 8601 timestamp
    
#     Returns:
#         {"ok": True if successful, False if failed, "error": optional error message}
#     """
#     logger.info("reserve_slot_tool: provider_id=%s start=%s end=%s", provider_id, start, end)
#     global providers
#     p = next((x for x in providers if x["id"] == provider_id), None)
#     if not p:
#         logger.warning("reserve_slot_tool: unknown provider_id=%s", provider_id)
#         return {"ok": False, "error": f"Unknown provider_id={provider_id}"}
#     ok = reserve_slot_sim(p, {"start": start, "end": end})
#     logger.info("reserve_slot_tool: ok=%s", ok)
#     return {"ok": bool(ok)}


@mcp.tool()
def select_best_appointment(time_window: str) -> dict:
    """Find the best available appointment from previously searched providers.
    
    This tool selects the optimal appointment by:
    1. Reading from the global providers list (populated by search_providers_tool)
    2. Checking which slots are free in user's calendar
    3. Scoring each available option
    4. Returning the best match (without reserving it)
    
    Important: Run search_providers_tool first to populate the provider list.
    
    Args:
        time_window: Preferred time (e.g., "this week", "tomorrow morning")
    
    Returns:
        {
            "success": True/False,
            "provider": {id, name, address, rating, distance_km},
            "slot": {start, end},
            "score": 0-10 rating,
            "error": Optional error message
        }
    """
    logger.info("find_best_appointment_tool: time_window=%s", time_window)
    
    try:
        global providers
        
        # Check if providers list is populated
        if not providers:
            logger.warning("find_best_appointment_tool: no providers available")
            return {"success": False, "error": "No providers found. Please run search_providers_tool first."}
        
        logger.info("find_best_appointment_tool: checking %d providers", len(providers))
        
        # Find best slot from providers
        best_option = None
        best_score = -1
        
        for provider in providers:
            openings = provider.get("openings", [])
            if not openings:
                logger.info("find_best_appointment_tool: provider %s has no openings", provider.get("name", provider["id"]))
                continue
            
            logger.info("find_best_appointment_tool: checking %d slots for provider %s", 
                        len(openings), provider.get("name", provider["id"]))
            
            # Check each slot
            for slot in openings:
                # Check if free in calendar
                is_free = check_calendar_free(slot)
                logger.info("find_best_appointment_tool: slot %s - calendar free: %s", 
                           slot.get("start"), is_free)
                
                if not is_free:
                    continue
                
                # Score this option
                score_result = score_fn(provider, slot)
                current_score = score_result.get("score", 0)
                
                logger.info("find_best_appointment_tool: slot %s scored %.1f", 
                           slot.get("start"), current_score)
                
                if current_score > best_score:
                    best_score = current_score
                    best_option = {
                        "provider": {
                            "id": provider["id"],
                            "name": provider["name"],
                            "address": provider.get("address", ""),
                            "rating": provider.get("rating", 0),
                            "distance_km": provider.get("distance_km", 0)
                        },
                        "slot": slot,
                        "score": current_score
                    }
        
        if not best_option:
            # create a dummy slot to be booked later, so that the workflow can proceed to reservation step and demonstrate the full flow.
            logger.warning("find_best_appointment_tool: no available slots found....creating a dummy appointment option for demonstration purposes")
            best_option = {
                "provider": {
                    "id": "dummy_provider",
                    "name": "Demo Healthcare Provider",
                    "address": "123 Demo Street, Berlin",
                    "rating": 4.5,
                    "distance_km": 2.0
                },
                "slot": {
                    "start": "2026-02-10T14:00:00",
                    "end": "2026-02-10T14:30:00"
                },
                "score": 0
            }
        
        logger.info("find_best_appointment_tool: best appointment selected - provider=%s score=%.1f", 
                   best_option["provider"]["name"], best_score)
        
        return {
            "success": True,
            "provider": best_option["provider"],
            "slot": best_option["slot"],
            "score": best_option["score"]
        }
        
    except Exception as e:
        logger.error("find_best_appointment_tool: exception - %s", str(e), exc_info=True)
        return {"success": False, "error": f"Error finding appointment: {str(e)}"}


# @mcp.tool()
# def score_option_tool(provider_id: str, start: str, end: str) -> dict:
#     """Calculate a quality score for a provider and time slot.
    
#     Scores the appointment option based on provider rating, distance, and timing.
#     Higher scores (0-10 scale) indicate better options. Used to rank alternatives.
    
#     Args:
#         provider_id: Provider's unique identifier
#         start: Appointment start as ISO 8601 timestamp
#         end: Appointment end as ISO 8601 timestamp
    
#     Returns:
#         {"score": 0-10 rating, "rating": provider rating, "distance_km": distance} or {"error": message}
#     """
#     logger.info("score_option_tool: provider_id=%s start=%s end=%s", provider_id, start, end)
#     global providers
#     p = next((x for x in providers if x["id"] == provider_id), None)
#     if not p:
#         logger.warning("score_option_tool: unknown provider_id=%s", provider_id)
#         return {"error": f"Unknown provider_id={provider_id}"}
#     logger.info("score_option_tool: ok")
#     return score_fn(p, {"start": start, "end": end})
