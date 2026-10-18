"Rescue-filter rules separated from the Dash callback layer."

from __future__ import annotations

from copy import deepcopy
from typing import Any


RESCUE_QUERIES: dict[str, dict[str, Any]] = {
    "reset": {},
    "water": {
        "animal_type": "Dog",
        "breed": {
            "$in": [
                "Labrador Retriever",
                "Chesapeake Bay Retriever",
                "Newfoundland",
                "Labrador Retriever Mix",
            ]
        },
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    },
    "mountain": {
        "animal_type": "Dog",
        "breed": {
            "$in": [
                "German Shepherd",
                "Alaskan Malamute",
                "Old English Sheepdog",
                "Siberian Husky",
                "Rottweiler",
            ]
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
    },
    "disaster": {
        "animal_type": "Dog",
        "breed": {
            "$in": [
                "Doberman Pinscher",
                "German Shepherd",
                "Golden Retriever",
                "Bloodhound",
                "Rottweiler",
            ]
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 20, "$lte": 300},
    },
}


def get_rescue_query(filter_type: str | None) -> dict[str, Any]:
    """Return a copy of the query for a known rescue filter."""
    key = (filter_type or "reset").strip().lower()
    if key not in RESCUE_QUERIES:
        raise ValueError(f"Unknown rescue filter: {filter_type!r}")
    return deepcopy(RESCUE_QUERIES[key])
