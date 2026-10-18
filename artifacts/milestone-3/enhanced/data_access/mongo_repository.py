"""Read animal records from MongoDB."""

from __future__ import annotations

from typing import Any


class MongoAnimalRepository:
    """Read-only access to the animal collection."""

    def __init__(self, uri: str, database: str, collection: str):
        if not uri:
            raise ValueError("A MongoDB URI is required.")

        # Import lazily so the CSV mode can run without pymongo installed.
        from pymongo import MongoClient

        self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self._client.admin.command("ping")
        self._collection = self._client[database][collection]

    def read(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return list(self._collection.find(query or {}))

    def close(self) -> None:
        self._client.close()
