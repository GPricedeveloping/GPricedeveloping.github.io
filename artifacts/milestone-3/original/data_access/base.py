"""Common repository interface used by the dashboard service layer."""

from __future__ import annotations

from typing import Any, Protocol


class AnimalRepository(Protocol):
    """Small interface the UI depends on instead of a concrete database class."""

    def read(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return records matching the supplied query."""
        ...
