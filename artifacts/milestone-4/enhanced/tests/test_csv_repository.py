from pathlib import Path

from data_access.csv_repository import CsvAnimalRepository


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "aac_shelter_outcomes.csv"


def test_read_all_records():
    repository = CsvAnimalRepository(DATA_FILE)
    records = repository.read({})
    assert len(records) > 1000
    assert "animal_type" in records[0]


def test_water_style_query_filters_records():
    repository = CsvAnimalRepository(DATA_FILE)
    records = repository.read(
        {
            "animal_type": "Dog",
            "breed": {"$in": ["Labrador Retriever", "Labrador Retriever Mix"]},
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome_in_weeks": {"$gte": 26, "$lte": 156},
        }
    )
    assert records
    assert all(record["animal_type"] == "Dog" for record in records)
    assert all(record["sex_upon_outcome"] == "Intact Female" for record in records)
