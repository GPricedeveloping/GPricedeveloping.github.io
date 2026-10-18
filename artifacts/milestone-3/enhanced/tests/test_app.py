from pathlib import Path

from app import create_app
from config import Settings


class StubRepository:
    def __init__(self, records):
        self.records = records

    def read(self, query=None):
        return self.records


def settings():
    return Settings(
        data_source="csv",
        csv_path=Path("unused.csv"),
        mongo_uri=None,
        mongo_database="AAC",
        mongo_collection="animals",
        host="127.0.0.1",
        port=8050,
        debug=False,
    )


def records():
    return [
        {
            "animal_id": "A100",
            "name": "Middle",
            "animal_type": "Dog",
            "breed": "Labrador Retriever Mix",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome": "1 year",
            "age_upon_outcome_in_weeks": 91,
            "outcome_type": "Transfer",
            "location_lat": 30.27,
            "location_long": -97.74,
        },
        {
            "animal_id": "A101",
            "name": "Young",
            "animal_type": "Dog",
            "breed": "Labrador Retriever",
            "sex_upon_outcome": "Intact Female",
            "age_upon_outcome": "6 months",
            "age_upon_outcome_in_weeks": 26,
            "outcome_type": "Transfer",
            "location_lat": 30.28,
            "location_long": -97.75,
        },
    ]


def test_app_serves_layout_with_existing_and_ranking_components():
    dashboard = create_app(settings(), StubRepository(records()))
    client = dashboard.server.test_client()

    assert client.get("/").status_code == 200
    layout_text = client.get("/_dash-layout").get_data(as_text=True)
    for component_id in (
        "filter-type",
        "datatable-id",
        "graph-id",
        "map-id",
        "ranked-candidates-id",
        "ranking-message",
    ):
        assert component_id in layout_text


def test_water_filter_callback_returns_ranked_candidates():
    dashboard = create_app(settings(), StubRepository(records()))
    client = dashboard.server.test_client()
    callback_key = next(
        key
        for key in dashboard.callback_map
        if "datatable-id.data" in key and "ranked-candidates-id.data" in key
    )
    response = client.post(
        "/_dash-update-component",
        json={
            "output": callback_key,
            "outputs": [
                {"id": "datatable-id", "property": "data"},
                {"id": "datatable-id", "property": "columns"},
                {"id": "datatable-id", "property": "selected_rows"},
                {"id": "error-message", "property": "children"},
                {"id": "ranked-candidates-id", "property": "data"},
                {"id": "ranking-message", "property": "children"},
            ],
            "changedPropIds": ["filter-type.value"],
            "inputs": [
                {"id": "filter-type", "property": "value", "value": "water"}
            ],
            "state": [],
        },
    )

    assert response.status_code == 200
    body = response.get_json()["response"]
    ranked = body["ranked-candidates-id"]["data"]
    assert [animal["animal_id"] for animal in ranked] == ["A100", "A101"]
    assert [animal["rank"] for animal in ranked] == [1, 2]
    assert body["error-message"]["children"] == ""
