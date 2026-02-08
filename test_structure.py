"""
Quick test to verify CallPilot structure and imports
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing CallPilot imports...\n")

# Test main package
try:
    from callpilot import Config, AppointmentState, build_graph, run_agent
    print("✓ Main package imports successful")
except ImportError as e:
    print(f"✗ Main package import failed: {e}")
    sys.exit(1)

# Test tools
try:
    from callpilot.tools import load_providers, parse_date, calculate_match_score
    print("✓ Tools imports successful")
except ImportError as e:
    print(f"✗ Tools import failed: {e}")
    sys.exit(1)

# Test adapters
try:
    from callpilot.adapters import ReceptionistSimulator, simulate_provider_call
    print("✓ Adapters imports successful")
except ImportError as e:
    print(f"✗ Adapters import failed: {e}")
    sys.exit(1)

# Test loading providers
try:
    providers = load_providers()
    print(f"✓ Loaded {len(providers)} providers from data file")
except Exception as e:
    print(f"✗ Failed to load providers: {e}")
    sys.exit(1)

# Test config
try:
    config = Config()
    has_keys = bool(config.elevenlabs_api_key and config.openai_api_key)
    print(f"✓ Config initialized (API keys: {'set' if has_keys else 'not set - add to .env'})")
except Exception as e:
    print(f"✗ Config failed: {e}")
    sys.exit(1)

print("\n🎉 All imports and basic tests passed!")
print("\nTo run the agent:")
print("  python -m src.callpilot.run")
print("\nOr:")
print("  cd src && python -m callpilot.run")
