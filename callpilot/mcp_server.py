from __future__ import annotations

from mcp.server.fastmcp import FastMCP

import logging
from pathlib import Path
from .tools.providers import search_providers, load_providers
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


@mcp.tool()
def search_providers_tool(specialty: str, radius_km: float = 5.0) -> dict:
    """Return providers matching specialty within radius_km."""
    logger.info("search_providers_tool: specialty=%s radius_km=%s", specialty, radius_km)
    providers = search_providers(specialty=specialty, radius_km=radius_km)
    logger.info("search_providers_tool: found=%d", len(providers))
    return {"providers": providers}


@mcp.tool()
def get_openings_tool(provider_id: str) -> dict:
    """Return openings list for a provider."""
    logger.info("get_openings_tool: provider_id=%s", provider_id)
    providers = load_providers()
    p = next((x for x in providers if x["id"] == provider_id), None)
    if not p:
        logger.warning("get_openings_tool: unknown provider_id=%s", provider_id)
        return {"openings": [], "error": f"Unknown provider_id={provider_id}"}
    logger.info("get_openings_tool: openings=%d", len(p.get("openings", [])))
    return {"openings": p.get("openings", [])}


@mcp.tool()
def check_calendar_free_tool(start: str, end: str) -> dict:
    """Check if slot is free in user's calendar (MVP stub)."""
    logger.info("check_calendar_free_tool: start=%s end=%s", start, end)
    ok = check_calendar_free({"start": start, "end": end})
    logger.info("check_calendar_free_tool: free=%s", ok)
    return {"free": ok}


@mcp.tool()
def reserve_slot_tool(provider_id: str, start: str, end: str) -> dict:
    """Reserve a slot with a provider (MVP sim)."""
    logger.info("reserve_slot_tool: provider_id=%s start=%s end=%s", provider_id, start, end)
    providers = load_providers()
    p = next((x for x in providers if x["id"] == provider_id), None)
    if not p:
        logger.warning("reserve_slot_tool: unknown provider_id=%s", provider_id)
        return {"ok": False, "error": f"Unknown provider_id={provider_id}"}
    ok = reserve_slot_sim(p, {"start": start, "end": end})
    logger.info("reserve_slot_tool: ok=%s", ok)
    return {"ok": bool(ok)}


@mcp.tool()
def create_calendar_event_tool(title: str, start: str, end: str, location: str = "") -> dict:
    """Create calendar event (MVP stub)."""
    logger.info("create_calendar_event_tool: title=%s start=%s end=%s", title, start, end)
    event_id = create_calendar_event(title=title, slot={"start": start, "end": end}, location=location)
    logger.info("create_calendar_event_tool: event_id=%s", event_id)
    return {"event_id": event_id}


@mcp.tool()
def score_option_tool(provider_id: str, start: str, end: str) -> dict:
    """Score a provider+slot option."""
    logger.info("score_option_tool: provider_id=%s start=%s end=%s", provider_id, start, end)
    providers = load_providers()
    p = next((x for x in providers if x["id"] == provider_id), None)
    if not p:
        logger.warning("score_option_tool: unknown provider_id=%s", provider_id)
        return {"error": f"Unknown provider_id={provider_id}"}
    logger.info("score_option_tool: ok")
    return score_fn(p, {"start": start, "end": end})
