"""Validate animal records and the small set of supported search conditions.

Gordon Price | CS 499 Milestone Four | October 3, 2026 | Version 4
"""

from math import isfinite
from numbers import Real

from bson import ObjectId


TEXT_FIELDS = {
    "animal_id", "animal_type", "breed", "name", "sex_upon_outcome",
    "age_upon_outcome", "outcome_type", "outcome_subtype", "color",
    "date_of_birth", "datetime", "monthyear",
}
NUMBER_FIELDS = {"age_upon_outcome_in_weeks", "location_lat", "location_long"}
REQUIRED_FIELDS = {
    "animal_id", "animal_type", "breed", "sex_upon_outcome",
    "age_upon_outcome_in_weeks",
}
FIELDS = TEXT_FIELDS | NUMBER_FIELDS


def record_id(value):
    """An update or delete must identify one document, not a search filter."""
    if isinstance(value, ObjectId):
        return value
    if not isinstance(value, str) or not ObjectId.is_valid(value):
        raise ValueError("Record ID must be a 24-character MongoDB ObjectId.")
    return ObjectId(value)


def field_value(field, value, *, allow_none=False):
    if value is None and allow_none and field not in REQUIRED_FIELDS:
        return None
    if field in TEXT_FIELDS:
        if not isinstance(value, str) or len(value) > 500 or "\x00" in value:
            raise ValueError(f"{field} must be text of at most 500 characters.")
        value = value.strip()
        if field in REQUIRED_FIELDS and not value:
            raise ValueError(f"{field} cannot be blank.")
        return value
    if isinstance(value, int) and not -(2**63) <= value < 2**63:
        raise ValueError(f"{field} is too large to store as a MongoDB integer.")
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{field} must be a finite number.")
    if field == "age_upon_outcome_in_weeks" and value < 0:
        raise ValueError("Age in weeks cannot be negative.")
    if field == "location_lat" and not -90 <= value <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if field == "location_long" and not -180 <= value <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    return value


def validate_record(record, *, partial=False):
    if not isinstance(record, dict) or not record:
        raise ValueError("Supply a nonempty record object.")
    if any(field not in FIELDS for field in record):
        raise ValueError("The record contains an unsupported field.")
    if not partial and not REQUIRED_FIELDS.issubset(record):
        raise ValueError("Required fields: " + ", ".join(sorted(REQUIRED_FIELDS)))
    # Only flat, known fields are accepted; MongoDB operators can't be written.
    return {field: field_value(field, value, allow_none=True) for field, value in record.items()}


def validate_query(query=None):
    if query is None:
        return {}
    if not isinstance(query, dict):
        raise ValueError("Search must be an object.")
    clean = {}
    for field, condition in query.items():
        if field == "_id":
            clean[field] = record_id(condition)
        elif field not in FIELDS:
            raise ValueError("The search contains an unsupported field.")
        elif isinstance(condition, dict):
            if not condition:
                raise ValueError("A search condition cannot be empty.")
            operators = {}
            for operator, value in condition.items():
                if operator == "$in":
                    if not isinstance(value, list) or not 1 <= len(value) <= 100:
                        raise ValueError("$in requires between 1 and 100 values.")
                    operators[operator] = [field_value(field, item) for item in value]
                elif operator in {"$gte", "$lte"} and field in NUMBER_FIELDS:
                    operators[operator] = field_value(field, value)
                else:
                    raise ValueError("Unsupported search operator.")
            if "$gte" in operators and "$lte" in operators and operators["$gte"] > operators["$lte"]:
                raise ValueError("The lower bound cannot exceed the upper bound.")
            clean[field] = operators
        else:
            clean[field] = field_value(field, condition, allow_none=True)
    return clean
