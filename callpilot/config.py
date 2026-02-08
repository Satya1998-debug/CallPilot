"""Configuration management for CallPilot.

This module handles all configuration settings including file paths
and environment variables. Settings are loaded from .env file if present.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass(frozen=True)
class Settings:
    """Application settings and configuration.
    
    All settings are immutable (frozen=True) to prevent accidental modification.
    Values can be overridden via environment variables.
    
    Attributes:
        providers_path: Path to the JSON file containing provider data.
                       Can be set via PROVIDERS_PATH environment variable.
    """
    providers_path: str = os.getenv("PROVIDERS_PATH", "callpilot/data/providers.json")

# Global settings instance - import this in other modules
settings = Settings()
