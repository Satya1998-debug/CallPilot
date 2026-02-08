"""
CallPilot - AI-powered healthcare appointment scheduling agent
"""

__version__ = "0.1.0"

from .config import Settings, settings
from .state import CallState

__all__ = ["Settings", "settings", "CallState"]
