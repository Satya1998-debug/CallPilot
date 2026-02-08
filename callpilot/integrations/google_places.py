"""Google Places API integration.

This module provides functions for searching medical providers
using the Google Places API.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

import googlemaps
from dotenv import load_dotenv

load_dotenv()


def get_places_client() -> googlemaps.Client:
    """Get authenticated Google Maps/Places client.
    
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


def search_medical_providers(
    specialty: str,
    location: str,
    radius_meters: int = 5000,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Search for medical providers using Google Places API.
    
    Args:
        specialty: Medical specialty to search for (e.g., "dentist", "cardiologist")
        location: User location as address or lat/lng string (e.g., "Berlin, Germany")
        radius_meters: Search radius in meters (default: 5000m = 5km)
        max_results: Maximum number of results to return
    
    Returns:
        List of provider dictionaries with:
        - id: Google Place ID
        - name: Provider/practice name
        - address: Formatted address
        - location: Dict with 'lat' and 'lng'
        - rating: Google rating (0-5)
        - user_ratings_total: Number of reviews
        - phone: Phone number (if available)
        - website: Website URL (if available)
        - opening_hours: Dict with opening hours (if available)
    
    Example:
        >>> providers = search_medical_providers(
        ...     "dentist",
        ...     "Berlin, Germany",
        ...     radius_meters=5000
        ... )
        >>> print(f"Found {len(providers)} dentists")
        Found 8 dentists
    """
    try:
        client = get_places_client()
        
        # Geocode the location to get coordinates
        geocode_result = client.geocode(location)
        if not geocode_result:
            print(f"Could not geocode location: {location}")
            return []
        
        lat_lng = geocode_result[0]['geometry']['location']
        
        # Search for providers
        # Note: "doctor" or specific types like "dentist" work well
        query = f"{specialty} near {location}"
        
        places_result = client.places_nearby(
            location=lat_lng,
            radius=radius_meters,
            keyword=specialty,
            type='health'  # Filter to health-related places
        )
        
        providers = []
        for place in places_result.get('results', [])[:max_results]:
            # Get detailed information
            place_id = place.get('place_id')
            details = client.place(place_id, fields=[
                'name', 'formatted_address', 'geometry',
                'rating', 'user_ratings_total',
                'formatted_phone_number', 'website',
                'opening_hours'
            ])
            
            result = details.get('result', {})
            
            provider = {
                'id': place_id,
                'name': result.get('name', 'Unknown'),
                'address': result.get('formatted_address', ''),
                'location': result.get('geometry', {}).get('location', {}),
                'rating': result.get('rating', 0.0),
                'user_ratings_total': result.get('user_ratings_total', 0),
                'phone': result.get('formatted_phone_number', ''),
                'website': result.get('website', ''),
                'opening_hours': result.get('opening_hours', {}),
            }
            providers.append(provider)
        
        return providers
        
    except ValueError as e:
        print(f"Google Places API configuration error: {e}")
        return []
    except Exception as e:
        print(f"Google Places API error: {e}")
        return []


def get_provider_details(place_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific provider.
    
    Args:
        place_id: Google Place ID
    
    Returns:
        Provider details dictionary or None if not found.
    """
    try:
        client = get_places_client()
        
        details = client.place(place_id, fields=[
            'name', 'formatted_address', 'geometry',
            'rating', 'user_ratings_total',
            'formatted_phone_number', 'website',
            'opening_hours', 'reviews'
        ])
        
        result = details.get('result', {})
        if not result:
            return None
        
        return {
            'id': place_id,
            'name': result.get('name', 'Unknown'),
            'address': result.get('formatted_address', ''),
            'location': result.get('geometry', {}).get('location', {}),
            'rating': result.get('rating', 0.0),
            'user_ratings_total': result.get('user_ratings_total', 0),
            'phone': result.get('formatted_phone_number', ''),
            'website': result.get('website', ''),
            'opening_hours': result.get('opening_hours', {}),
            'reviews': result.get('reviews', [])[:5],  # Top 5 reviews
        }
        
    except Exception as e:
        print(f"Error fetching provider details: {e}")
        return None


def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """Convert an address to latitude/longitude coordinates.
    
    Args:
        address: Address string
    
    Returns:
        Dict with 'lat' and 'lng' keys, or None if geocoding fails.
    """
    try:
        client = get_places_client()
        result = client.geocode(address)
        
        if result:
            return result[0]['geometry']['location']
        return None
        
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None
