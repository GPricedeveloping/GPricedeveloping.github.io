"""Load application settings from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    data_source: str
    csv_path: Path
    mongo_uri: str | None
    mongo_database: str
    mongo_collection: str
    host: str
    port: int
    debug: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        base_dir = Path(__file__).resolve().parent
        csv_default = base_dir / "data" / "aac_shelter_outcomes.csv"

        data_source = os.getenv("DATA_SOURCE", "csv").strip().lower()
        if data_source not in {"csv", "mongo"}:
            raise ConfigurationError("DATA_SOURCE must be either 'csv' or 'mongo'.")

        mongo_uri = os.getenv("MONGO_URI") or None
        if data_source == "mongo" and not mongo_uri:
            raise ConfigurationError(
                "MONGO_URI is required when DATA_SOURCE is set to 'mongo'."
            )

        try:
            port = int(os.getenv("PORT", "8050"))
        except ValueError as exc:
            raise ConfigurationError("PORT must be an integer.") from exc

        debug = os.getenv("DEBUG", "false").strip().lower() in {"1", "true", "yes"}

        return cls(
            data_source=data_source,
            csv_path=Path(os.getenv("CSV_PATH", str(csv_default))).expanduser(),
            mongo_uri=mongo_uri,
            mongo_database=os.getenv("MONGO_DATABASE", "AAC"),
            mongo_collection=os.getenv("MONGO_COLLECTION", "animals"),
            host=os.getenv("HOST", "127.0.0.1"),
            port=port,
            debug=debug,
        )
