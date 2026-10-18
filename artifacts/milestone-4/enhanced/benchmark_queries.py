"""Compare rescue queries before and after indexing a separate sample database.

Gordon Price | CS 499 Milestone Four | October 3, 2026 | Version 4
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from data_access.mongo_repository import MongoAnimalRepository, RepositoryError
from services.rescue_service import get_rescue_query


def plan_values(node, key):
    result = set()
    if isinstance(node, dict):
        if key in node:
            result.add(node[key])
        for value in node.values():
            result.update(plan_values(value, key))
    elif isinstance(node, list):
        for value in node:
            result.update(plan_values(value, key))
    return sorted(result)


def measure(repository, query):
    plan = repository.explain(query)
    stats = plan["executionStats"]
    return {
        "returned": stats["nReturned"],
        "documents_examined": stats["totalDocsExamined"],
        "keys_examined": stats["totalKeysExamined"],
        "execution_time_ms": stats["executionTimeMillis"],
        "stages": plan_values(plan["queryPlanner"]["winningPlan"], "stage"),
        "index_names": plan_values(plan["queryPlanner"]["winningPlan"], "indexName"),
    }


def benchmark(uri, csv_path):
    # A fresh name prevents the comparison from altering an existing collection.
    database = "cs499_m4_benchmark_" + uuid4().hex
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    repository = None
    try:
        client.admin.command("ping")
        frame = pd.read_csv(csv_path)
        frame = frame.loc[:, ~frame.columns.str.startswith("Unnamed:")]
        records = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
        collection = client[database]["animals"]
        collection.insert_many(records)
        repository = MongoAnimalRepository(uri, database, "animals", allow_writes=True)
        queries = {name: get_rescue_query(name) for name in ("water", "mountain", "disaster")}
        before = {name: measure(repository, query) for name, query in queries.items()}
        identities = {name: [r["_id"] for r in repository.read(query)] for name, query in queries.items()}
        started = perf_counter()
        indexes = repository.ensure_indexes()
        index_build_ms = round((perf_counter() - started) * 1000, 3)
        after = {name: measure(repository, query) for name, query in queries.items()}
        same_results = all(
            identities[name] == [r["_id"] for r in repository.read(query)]
            for name, query in queries.items()
        )
        if not same_results:
            raise RuntimeError("Indexing changed the query results or their order.")
        sizes = client[database].command("collStats", "animals")["indexSizes"]
        return {
            "tested_at_utc": datetime.now(timezone.utc).isoformat(),
            "mongodb_version": client.server_info()["version"],
            "database": database,
            "records": len(records),
            "duplicate_animal_ids": int(frame["animal_id"].duplicated().sum()),
            "indexes": indexes,
            "index_build_ms": index_build_ms,
            "index_sizes_bytes": sizes,
            "same_results_and_order": same_results,
            "before": before,
            "after": after,
            "notes": "Fresh copy of the included CSV; no forced index hints. Explain timings are single observations, not a latency benchmark. Database retained for inspection.",
        }
    finally:
        if repository is not None:
            repository.close()
        client.close()


def main():
    command = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    command.add_argument("--csv", type=Path, default=Path(__file__).parent / "data" / "aac_shelter_outcomes.csv")
    command.add_argument("--output", type=Path, required=True)
    args = command.parse_args()
    uri = os.getenv("MONGO_TEST_URI")
    if not uri:
        command.error("Set MONGO_TEST_URI to a local or dedicated test MongoDB server.")
    try:
        report = benchmark(uri, args.csv)
    except (PyMongoError, RepositoryError):
        print("Database comparison failed. Check the test server and permissions.")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
