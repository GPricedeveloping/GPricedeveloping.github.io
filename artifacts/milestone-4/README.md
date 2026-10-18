# CS 499 Milestone Four

Gordon Price

This enhancement adds MongoDB CRUD operations, validation, confirmed deletion, and indexes to the animal-shelter dashboard.

## Files

- `original/` is the unchanged Milestone Three application used as the starting point.
- `enhanced/` contains the database enhancement and all earlier dashboard features.
- `test_results/` contains the test output and measured query comparison.
- `Milestone Four Narrative.docx` explains the changes, course outcomes, and testing.

The original CS 340 artifact was the MongoDB CRUD Dashboard. This package shows the changes from Milestone Three to Milestone Four; the earlier milestone packages remain separate.

## Run the dashboard

Python 3.10 or newer is needed. From the `enhanced` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:8050`. CSV mode is the default and doesn't need a running MongoDB server. The included CSV remains read-only. Rescue filters, candidate rankings, the breed chart, and the map work as before. Rankings follow the rescue category; native table filters affect the chart and map, not the ranked list.

For MongoDB mode, set `DATA_SOURCE=mongo`, `MONGO_URI`, `MONGO_DATABASE`, and `MONGO_COLLECTION` in the environment or a local `.env` file. `.env.example` shows the settings. Credentials and local environments aren't included in the package.

## Database operations

The dashboard stays read-only. `manage_records.py` provides a small command-line interface for maintaining records. It uses the same configured collection as the dashboard. Use a test collection while trying the examples and reload the dashboard after changes.

After setting the MongoDB connection variables:

```powershell
.\.venv\Scripts\python.exe manage_records.py read --rescue water
.\.venv\Scripts\python.exe manage_records.py read --animal-id M4-DEMO
.\.venv\Scripts\python.exe manage_records.py --allow-writes create examples/new_animal.json
```

The create command prints a MongoDB record ID. Use that ID for subsequent operations:

```powershell
.\.venv\Scripts\python.exe manage_records.py read --record-id RECORD_ID
.\.venv\Scripts\python.exe manage_records.py --allow-writes update RECORD_ID examples/update_animal.json
.\.venv\Scripts\python.exe manage_records.py --allow-writes delete RECORD_ID
.\.venv\Scripts\python.exe manage_records.py --allow-writes indexes
```

Replace `RECORD_ID` with the 24-character ID, without angle brackets. Deletion first displays the record, then requires the exact phrase `DELETE RECORD_ID`. Any other response cancels it. There is no bulk-delete command.

Records require `animal_id`, `animal_type`, `breed`, `sex_upon_outcome`, and numeric `age_upon_outcome_in_weeks`. Other supported shelter fields are optional. Updates accept only the fields being changed. Empty updates, unknown fields, nested operators, invalid IDs, nonfinite numbers, negative ages, and out-of-range coordinates are rejected. Dates and descriptive ages remain text; they aren't parsed or automatically synchronized with age in weeks. The validation rules apply to new and updated values, not a cleanup of existing data.

Animal IDs aren't unique in this dataset. MongoDB `_id` identifies a specific outcome record. The repository returns whether an update matched, even when the supplied value was already present.

Writes are disabled unless explicitly enabled. This is an application safeguard, not database authorization. Use a read-only MongoDB account for the dashboard and a separately authorized account for maintenance. A deployed service would still need authentication and access controls; this course application is intended for local use.

## Index comparison

The `indexes` command adds a nonunique animal-ID lookup and a compound rescue index on `animal_type`, `sex_upon_outcome`, `breed`, and `age_upon_outcome_in_weeks`. The equality fields come before the age range. Reads use `_id` order to keep tied rankings stable when the query plan changes.

`benchmark_queries.py` loads a fresh copy of the included 10,000-row CSV into a uniquely named `cs499_m4_benchmark_...` database on a test server. It measures the actual sorted rescue queries before and after adding indexes and checks that the same records return in the same order. It doesn't modify the configured AAC collection or drop existing indexes. The new database is retained for inspection.

```powershell
$env:MONGO_TEST_URI = 'mongodb://127.0.0.1:27017/'
.\.venv\Scripts\python.exe benchmark_queries.py --output ../test_results/query_comparison.json
```

Use a local or dedicated test server for `MONGO_TEST_URI`. The account needs permission to create a test database and indexes. The output includes its database name. Set `MONGO_DATABASE` to that name and `MONGO_COLLECTION=animals` to view the imported sample in the dashboard.

The measured results are in `test_results/query_comparison.json`. Before adding the rescue index, MongoDB used its existing `_id` index for ordering and examined all 10,000 documents. Afterward, it used `rescue_lookup`, examined 18, 5, and 4 documents for Water, Mountain, and Disaster, and sorted those small result sets. No index hints were forced. Single explain timings are recorded for context, not presented as a reliable speed multiplier. Indexes also occupy storage and require maintenance on writes.

The index ordering follows MongoDB's [Equality, Sort, Range guidance](https://www.mongodb.com/docs/manual/tutorial/equality-sort-range-guideline/). Driver behavior is described in MongoDB's [insert](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/insert/) and [update](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/update/) documentation.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Without `MONGO_TEST_URI`, the eight live-database tests are skipped. To include them:

```powershell
$env:MONGO_TEST_URI = 'mongodb://127.0.0.1:27017/'
.\.venv\Scripts\python.exe -m pytest -q
```

Each live test creates a unique `cs499_m4_test_...` database and removes only that test database afterward. Don't point the tests at a production server. The suite covers validation, CRUD behavior, canceled and confirmed deletes, safe error messages, index creation, stable rankings, and dashboard callbacks backed by MongoDB.

Testing used Python 3.14.3, PyMongo 4.18.1, MongoDB 8.2.5, and Dash 3.4.0. Dash reports a warning about a future DataTable removal. It doesn't prevent this version from running; replacing the table component is outside this database enhancement.
