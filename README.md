# Kenya TB Care Cascade Explorer
# Wayne Willis Omondi

An interactive Streamlit application for examining the path from WHO-estimated
tuberculosis burden to case notification and treatment outcomes.

The project pulls the WHO Global TB Database at runtime.

## What the app contains

- **Care cascade Sankey**
  - estimated TB incidence
  - notified new and relapse cases
  - notification gap
  - new-and-relapse treatment cohort
  - treatment success
  - deaths
  - treatment failure
  - loss to follow-up
  - not evaluated

- **Historical trends**
  - estimated incidence vs notifications
  - notifications as a share of estimated incidence
  - downloadable country-year analytical table

- **Treatment outcomes**
  - outcome distribution for the latest compatible cohort year

- **Data notes**
  - definitions
  - interpretation caveats
  - live source URLs
  - refresh behaviour

## Stack

- Python
- Streamlit
- Pandas
- Plotly
- Requests

Plotly's `go.Sankey` provides the central flow visualization.

## Data sources

The app reads three WHO CSV endpoints:

```text
https://extranet.who.int/tme/generateCSV.asp?ds=estimates
https://extranet.who.int/tme/generateCSV.asp?ds=notifications
https://extranet.who.int/tme/generateCSV.asp?ds=outcomes
```

WHO source page:

```text
https://www.who.int/teams/global-programme-on-tuberculosis-and-lung-health/data
```

The WHO Global TB Database is updated as countries report corrections. Values
shown by the app can therefore change after a refresh.

## Main fields used

### Burden estimates

| Field | Use |
|---|---|
| `e_inc_num` | Estimated number of incident TB cases |
| `e_inc_num_lo` | Lower uncertainty bound, when available |
| `e_inc_num_hi` | Upper uncertainty bound, when available |
| `e_inc_100k` | Estimated incidence rate per 100,000 |
| `e_pop_num` | Estimated population |
| `c_cdr` | WHO case detection / diagnosis-treatment coverage measure, when present |

### Notifications

The application first looks for `c_newinc`, WHO's total new and relapse
notification count. Compatibility aliases are included in case export labels
change.

### Treatment outcomes

The application reads the WHO new-and-relapse cohort fields:

```text
newrel_coh
newrel_succ
newrel_died
newrel_fail
newrel_lost / newrel_ltfu
newrel_neval
```

Compatibility aliases are included for common prefixed variants.

## Interpretation

The app deliberately does **not** label the difference between WHO estimated
incidence and notifications as a count of "undiagnosed people".

It is shown as a **notification gap**:

```text
notification_gap = estimated_incidence - notified_cases
```

Estimated incidence is modelled. Notifications are surveillance counts.
The difference can reflect people who were not diagnosed, people diagnosed but
not notified, reporting incompleteness, private-sector gaps, and uncertainty in
the incidence estimate.

Treatment outcomes may refer to an earlier cohort than the selected reporting
year. When an exact outcome year is unavailable, the app uses the latest cohort
at or before the selected year and displays that cohort year explicitly.

## Run locally

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Streamlit

```bash
streamlit run app.py
```

The terminal prints the local URL, normally:

```text
http://localhost:8501
```

## Project structure

```text
kenya_tb_care_cascade/
├── app.py
├── charts.py
├── data.py
├── requirements.txt
├── README.md
├── assets/
│   └── styles.css
└── .streamlit/
    └── config.toml
```

`data.py` handles downloading, caching, country filtering, variable mapping and
derived metrics. `charts.py` only builds visualizations. `app.py` handles the
user interface and page logic.

This separation makes it easier to replace WHO CSV retrieval later with:

- a scheduled ETL pipeline
- DuckDB or PostgreSQL
- a FastAPI service
- county-level Kenya programme data
- a materialized analytical warehouse

without rewriting the visualization layer.

## Next extensions

A second data layer could introduce Kenya county-level notifications and
treatment outcomes, if an authoritative public dataset or approved programme
extract is available. The national WHO series should remain separate from any
subnational source so definitions and reporting periods can be audited.
