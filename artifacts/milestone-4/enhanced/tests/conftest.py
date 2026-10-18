import pytest


@pytest.fixture
def animal():
    return {
        "animal_id": "M4-TEST",
        "name": "River",
        "animal_type": "Dog",
        "breed": "Labrador Retriever Mix",
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": 52,
        "age_upon_outcome": "1 year",
        "location_lat": 30.27,
        "location_long": -97.74,
    }
