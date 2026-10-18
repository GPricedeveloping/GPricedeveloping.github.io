"""Score rescue candidates and select the strongest matches with a heap."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from heapq import heappush, heapreplace
from math import isfinite
from typing import Any

from .rescue_service import get_rescue_query


DEFAULT_TOP_K = 5


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _has_valid_location(animal: Mapping[str, Any]) -> bool:
    latitude = _number(animal.get("location_lat"))
    longitude = _number(animal.get("location_long"))
    return (
        latitude is not None
        and longitude is not None
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def _score_with_query(
    animal: Mapping[str, Any], query: Mapping[str, Any]
) -> int:
    score = 0

    if _text(animal.get("animal_type")) == _text(query.get("animal_type")):
        score += 20

    breed_condition = query.get("breed", {})
    preferred_breeds = breed_condition.get("$in", [])
    if _text(animal.get("breed")) in {_text(breed) for breed in preferred_breeds}:
        score += 30

    if _text(animal.get("sex_upon_outcome")) == _text(
        query.get("sex_upon_outcome")
    ):
        score += 20

    age_condition = query.get("age_upon_outcome_in_weeks", {})
    age = _number(animal.get("age_upon_outcome_in_weeks"))
    minimum_age = _number(age_condition.get("$gte"))
    maximum_age = _number(age_condition.get("$lte"))
    if (
        age is not None
        and minimum_age is not None
        and maximum_age is not None
        and minimum_age <= age <= maximum_age
    ):
        score += 10
        midpoint = (minimum_age + maximum_age) / 2
        half_range = (maximum_age - minimum_age) / 2
        closeness = 1.0 if half_range == 0 else 1 - abs(age - midpoint) / half_range
        score += round(max(0.0, closeness) * 10)

    if _has_valid_location(animal):
        score += 10

    return score


def score_candidate(animal: Mapping[str, Any], rescue_type: str) -> int:
    """Return a suitability score from 0 to 100 for one animal."""
    query = get_rescue_query(rescue_type)
    if not query:
        return 0
    return _score_with_query(animal, query)


def rank_candidates(
    candidates: Iterable[Mapping[str, Any]],
    rescue_type: str,
    k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    """Return the best ``k`` candidates in descending score order.

    The min-heap never holds more than ``k`` entries, so selecting candidates
    takes O(n log k) time and O(k) extra space. The final k entries are sorted
    only so the dashboard can display them from highest to lowest score.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer")

    query = get_rescue_query(rescue_type)
    if not query:
        return []

    heap: list[tuple[int, int, dict[str, Any]]] = []
    for position, animal in enumerate(candidates):
        if not isinstance(animal, Mapping):
            raise TypeError("Each candidate must be a mapping")

        ranked_animal = dict(animal)
        score = _score_with_query(ranked_animal, query)
        ranked_animal["suitability_score"] = score

        # A negative position keeps the earlier record when scores are tied.
        entry = (score, -position, ranked_animal)
        if len(heap) < k:
            heappush(heap, entry)
        elif entry[:2] > heap[0][:2]:
            heapreplace(heap, entry)

    selected = sorted(heap, key=lambda entry: entry[:2], reverse=True)
    result: list[dict[str, Any]] = []
    for rank, (_, _, animal) in enumerate(selected, start=1):
        animal["rank"] = rank
        result.append(animal)
    return result
