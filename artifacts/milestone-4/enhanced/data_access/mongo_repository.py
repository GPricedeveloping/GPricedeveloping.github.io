"""Read and manage individual shelter records in MongoDB.

Gordon Price | CS 499 Milestone Four | October 3, 2026 | Version 4
"""

from __future__ import annotations

from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from .validation import record_id, validate_query, validate_record


RESCUE_INDEX = "rescue_lookup"
RESCUE_INDEX_KEYS = [
    ("animal_type", 1),
    ("sex_upon_outcome", 1),
    ("breed", 1),
    ("age_upon_outcome_in_weeks", 1),
]


class RepositoryError(RuntimeError):
    """Database failure that can be displayed without connection details."""


class MongoAnimalRepository:
    """Writes are opt-in; the dashboard only uses read access."""

    def __init__(self, uri: str, database: str, collection: str, *, allow_writes=False):
        if not uri:
            raise ValueError("A MongoDB URI is required.")
        if not database or not collection:
            raise ValueError("Database and collection names are required.")
        self._allow_writes = allow_writes is True
        self._client = None
        try:
            self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self._client.admin.command("ping")
            self._collection = self._client[database][collection]
        except PyMongoError:
            self.close()
            raise RepositoryError("Unable to connect to MongoDB. Check the connection settings.") from None

    def _require_writes(self):
        if not self._allow_writes:
            raise ValueError("Writes are disabled for this repository.")

    def read(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = validate_query(query)
        try:
            # Fixed order also keeps tied candidate scores stable after indexing.
            return list(self._collection.find(query).sort("_id", 1))
        except PyMongoError:
            raise RepositoryError("Unable to read animal records.") from None

    def create(self, record: dict[str, Any]) -> str:
        self._require_writes()
        clean = validate_record(record)
        try:
            return str(self._collection.insert_one(clean).inserted_id)
        except PyMongoError:
            raise RepositoryError("Unable to create the animal record.") from None

    def update(self, identifier, changes: dict[str, Any]) -> bool:
        """Return whether a record matched, including an unchanged value."""
        self._require_writes()
        identifier = record_id(identifier)
        clean = validate_record(changes, partial=True)
        try:
            return self._collection.update_one({"_id": identifier}, {"$set": clean}).matched_count == 1
        except PyMongoError:
            raise RepositoryError("Unable to update the animal record.") from None

    def delete(self, identifier, *, confirmed=False) -> bool:
        self._require_writes()
        identifier = record_id(identifier)
        if confirmed is not True:
            raise ValueError("Deletion requires explicit confirmation.")
        try:
            return self._collection.delete_one({"_id": identifier}).deleted_count == 1
        except PyMongoError:
            raise RepositoryError("Unable to delete the animal record.") from None

    def ensure_indexes(self) -> list[str]:
        self._require_writes()
        try:
            # Animal IDs repeat across outcomes, so this index isn't unique.
            animal_index = self._collection.create_index("animal_id", name="animal_id_lookup")
            rescue_index = self._collection.create_index(RESCUE_INDEX_KEYS, name=RESCUE_INDEX)
            return [animal_index, rescue_index]
        except PyMongoError:
            raise RepositoryError("Unable to create the database indexes.") from None

    def explain(self, query=None) -> dict[str, Any]:
        """Measure the same filter and ordering used by read()."""
        query = validate_query(query)
        try:
            return self._collection.database.command(
                "explain",
                {"find": self._collection.name, "filter": query, "sort": {"_id": 1}},
                verbosity="executionStats",
            )
        except PyMongoError:
            raise RepositoryError("Unable to inspect the query plan.") from None

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
