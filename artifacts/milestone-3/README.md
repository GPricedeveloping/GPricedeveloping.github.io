# CS 499 Milestone Three Artifact

- `original` is the working Milestone Two version used as the starting point.
- `enhanced` adds rescue-candidate scoring, heap-based Top-K selection, tests,
  and the ranked-candidate table in the dashboard.
- `Milestone Three Narrative.docx` explains the changes, course outcomes,
  testing, and reflection.

From the `enhanced` folder:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
python app.py
```

Open http://127.0.0.1:8050 in a browser. The app uses the included CSV data by
default. Select a rescue type to see up to five ranked candidates. The ranking
uses all records returned by that rescue filter; the main table's column
filters still control its chart and map.

The score totals 100 points: animal type (20), breed (30), sex (20), age within
the rescue range (10), closeness to the middle of that range (up to 10), and
valid coordinates (10). The age preference is a course-project scoring rule.
Equal scores keep the records' original order.

All 20 tests passed. Browser testing used the included CSV data and covered
Reset, Water Rescue, Mountain/Wilderness Rescue, and Disaster/Individual
Tracking. Live MongoDB testing wasn't part of this milestone.

The `original` folder contains the unchanged Milestone Two source, data, and
tests. Local settings, virtual environments, and caches are excluded from the
submission. New CRUD operations, indexing, and database benchmarks remain
planned for the database milestone.
