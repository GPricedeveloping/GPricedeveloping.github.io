"""Command-line access to the database enhancement.

Gordon Price | CS 499 Milestone Four | October 3, 2026 | Version 4
"""

import argparse
import json
from pathlib import Path

from config import Settings
from data_access.mongo_repository import MongoAnimalRepository, RepositoryError
from services.rescue_service import get_rescue_query


def parser():
    command = argparse.ArgumentParser(description="Manage shelter records in MongoDB.")
    command.add_argument("--allow-writes", action="store_true", help="Enable create, update, delete, or index commands.")
    actions = command.add_subparsers(dest="action", required=True)
    read = actions.add_parser("read")
    search = read.add_mutually_exclusive_group()
    search.add_argument("--record-id")
    search.add_argument("--animal-id")
    search.add_argument("--rescue", choices=["reset", "water", "mountain", "disaster"], default="reset")
    create = actions.add_parser("create")
    create.add_argument("file", type=Path, help="JSON object containing a new record.")
    update = actions.add_parser("update")
    update.add_argument("record_id")
    update.add_argument("file", type=Path, help="JSON object containing only the fields to change.")
    delete = actions.add_parser("delete")
    delete.add_argument("record_id")
    actions.add_parser("indexes")
    return command


def run_action(args, repository):
    if args.action == "read":
        query = get_rescue_query(args.rescue)
        if args.record_id:
            query = {"_id": args.record_id}
        elif args.animal_id:
            query = {"animal_id": args.animal_id}
        print(json.dumps(repository.read(query), default=str, indent=2, allow_nan=False))
    elif args.action in {"create", "update"}:
        with args.file.open(encoding="utf-8-sig") as source:
            record = json.load(source)
        if args.action == "create":
            print("Created record:", repository.create(record))
        else:
            print("Record matched and updated." if repository.update(args.record_id, record) else "No matching record.")
    elif args.action == "delete":
        matches = repository.read({"_id": args.record_id})
        if not matches:
            print("No matching record.")
            return
        print(json.dumps(matches[0], default=str, indent=2, allow_nan=False))
        confirmation = input(f"Type DELETE {args.record_id} to delete this record: ")
        if confirmation != f"DELETE {args.record_id}":
            print("Delete canceled.")
            return
        print("Record deleted." if repository.delete(args.record_id, confirmed=True) else "No matching record.")
    else:
        print("Indexes:", ", ".join(repository.ensure_indexes()))


def main(argv=None):
    args = parser().parse_args(argv)
    repository = None
    try:
        if args.action != "read" and not args.allow_writes:
            raise ValueError("Use --allow-writes for this operation.")
        settings = Settings.from_env()
        if settings.data_source != "mongo":
            raise ValueError("Set DATA_SOURCE=mongo and MONGO_URI before managing records. CSV mode is read-only.")
        repository = MongoAnimalRepository(
            settings.mongo_uri, settings.mongo_database, settings.mongo_collection,
            allow_writes=args.allow_writes,
        )
        run_action(args, repository)
        return 0
    except (ValueError, RepositoryError) as error:
        print(f"Error: {error}")
        return 1
    except OSError:
        print("Error: Unable to read the JSON file.")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Operation canceled.")
        return 1
    finally:
        if repository is not None:
            repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
