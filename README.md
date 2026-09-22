# 🏛️ Dust & Data

**Dust & Data** is a Streamlit dashboard that finds incomplete artwork records in the [Cleveland Museum of Art Open Access collection](https://openaccess-api.clevelandart.org/).

It gives each record a metadata completeness score and creates a ranked queue of records that may need attention.

## ✨ What it does

Dust & Data checks five parts of each artwork record:

- 🖼️ Public image availability
- 📅 Date precision
- 🧱 Medium and material detail
- 👤 Artist or culture attribution
- 📝 Description availability

The app lets you:

- Review the lowest-scoring records first
- See exactly why each record received its score
- Filter by department, object type, license, score, or missing information
- Compare metadata quality using charts and summary metrics
- Export the filtered review queue as a CSV file
- Choose a sample of 250, 500, or 1,000 records

The default sample size is **500 records**, which offers a good balance between speed and coverage.

## 📥 Download the project

### Option 1: Download a ZIP

1. Open the [Dust & Data GitHub repository](https://github.com/11samm/Dust-Data).
2. Select **Code** → **Download ZIP**.
3. Extract the ZIP file somewhere on your computer.
4. Open a terminal inside the extracted folder.

### Option 2: Clone with Git

```bash
git clone https://github.com/11samm/Dust-Data.git
cd Dust-Data
```

## 🚀 Install and run

You need [Python](https://www.python.org/downloads/) installed on your computer and an internet connection for downloading museum records.

### Windows

Open PowerShell inside the project folder and run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

After installing the requirements once, you can also start the app by double-clicking `run.bat`.

### macOS or Linux

Open a terminal inside the project folder and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit will open the dashboard in your browser. If it does not open automatically, visit:

```text
http://localhost:8501
```

## 🧭 Using the dashboard

1. Choose a sample mode: **Stratified**, **Department**, or **Type**.
2. Choose a sample size. Start with **250** for speed or **500** for normal use.
3. Select **Refresh sample** when you want a new randomized set of records.
4. Use the sidebar filters to focus on specific metadata gaps.
5. Select **Evidence** beside a record to see how its score was calculated.
6. Use **Export queue** to download the current results as a CSV file.

The first load may take a little longer because the app downloads data from the museum API. Samples are cached locally so later visits are faster.

## 🧮 Understanding the score

Scores range from **0 to 100**. Higher scores indicate more complete public-facing metadata.

| Dimension | Weight |
| --- | ---: |
| Image | 15% |
| Date | 25% |
| Medium | 20% |
| Attribution | 25% |
| Description | 15% |

The evidence dialog shows the band, score, weight, and source value used for every dimension. A low score identifies missing or vague metadata; it does not judge the quality or importance of the artwork itself.

## 🧪 Run the tests

```bash
python -m pytest
```

The normal test suite runs without contacting the museum API. Optional live API checks can be run with:

```bash
python -m pytest -m live
```

## 🔧 Troubleshooting

### PowerShell blocks virtual environment activation

Run the commands without activating the environment:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

### Streamlit asks for an email address

Press **Enter** without entering an email address. This prompt normally appears only on the first Streamlit launch.

### The museum API is temporarily unavailable

If a previous sample exists, Dust & Data will show the cached version. Try **Refresh sample** again later to download new records.

## 📚 More detail

See [ARCHITECTURE.md](ARCHITECTURE.md) for the complete scoring policy, data model, API behavior, and project structure.
