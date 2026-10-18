from services.rescue_service import get_rescue_query


def test_reset_returns_empty_query():
    assert get_rescue_query("reset") == {}


def test_water_query_has_expected_constraints():
    query = get_rescue_query("water")
    assert query["animal_type"] == "Dog"
    assert query["sex_upon_outcome"] == "Intact Female"
    assert "Labrador Retriever" in query["breed"]["$in"]
    assert query["age_upon_outcome_in_weeks"] == {"$gte": 26, "$lte": 156}


def test_queries_are_returned_as_copies():
    first = get_rescue_query("mountain")
    first["animal_type"] = "Cat"
    second = get_rescue_query("mountain")
    assert second["animal_type"] == "Dog"


def test_invalid_filter_is_rejected():
    try:
        get_rescue_query("not-a-real-filter")
    except ValueError as exc:
        assert "Unknown rescue filter" in str(exc)
    else:
        raise AssertionError("Expected ValueError for an unknown filter")
