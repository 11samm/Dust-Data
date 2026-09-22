# Dust & Data

Streamlit dashboard that scores Cleveland Museum of Art Open Access metadata for public-facing completeness and ranks records to fix first.

Policy, UI, and module boundaries are defined in [ARCHITECTURE.md](ARCHITECTURE.md).

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Tests

```bash
python -m pytest
```

Offline tests cover normalizers and scoring policy. Live API checks (optional): `python -m pytest -m live`.

## Run

From the project folder (use `python -m` if `streamlit` / `pytest` are not on your PATH):

```bash
python -m streamlit run app.py
```

On Windows you can also double-click or run `run.bat`.

If Streamlit stops at an **Email:** prompt on first launch, press Enter once (blank email) or create `%USERPROFILE%\.streamlit\credentials.toml` with `[general]` and `email = ""`, then run again.
