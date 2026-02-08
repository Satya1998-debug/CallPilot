"""Provider search and filtering functionality.

This module provides tools for searching providers via Google Places/Maps.

Note: The MVP local JSON fallback is intentionally disabled.
"""

from __future__ import annotations

from typing import Any, Dict, List
from ..config import settings


# def load_providers() -> List[Dict[str, Any]]:
#     """Load all providers from the JSON database.
    
#     Reads the provider data file specified in settings.providers_path
#     and returns the complete list of providers.
    
#     Returns:
#         List of provider dictionaries, each containing:
#         - id: Unique provider identifier
#         - name: Provider/practice name
#         - specialty: Medical specialty
#         - distance_km: Distance from user in kilometers
#         - rating: User rating (0-5 scale)
#         - openings: Available appointment slots
#         - address: Location string
    
#     Example:
#         >>> providers = load_providers()
#         >>> print(providers[0]['name'])
#         'Mitte Dental'
#     """
#     with open(settings.providers_path, "r", encoding="utf-8") as f:
#         return json.load(f)


def search_providers(
    specialty: str,
    radius_km: float,
    user_location: str = "Berlin"
) -> List[Dict[str, Any]]:
    """Search for providers matching specialty and distance criteria.
    
    Uses Google Places API (no local fallback).
    
    Args:
        specialty: Medical specialty to search for (e.g., "dentist", "cardiology")
        radius_km: Maximum distance in kilometers from user location
        user_location: User's location (address or coordinates)
    
    Returns:
        List of matching providers sorted by distance (closest first).
        Empty list if no providers match the criteria.
    
    Example:
        >>> dentists = search_providers("dentist", 5.0, "Berlin, Germany")
        >>> print(f"Found {len(dentists)} dentists within 5km")
        Found 2 dentists within 5km
    """
    if not settings.use_google_apis:
        raise RuntimeError("Google provider search is disabled (set USE_GOOGLE_APIS=true)")

    try:
        from ..integrations.google_places import search_medical_providers
        from ..integrations.google_maps import calculate_distances_to_multiple

        # Search using Google Places API
        providers = search_medical_providers(
            specialty=specialty,
            location=user_location,
            radius_meters=int(radius_km * 1000),
            max_results=20,
        )

        if not providers:
            return []

        # Calculate distances
        destinations = [p.get("address") for p in providers if p.get("address")]
        distances = calculate_distances_to_multiple(user_location, destinations)

        # Enrich providers with distance info
        enriched: List[Dict[str, Any]] = []
        for provider, dist_info in zip(providers, distances):
            if not dist_info:
                continue
            provider["distance_km"] = dist_info.get("distance_km")
            provider["travel_time_min"] = dist_info.get("duration_minutes")
            provider["specialty"] = specialty
            provider["openings"] = []  # Google Places doesn't provide appointment slots
            enriched.append(provider)

        # Filter by radius and sort by distance
        enriched = [p for p in enriched if float(p.get("distance_km", 999)) <= radius_km]
        enriched.sort(key=lambda x: float(x.get("distance_km", 999)))
        return enriched
    except Exception as e:
        # No fallback: bubble up a clear error for the caller/tool layer.
        raise RuntimeError(f"Google provider search failed: {e}") from e

