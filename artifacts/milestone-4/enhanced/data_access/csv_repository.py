"""Read local CSV records using equality, $in, $gte, and $lte filters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class CsvAnimalRepository:
    def __init__(self, csv_path: Path | str):
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV data file not found: {self.csv_path}")

        self._frame = pd.read_csv(self.csv_path)
        unnamed_columns = [c for c in self._frame.columns if c.startswith("Unnamed:")]
        if unnamed_columns:
            self._frame = self._frame.drop(columns=unnamed_columns)

    def read(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = query or {}
        frame = self._frame

        for field, condition in query.items():
            if field not in frame.columns:
                return []

            if isinstance(condition, dict):
                for operator, value in condition.items():
                    if operator == "$in":
                        frame = frame[frame[field].isin(value)]
                    elif operator == "$gte":
                        frame = frame[frame[field] >= value]
                    elif operator == "$lte":
                        frame = frame[frame[field] <= value]
                    else:
                        raise ValueError(f"Unsupported query operator: {operator}")
            else:
                frame = frame[frame[field] == condition]

        # Dash expects normal Python values rather than pandas/numpy scalar types.
        clean = frame.where(pd.notna(frame), None)
        return clean.to_dict(orient="records")
