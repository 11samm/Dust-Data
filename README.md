# 🏛️ Dust & Data

**Dust & Data** helps museum staff find public artwork records that may need metadata review. It gives each sampled record a completeness score, puts records with the most gaps first, and shows the source information behind every score.

**Try the live app:** [dust-data.streamlit.app](https://dust-data.streamlit.app/). You can also run it locally using the instructions below.

**The Getty integration is the focus of this project.** I first built the review workflow with the [Cleveland Museum of Art's Open Access API](https://openaccess-api.clevelandart.org/), whose straightforward artwork fields made it a useful starting point. I then adapted the same workflow to the [J. Paul Getty Museum Collection API](https://data.getty.edu/museum/collection/docs/). Getty's nested Linked.Art data, vocabulary references, and IIIF images made this the main test of whether one review tool could handle very different museum data.

Read the [product requirements document (PDF)](./Dust%20%26%20Data%20PRD.pdf) for the problem, product decisions, tradeoffs, and proposed validation.

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
- See patterns in the current sample using charts and summary metrics
- Export the filtered review queue as a CSV file
- Choose a Cleveland sample of 250, 500, or 1,000 records, or a Getty exploratory sample of 5, 25, 50, or 100 objects

Getty defaults to **25** objects; Cleveland defaults to **500**. Pressing **Refresh sample** requests a new group of records. For Getty, the new group excludes the immediately previous group. Getty's selection is exploratory, so its charts describe the current sample rather than the whole collection.

## Why Getty needed extra work

Getty records are rich, but the information needed for this review is spread across nested fields. The app finds Getty object IDs, downloads each record, and translates its title, date, maker, materials, description, rights, and image links into the same format used by the review queue. It keeps the original Getty record available in **Evidence** so a person can check the interpretation.

Getty also uses the [Art & Architecture Thesaurus (AAT)](https://www.getty.edu/research/tools/vocabularies/aat/) to identify concepts. For a medium such as a material or technique, the app checks a relevant AAT ID already in the Getty record first. If there is none, it tries the project's local vocabulary, then a saved lookup, then a live Getty AAT search. If no reliable match is found, it leaves the term unresolved for human review. An AAT ID describing the *type of object* does not automatically count as evidence for its medium.

When a Getty image is available, **Evidence** shows a small preview and links to its IIIF image and manifest. It labels image rights separately from metadata rights. When image availability cannot be established, the score leaves that dimension unassessed instead of treating the image as missing.

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

1. Choose **J. Paul Getty Museum** under **Museum** and start with **5** objects for a quick look, or **25** for a broader review. Cleveland is also available with **Stratified**, **Department**, and **Type** sample modes.
2. Select **Refresh sample** when you want a new group of records.
3. Use the sidebar filters to focus on specific metadata gaps.
4. Select **Evidence** beside a record to see how its score was calculated.
5. Use **Export queue** to download the current results as a CSV file.

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

The evidence dialog shows the rating, points, weight, and source value used for every dimension. A low score identifies missing or vague information for review; it does not judge the artwork, prove that the museum record is wrong, or rank museums against one another. The weights and ratings are prototype choices that still need review with collections professionals.

## 🧪 Run the tests

```bash
python -m pytest
```

The normal test suite runs without contacting the museum API. Optional live API checks can be run with:

```bash
python -m pytest -m live
```

The Getty tests include saved real-world examples so parsing and scoring can be checked without relying on a live service. A small live spot check also compared sampled records with Getty's source JSON, verified a Getty image and manifest, and confirmed that a refresh produced a different five-record group. These checks do not establish accuracy across Getty's entire collection.

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

See the [PRD](./Dust%20%26%20Data%20PRD.pdf) for the product reasoning and planned validation, or [ARCHITECTURE.md](./ARCHITECTURE.md) for the implementation. The scoring rules live in `src/dust/score/`, source adapters in `src/dust/sources/`, and regression examples in `tests/`.
