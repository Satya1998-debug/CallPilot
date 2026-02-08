#!/usr/bin/env python3
"""
Test script for Google API integrations.

This script tests the Google Calendar, Places, and Maps integrations
to verify they're working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


def test_calendar_api():
    """Test Google Calendar API integration."""
    print("\n" + "="*60)
    print("Testing Google Calendar API")
    print("="*60)
    
    try:
        from callpilot.integrations.google_calendar import (
            check_calendar_availability,
            create_calendar_event,
            list_upcoming_events
        )
        
        # List upcoming events
        print("\n1. Listing upcoming events...")
        events = list_upcoming_events(max_results=5)
        if events:
            print(f"   Found {len(events)} upcoming events:")
            for event in events:
                print(f"   - {event['summary']} ({event['start']})")
        else:
            print("   No upcoming events found")
        
        # Check availability
        print("\n2. Checking calendar availability...")
        is_free = check_calendar_availability(
            "2026-02-15T10:00:00Z",
            "2026-02-15T11:00:00Z"
        )
        print(f"   Slot 2026-02-15 10:00-11:00 is {'FREE' if is_free else 'BUSY'}")
        
        # Create test event
        print("\n3. Creating test event...")
        event_id = create_calendar_event(
            title="CallPilot Test Event",
            start_time="2026-02-20T14:00:00Z",
            end_time="2026-02-20T14:30:00Z",
            location="Test Location",
            description="Created by CallPilot test script"
        )
        print(f"   Created event with ID: {event_id}")
        
        print("\n✅ Google Calendar API: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Google Calendar API: FAILED")
        print(f"   Error: {e}")
        return False


def test_places_api():
    """Test Google Places API integration."""
    print("\n" + "="*60)
    print("Testing Google Places API")
    print("="*60)
    
    try:
        from callpilot.integrations.google_places import search_medical_providers
        
        print("\n1. Searching for dentists in Berlin...")
        providers = search_medical_providers(
            specialty="dentist",
            location="Berlin, Germany",
            radius_meters=5000,
            max_results=5
        )
        
        if providers:
            print(f"   Found {len(providers)} providers:")
            for i, provider in enumerate(providers, 1):
                print(f"   {i}. {provider['name']}")
                print(f"      Rating: {provider['rating']} ({provider['user_ratings_total']} reviews)")
                print(f"      Address: {provider['address']}")
                if provider.get('phone'):
                    print(f"      Phone: {provider['phone']}")
        else:
            print("   No providers found")
        
        print("\n✅ Google Places API: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Google Places API: FAILED")
        print(f"   Error: {e}")
        return False


def test_maps_api():
    """Test Google Maps Distance Matrix API integration."""
    print("\n" + "="*60)
    print("Testing Google Maps Distance Matrix API")
    print("="*60)
    
    try:
        from callpilot.integrations.google_maps import calculate_distance_and_time
        
        print("\n1. Calculating distance and time...")
        result = calculate_distance_and_time(
            origin="Berlin Hauptbahnhof",
            destination="Brandenburg Gate, Berlin",
            mode="driving"
        )
        
        if result:
            print(f"   Distance: {result['distance_km']:.2f} km ({result['distance_text']})")
            print(f"   Duration: {result['duration_minutes']} minutes ({result['duration_text']})")
            print(f"   Mode: {result['mode']}")
        else:
            print("   Could not calculate distance")
        
        print("\n✅ Google Maps API: PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Google Maps API: FAILED")
        print(f"   Error: {e}")
        return False


def main():
    """Run all API tests."""
    print("\n" + "="*60)
    print("CallPilot Google APIs Integration Test")
    print("="*60)
    
    results = {
        "Calendar API": test_calendar_api(),
        "Places API": test_places_api(),
        "Maps API": test_maps_api(),
    }
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for api, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{api}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 All tests PASSED! Google APIs are ready to use.")
    else:
        print("⚠️  Some tests FAILED. Check configuration and API keys.")
        print("   See GOOGLE_SETUP.md for setup instructions.")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
