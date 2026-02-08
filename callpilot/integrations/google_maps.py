"""Google Maps Distance Matrix API integration.

This module provides functions for calculating travel times and distances
between locations using the Google Maps Distance Matrix API.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional, Tuple

import googlemaps
from dotenv import load_dotenv

load_dotenv()


def get_maps_client() -> googlemaps.Client:
    """Get authenticated Google Maps client.
    
    Returns:
        Authenticated googlemaps.Client instance.
        
    Raises:
        ValueError: If GOOGLE_MAPS_API_KEY is not set.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing GOOGLE_MAPS_API_KEY environment variable.\n"
            "Get your API key from: https://console.cloud.google.com/google/maps-apis"
        )
    return googlemaps.Client(key=api_key)


def calculate_distance_and_time(
    origin: str,
    destination: str,
    mode: str = "driving",
    departure_time: str = "now"
) -> Optional[Dict[str, Any]]:
    """Calculate distance and travel time between two locations.
    
    Args:
        origin: Starting location (address or lat/lng string)
        destination: Destination location (address or lat/lng string)
        mode: Travel mode - "driving", "walking", "bicycling", or "transit"
        departure_time: When to depart - "now" or Unix timestamp
    
    Returns:
        Dictionary with:
        - distance_meters: Distance in meters
        - distance_km: Distance in kilometers
        - distance_text: Human-readable distance (e.g., "5.2 km")
        - duration_seconds: Travel time in seconds
        - duration_minutes: Travel time in minutes
        - duration_text: Human-readable duration (e.g., "12 mins")
        - mode: Travel mode used
        
        Returns None if calculation fails.
    
    Example:
        >>> result = calculate_distance_and_time(
        ...     "Berlin Hauptbahnhof",
        ...     "Brandenburg Gate, Berlin"
        ... )
        >>> print(f"Distance: {result['distance_km']:.1f} km")
        >>> print(f"Time: {result['duration_minutes']} minutes")
        Distance: 2.3 km
        Time: 8 minutes
    """
    try:
        client = get_maps_client()
        
        # Call Distance Matrix API
        result = client.distance_matrix(
            origins=[origin],
            destinations=[destination],
            mode=mode,
            departure_time=departure_time
        )
        
        # Extract result
        if result['status'] != 'OK':
            print(f"Distance Matrix API returned status: {result['status']}")
            return None
        
        element = result['rows'][0]['elements'][0]
        
        if element['status'] != 'OK':
            print(f"Route calculation failed: {element['status']}")
            return None
        
        distance = element['distance']
        duration = element['duration']
        
        return {
            'distance_meters': distance['value'],
            'distance_km': distance['value'] / 1000,
            'distance_text': distance['text'],
            'duration_seconds': duration['value'],
            'duration_minutes': round(duration['value'] / 60),
            'duration_text': duration['text'],
            'mode': mode,
        }
        
    except ValueError as e:
        print(f"Google Maps API configuration error: {e}")
        return None
    except Exception as e:
        print(f"Google Maps API error: {e}")
        return None


def calculate_distances_to_multiple(
    origin: str,
    destinations: List[str],
    mode: str = "driving"
) -> List[Optional[Dict[str, Any]]]:
    """Calculate distances and times from one origin to multiple destinations.
    
    Useful for comparing multiple providers at once.
    
    Args:
        origin: Starting location
        destinations: List of destination locations
        mode: Travel mode
    
    Returns:
        List of distance/time dictionaries (same format as calculate_distance_and_time).
        List length matches destinations length. None entries indicate failed calculations.
    
    Example:
        >>> providers = ["Provider A Address", "Provider B Address", "Provider C Address"]
        >>> results = calculate_distances_to_multiple("My Address", providers)
        >>> for i, result in enumerate(results):
        ...     if result:
        ...         print(f"Provider {i+1}: {result['distance_km']:.1f} km")
        Provider 1: 2.5 km
        Provider 2: 5.1 km
        Provider 3: 3.8 km
    """
    try:
        client = get_maps_client()
        
        # Call Distance Matrix API with multiple destinations
        result = client.distance_matrix(
            origins=[origin],
            destinations=destinations,
            mode=mode
        )
        
        if result['status'] != 'OK':
            print(f"Distance Matrix API returned status: {result['status']}")
            return [None] * len(destinations)
        
        # Extract results for each destination
        results = []
        elements = result['rows'][0]['elements']
        
        for element in elements:
            if element['status'] != 'OK':
                results.append(None)
                continue
            
            distance = element['distance']
            duration = element['duration']
            
            results.append({
                'distance_meters': distance['value'],
                'distance_km': distance['value'] / 1000,
                'distance_text': distance['text'],
                'duration_seconds': duration['value'],
                'duration_minutes': round(duration['value'] / 60),
                'duration_text': duration['text'],
                'mode': mode,
            })
        
        return results
        
    except ValueError as e:
        print(f"Google Maps API configuration error: {e}")
        return [None] * len(destinations)
    except Exception as e:
        print(f"Google Maps API error: {e}")
        return [None] * len(destinations)


def get_travel_time_with_traffic(
    origin: str,
    destination: str,
    departure_time: int = None
) -> Optional[int]:
    """Get travel time accounting for traffic conditions.
    
    Args:
        origin: Starting location
        destination: Destination location
        departure_time: Unix timestamp for departure (None = now)
    
    Returns:
        Travel time in minutes, or None if calculation fails.
    """
    result = calculate_distance_and_time(
        origin,
        destination,
        mode="driving",
        departure_time="now" if departure_time is None else departure_time
    )
    
    if result:
        return result['duration_minutes']
    return None


def filter_by_distance(
    providers: List[Dict[str, Any]],
    user_location: str,
    max_distance_km: float = 10.0
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Filter providers by distance and enrich with travel information.
    
    Args:
        providers: List of provider dictionaries (must have 'address' field)
        user_location: User's location
        max_distance_km: Maximum acceptable distance in kilometers
    
    Returns:
        List of tuples: (provider_dict, distance_info_dict)
        Sorted by distance (closest first).
        Only includes providers within max_distance_km.
    
    Example:
        >>> providers = [{"name": "Provider A", "address": "123 Main St"}]
        >>> filtered = filter_by_distance(providers, "My Location", 5.0)
        >>> for provider, distance_info in filtered:
        ...     print(f"{provider['name']}: {distance_info['distance_km']:.1f} km")
        Provider A: 3.2 km
    """
    destinations = [p.get('address', '') for p in providers]
    distance_results = calculate_distances_to_multiple(user_location, destinations)
    
    # Pair providers with their distance info
    paired = []
    for provider, dist_info in zip(providers, distance_results):
        if dist_info and dist_info['distance_km'] <= max_distance_km:
            paired.append((provider, dist_info))
    
    # Sort by distance
    paired.sort(key=lambda x: x[1]['distance_km'])
    
    return paired
