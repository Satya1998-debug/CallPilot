"""Provider search and filtering functionality.

This module provides tools for loading provider data and performing
search/filter operations based on specialty, distance, and other criteria.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List
from ..config import settings

def load_providers() -> List[Dict[str, Any]]:
    """Load all providers from the JSON database.
    
    Reads the provider data file specified in settings.providers_path
    and returns the complete list of providers.
    
    Returns:
        List of provider dictionaries, each containing:
        - id: Unique provider identifier
        - name: Provider/practice name
        - specialty: Medical specialty
        - distance_km: Distance from user in kilometers
        - rating: User rating (0-5 scale)
        - openings: Available appointment slots
        - address: Location string
    
    Example:
        >>> providers = load_providers()
        >>> print(providers[0]['name'])
        'Mitte Dental'
    """
    with open(settings.providers_path, "r", encoding="utf-8") as f:
        return json.load(f)

def search_providers(specialty: str, radius_km: float) -> List[Dict[str, Any]]:
    """Search for providers matching specialty and distance criteria.
    
    Filters the provider database to find matches within the specified
    distance radius that offer the requested medical specialty.
    
    Args:
        specialty: Medical specialty to search for (e.g., "dentist", "cardiology")
        radius_km: Maximum distance in kilometers from user location
    
    Returns:
        List of matching providers sorted by distance (closest first).
        Empty list if no providers match the criteria.
    
    Example:
        >>> dentists = search_providers("dentist", 5.0)
        >>> print(f"Found {len(dentists)} dentists within 5km")
        Found 2 dentists within 5km
    """
    providers = load_providers()
    
    # Filter by specialty match and distance constraint
    return [
        p for p in providers
        if p.get("specialty") == specialty and float(p.get("distance_km", 999)) <= radius_km
    ]
