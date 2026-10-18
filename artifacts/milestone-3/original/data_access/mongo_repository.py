"""MongoDB repository replacing the missing original animal_shelter.py dependency."""

from __future__ import annotations

from typing import Any


class MongoAnimalRepository:
    """Read-only repository for Milestone Two.

    Create/update/delete operations are intentionally reserved for the later
    database enhancement milestone so this milestone stays focused on software
    design and engineering.
    """

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
