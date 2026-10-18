# CS 499 Software Design and Engineering

Gordon Price

The original folder contains the CS 340 notebook and CSV. The enhanced folder contains the modular Dash application from Milestone Two.

The public notebook copy has its credential values removed and saved outputs cleared. Its program logic is unchanged. The original `animal_shelter.py` dependency isn't available, so the notebook is retained for comparison rather than as a complete runnable application.

## Run the enhanced dashboard

From the enhanced folder, with Python 3.10 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open `http://127.0.0.1:8050`. CSV mode is the default and doesn't require MongoDB. For database mode, use the settings in `.env.example` and keep actual credentials in your local environment. Don't commit a populated `.env` file.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The six tests cover the original software-design enhancement. Later packages add ranking and database tests. The Word narrative describes the design changes and learning from this milestone.
