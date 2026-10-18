"""Set MONGO_TEST_URI to run these against a dedicated MongoDB test server."""

import os
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from pymongo import MongoClient
import pytest

from app import create_app
from config import Settings
from data_access.mongo_repository import MongoAnimalRepository
from manage_records import main
from services import get_rescue_query, rank_candidates


@pytest.fixture
def live_repository():
    uri = os.getenv("MONGO_TEST_URI")
    if not uri:
        pytest.skip("Set MONGO_TEST_URI to run live MongoDB tests.")
    database = "cs499_m4_test_" + uuid4().hex
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    repository = MongoAnimalRepository(uri, database, "animals", allow_writes=True)
    try:
        yield repository, client[database]["animals"]
    finally:
        repository.close()
        # Only the unique database created by this test is removed.
        assert database.startswith("cs499_m4_test_") and len(database) == 46
        client.drop_database(database)
        client.close()


def test_live_crud_keeps_other_outcomes_for_same_animal(live_repository, animal):
    repository, collection = live_repository
    first = repository.create(animal)
    second = repository.create({**animal, "name": "Second outcome"})
    repository.ensure_indexes()
    assert len(repository.read({"animal_id": animal["animal_id"]})) == 2
    assert repository.update(first, {"name": "Updated"})
    assert repository.read({"_id": first})[0]["name"] == "Updated"
    assert repository.read({"_id": second})[0]["name"] == "Second outcome"
    with pytest.raises(ValueError):
        repository.delete(first)
    assert collection.count_documents({}) == 2
    assert repository.delete(first, confirmed=True)
    assert repository.read({"_id": first}) == []
    assert len(repository.read({"_id": second})) == 1


def test_live_invalid_write_does_not_change_record(live_repository, animal):
    repository, _ = live_repository
    identifier = repository.create(animal)
    with pytest.raises(ValueError):
        repository.update(identifier, {"location_lat": 100})
    assert repository.read({"_id": identifier})[0]["location_lat"] == animal["location_lat"]
    assert repository.update(ObjectId(), {"name": "Missing"}) is False
    assert repository.delete(ObjectId(), confirmed=True) is False


def test_live_indexes_are_repeatable_and_do_not_change_tie_order(live_repository, animal):
    repository, collection = live_repository
    for index in range(8):
        repository.create({**animal, "name": str(index)})
    query = get_rescue_query("water")
    before = rank_candidates(repository.read(query), "water")
    repository.ensure_indexes()
    repository.ensure_indexes()
    after = rank_candidates(repository.read(query), "water")
    assert [record["_id"] for record in before] == [record["_id"] for record in after]
    indexes = collection.index_information()
    assert set(indexes) == {"_id_", "animal_id_lookup", "rescue_lookup"}
    assert not indexes["animal_id_lookup"].get("unique", False)


def test_live_command_tool_create_update_read_and_confirmed_delete(live_repository, monkeypatch, capsys):
    repository, collection = live_repository
    monkeypatch.setenv("DATA_SOURCE", "mongo")
    monkeypatch.setenv("MONGO_URI", os.environ["MONGO_TEST_URI"])
    monkeypatch.setenv("MONGO_DATABASE", collection.database.name)
    monkeypatch.setenv("MONGO_COLLECTION", "animals")
    examples = Path(__file__).resolve().parents[1] / "examples"
    assert main(["--allow-writes", "create", str(examples / "new_animal.json")]) == 0
    identifier = str(repository.read({})[0]["_id"])
    assert main(["--allow-writes", "update", identifier, str(examples / "update_animal.json")]) == 0
    assert main(["read", "--record-id", identifier]) == 0
    assert "River Updated" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda prompt: "cancel")
    assert main(["--allow-writes", "delete", identifier]) == 0
    assert len(repository.read({})) == 1
    monkeypatch.setattr("builtins.input", lambda prompt: "DELETE " + identifier)
    assert main(["--allow-writes", "delete", identifier]) == 0
    assert repository.read({}) == []


@pytest.fixture
def live_dashboard(live_repository, animal):
    repository, _ = live_repository
    for record in (
        animal,
        {**animal, "breed": "German Shepherd", "sex_upon_outcome": "Intact Male"},
        {**animal, "animal_type": "Cat", "breed": "Domestic Shorthair"},
    ):
        repository.create(record)
    repository.ensure_indexes()
    settings = Settings("mongo", Path("unused.csv"), "unused", "unused", "animals", "127.0.0.1", 8054, False)
    return create_app(settings, repository)


@pytest.mark.parametrize("rescue,count", [("reset", 3), ("water", 1), ("mountain", 1), ("disaster", 1)])
def test_live_dashboard_filters_rankings_chart_and_map(live_dashboard, rescue, count):
    client = live_dashboard.server.test_client()
    assert client.get("/").status_code == 200
    key = next(key for key in live_dashboard.callback_map if "datatable-id.data" in key)
    callback = live_dashboard.callback_map[key]
    response = client.post("/_dash-update-component", json={
        "output": key,
        "outputs": [{"id": output.component_id, "property": output.component_property} for output in callback["output"]],
        "inputs": [{"id": "filter-type", "property": "value", "value": rescue}],
        "state": [], "changedPropIds": ["filter-type.value"],
    })
    assert response.status_code == 200
    body = response.get_json()["response"]
    rows = body["datatable-id"]["data"]
    assert len(rows) == count
    assert body["error-message"]["children"] == ""
    assert len(body["ranked-candidates-id"]["data"]) == (0 if rescue == "reset" else count)
    for output, inputs, expected_type in (
        ("graph-id", [{"id": "datatable-id", "property": "derived_virtual_data", "value": rows}], "Graph"),
        ("map-id", [
            {"id": "datatable-id", "property": "derived_virtual_data", "value": rows},
            {"id": "datatable-id", "property": "derived_virtual_selected_rows", "value": [0]},
        ], "MapContainer"),
    ):
        response = client.post("/_dash-update-component", json={
            "output": output + ".children", "outputs": {"id": output, "property": "children"},
            "inputs": inputs, "state": [], "changedPropIds": ["datatable-id.derived_virtual_data"],
        })
        assert response.status_code == 200
        assert response.get_json()["response"][output]["children"]["type"] == expected_type
