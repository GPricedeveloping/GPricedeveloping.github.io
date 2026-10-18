"""Animal-shelter dashboard with rescue filters and candidate rankings.

Gordon Price | CS 499 Milestone Four | October 3, 2026 | Version 4
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from dash import Dash, Input, Output, dash_table, dcc, html
import dash_leaflet as dl
import plotly.express as px

from config import Settings
from data_access import AnimalRepository, CsvAnimalRepository, MongoAnimalRepository
from services import DEFAULT_TOP_K, get_rescue_query, rank_candidates


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


DISPLAY_COLUMNS = [
    "animal_id",
    "name",
    "animal_type",
    "breed",
    "sex_upon_outcome",
    "age_upon_outcome",
    "outcome_type",
    "location_lat",
    "location_long",
]

RANKED_COLUMNS = [
    ("Rank", "rank"),
    ("Animal ID", "animal_id"),
    ("Name", "name"),
    ("Breed", "breed"),
    ("Age", "age_upon_outcome"),
    ("Suitability Score", "suitability_score"),
]


def create_repository(settings: Settings) -> AnimalRepository:
    if settings.data_source == "mongo":
        return MongoAnimalRepository(
            uri=settings.mongo_uri or "",
            database=settings.mongo_database,
            collection=settings.mongo_collection,
        )
    return CsvAnimalRepository(settings.csv_path)


def records_to_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    if "_id" in frame.columns:
        frame = frame.drop(columns=["_id"])
    unnamed = [c for c in frame.columns if str(c).startswith("Unnamed:")]
    if unnamed:
        frame = frame.drop(columns=unnamed)
    return frame


def public_columns(frame: pd.DataFrame) -> list[str]:
    preferred = [column for column in DISPLAY_COLUMNS if column in frame.columns]
    return preferred or list(frame.columns)


def create_app(
    settings: Settings | None = None,
    repository: AnimalRepository | None = None,
) -> Dash:
    settings = settings or Settings.from_env()
    repository = repository or create_repository(settings)

    try:
        initial_frame = records_to_frame(repository.read({}))
        startup_error = ""
    except Exception:
        LOGGER.error("Unable to load initial animal data")
        initial_frame = pd.DataFrame()
        startup_error = "Unable to load animal data. Check the data source and connection settings."

    columns = public_columns(initial_frame)

    app = Dash(__name__)
    app.title = "Gordon Price - Animal Shelter Dashboard"

    app.layout = html.Div(
        [
            html.H2("Gordon Price - Animal Shelter Dashboard"),
            html.P(
                "CS 499 Milestone Four: Databases and Rescue Candidate Ranking"
            ),
            html.Div(
                startup_error,
                id="error-message",
                role="alert",
                style={"color": "#a61b1b", "fontWeight": "600", "minHeight": "24px"},
            ),
            html.Hr(),
            dcc.RadioItems(
                id="filter-type",
                options=[
                    {"label": "Reset (All)", "value": "reset"},
                    {"label": "Water Rescue", "value": "water"},
                    {"label": "Mountain/Wilderness Rescue", "value": "mountain"},
                    {"label": "Disaster/Individual Tracking", "value": "disaster"},
                ],
                value="reset",
                inline=True,
                labelStyle={"marginRight": "18px", "fontWeight": 500},
            ),
            html.Hr(),
            dash_table.DataTable(
                id="datatable-id",
                columns=[{"name": column, "id": column} for column in columns],
                data=initial_frame[columns].to_dict("records") if columns else [],
                row_selectable="single",
                selected_rows=[0] if not initial_frame.empty else [],
                page_size=10,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                column_selectable="single",
                style_table={"height": "400px", "overflowY": "auto"},
                style_cell={
                    "textAlign": "left",
                    "minWidth": "120px",
                    "width": "120px",
                    "maxWidth": "180px",
                    "whiteSpace": "normal",
                },
            ),
            html.Br(),
            html.Hr(),
            html.H3("Top Rescue Candidates"),
            html.P(
                "Up to five matching animals, ordered by suitability score."
            ),
            html.Div(
                "Choose a rescue type to rank matching animals.",
                id="ranking-message",
                style={"minHeight": "24px"},
            ),
            dash_table.DataTable(
                id="ranked-candidates-id",
                columns=[{"name": name, "id": column} for name, column in RANKED_COLUMNS],
                data=[],
                page_size=DEFAULT_TOP_K,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px"},
                style_header={"fontWeight": "bold"},
                style_data_conditional=[
                    {
                        "if": {"filter_query": "{rank} = 1"},
                        "backgroundColor": "#E8F5E9",
                        "fontWeight": "600",
                    }
                ],
            ),
            html.Br(),
            html.Hr(),
            html.Div(
                className="row",
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                children=[
                    html.Div(id="graph-id", style={"flex": "1 1 460px"}),
                    html.Div(id="map-id", style={"flex": "1 1 460px"}),
                ],
            ),
        ],
        style={"maxWidth": "1500px", "margin": "0 auto", "padding": "16px"},
    )

    @app.callback(
        Output("datatable-id", "data"),
        Output("datatable-id", "columns"),
        Output("datatable-id", "selected_rows"),
        Output("error-message", "children"),
        Output("ranked-candidates-id", "data"),
        Output("ranking-message", "children"),
        Input("filter-type", "value"),
    )
    def update_dashboard(filter_type: str):
        try:
            query = get_rescue_query(filter_type)
            records = repository.read(query)
            frame = records_to_frame(records)
            visible = public_columns(frame)
            data = frame[visible].to_dict("records") if visible else []
            table_columns = [{"name": column, "id": column} for column in visible]
            selected = [0] if data else []

            if filter_type == "reset":
                ranked_data = []
                ranking_message = "Choose a rescue type to rank matching animals."
            else:
                ranked = rank_candidates(records, filter_type, DEFAULT_TOP_K)
                ranked_data = [
                    {column: animal.get(column) for _, column in RANKED_COLUMNS}
                    for animal in ranked
                ]
                if ranked_data:
                    ranking_message = (
                        f"Showing the top {len(ranked_data)} of {len(records)} "
                        "matching animals."
                    )
                else:
                    ranking_message = "No animals matched this rescue type."

            return data, table_columns, selected, "", ranked_data, ranking_message
        except Exception:
            LOGGER.error("Dashboard filter failed")
            return (
                [],
                [],
                [],
                "Unable to apply filter. Check the data source and connection settings.",
                [],
                "Candidate ranking is unavailable.",
            )

    @app.callback(
        Output("datatable-id", "style_data_conditional"),
        Input("datatable-id", "selected_columns"),
    )
    def update_styles(selected_columns: list[str] | None):
        return [
            {"if": {"column_id": column}, "backgroundColor": "#D2F3FF"}
            for column in (selected_columns or [])
        ]

    @app.callback(
        Output("graph-id", "children"),
        Input("datatable-id", "derived_virtual_data"),
    )
    def update_graphs(view_data: list[dict[str, Any]] | None):
        if not view_data:
            return html.Div("No data to chart")

        frame = pd.DataFrame(view_data)
        if frame.empty or "breed" not in frame.columns:
            return html.Div("No breed data to chart")

        top = frame["breed"].value_counts().nlargest(10)
        figure = px.pie(
            values=top.values,
            names=top.index,
            title="Top Breeds in Current Selection (Top 10)",
        )
        return dcc.Graph(figure=figure)

    @app.callback(
        Output("map-id", "children"),
        Input("datatable-id", "derived_virtual_data"),
        Input("datatable-id", "derived_virtual_selected_rows"),
    )
    def update_map(
        view_data: list[dict[str, Any]] | None,
        selected_rows: list[int] | None,
    ):
        if not view_data:
            return html.Div("No data to map")

        frame = pd.DataFrame(view_data)
        row = selected_rows[0] if selected_rows else 0
        if row < 0 or row >= len(frame):
            return html.Div("Invalid row selection")

        required = {"location_lat", "location_long"}
        missing = required.difference(frame.columns)
        if missing:
            return html.Div(f"Missing location field(s): {', '.join(sorted(missing))}")

        lat = frame.iloc[row]["location_lat"]
        lon = frame.iloc[row]["location_long"]
        if pd.isna(lat) or pd.isna(lon):
            return html.Div("Selected record is missing coordinates")

        breed = str(frame.iloc[row].get("breed", "(unknown)"))
        name = str(frame.iloc[row].get("name") or "(no name)")

        return dl.Map(
            style={"width": "100%", "height": "500px"},
            center=[float(lat), float(lon)],
            zoom=10,
            children=[
                dl.TileLayer(),
                dl.Marker(
                    position=[float(lat), float(lon)],
                    children=[
                        dl.Tooltip(breed),
                        dl.Popup([html.H4("Animal Name"), html.P(name)]),
                    ],
                ),
            ],
        )

    return app


if __name__ == "__main__":
    application_settings = Settings.from_env()
    dashboard = create_app(application_settings)
    dashboard.run(
        host=application_settings.host,
        port=application_settings.port,
        debug=application_settings.debug,
    )
