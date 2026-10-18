from copy import deepcopy

from bson import ObjectId
import pytest

from data_access.validation import record_id, validate_record, validate_query
from services.rescue_service import get_rescue_query


def test_record_is_cleaned_without_changing_input(animal):
    animal["name"] = "  River  "
    original = deepcopy(animal)
    assert validate_record(animal)["name"] == "River"
    assert animal == original


@pytest.mark.parametrize("field,value", [
    ("animal_id", "  "), ("breed", {"$ne": None}),
    ("age_upon_outcome_in_weeks", -1), ("age_upon_outcome_in_weeks", True),
    ("age_upon_outcome_in_weeks", float("nan")), ("age_upon_outcome_in_weeks", float("inf")),
    ("age_upon_outcome_in_weeks", 10**400),
    ("age_upon_outcome_in_weeks", "52"), ("location_lat", 91), ("location_long", -181),
    ("name", "x" * 501), ("$set", {}), ("name.first", "River"), ("_id", ObjectId()),
])
def test_invalid_record_fields_are_rejected(animal, field, value):
    animal[field] = value
    with pytest.raises(ValueError):
        validate_record(animal)


def test_create_requires_fields_but_update_accepts_one_field():
    with pytest.raises(ValueError):
        validate_record({"name": "River"})
    assert validate_record({"name": "River"}, partial=True) == {"name": "River"}
    assert validate_record({"location_lat": None}, partial=True) == {"location_lat": None}
    with pytest.raises(ValueError):
        validate_record({}, partial=True)


@pytest.mark.parametrize("query", [
    [], "Dog", {"$where": "return true"}, {"name": {"$regex": ".*"}},
    {"breed": {"$in": [{"$ne": None}]}}, {"breed": {"$in": []}},
    {"name": {}}, {"age_upon_outcome_in_weeks": {"$gte": 100, "$lte": 10}},
    {"_id": {}}, {"secret": "value"},
])
def test_unsafe_or_invalid_queries_are_rejected(query):
    with pytest.raises(ValueError):
        validate_query(query)


@pytest.mark.parametrize("rescue", ["reset", "water", "mountain", "disaster"])
def test_existing_rescue_queries_still_work(rescue):
    query = get_rescue_query(rescue)
    assert validate_query(query) == query


def test_object_id_validation():
    identifier = ObjectId()
    assert record_id(str(identifier)) == identifier
    for invalid in (None, "", "M4-TEST", {}, True):
        with pytest.raises(ValueError):
            record_id(invalid)
