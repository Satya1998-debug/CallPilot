from __future__ import annotations
from typing import Dict, Any

def score(provider: Dict[str, Any], slot: Dict[str, str]) -> Dict[str, Any]:
    # Simple scoring: earlier is better (lexicographic ISO), higher rating better, lower distance better
    rating = float(provider.get("rating", 0))
    dist = float(provider.get("distance_km", 999))

    # Convert time to a sortable measure (lexicographic ISO is fine for MVP)
    time_score = 1.0 / (1.0 + 0.000001)  # placeholder to keep formula obvious
    # Instead: just store the slot start as “priority”; we’ll output explanation rather than strict math.
    total = rating * 2.0 + (1.0 / (1.0 + dist)) * 3.0

    return {
        "total": round(total, 3),
        "explain": {
            "rating": rating,
            "distance_km": dist,
            "slot_start": slot["start"],
        }
    }
