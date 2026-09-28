# Kenya TB Care Cascade Explorer
# Wayne Willis Omondi

An interactive Streamlit application for examining the path from WHO-estimated
tuberculosis burden to case notification and treatment outcomes.

The project pulls the WHO Global TB Database at runtime.

## What the app contains

- **Cohort-aligned care cascade**
  - a full Sankey from estimated incidence through notification and the
    treatment cohort to treatment outcomes
  - terminal branches for the estimated notification gap and the
    notification-to-cohort reconciliation difference, kept visually separate
    from treatment outcomes
  - a grouped count-and-share table with the correct denominator for every row

- **Historical trends**
  - estimated incidence vs notifications
  - notifications as a share of estimated incidence
  - treatment-outcome composition by cohort year
  - estimated TB mortality among HIV-negative people, with a pointer to the
    TB/HIV mortality series
  - downloadable country-year analytical table

- **TB/HIV trends**
  - WHO-estimated TB incidence among people living with HIV, with its
    uncertainty range
  - HIV testing coverage and HIV positivity among notified TB cases
  - TB/HIV treatment-outcome composition by cohort enrollment year
  - WHO-estimated TB mortality among people living with HIV, kept separate
    from deaths recorded in a TB/HIV treatment cohort

- **Who is notified?**
  - age and sex composition of reported new and relapse TB notifications
  - child (0–14) share of notifications
  - adult male-to-female notification ratio
  - age/sex reporting coverage, so incomplete classifications are visible

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

Plotly's `go.Sankey` provides the cohort-aligned care cascade. The Sankey is an
aggregate comparison rather than a person-linked patient flow: only the outcome
cohort feeds the treatment-outcome branches.

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
| `e_inc_tbhiv_num` | Estimated incident TB among people living with HIV |
| `e_mort_num` | Estimated TB mortality among HIV-negative people |
| `e_mort_tbhiv_num` | Estimated TB mortality among people living with HIV |
| `e_pop_num` | Estimated population |
| `c_cdr` | WHO case detection / diagnosis-treatment coverage measure, when present |

### Notifications

The application first looks for `c_newinc`, WHO's total new and relapse
notification count. Compatibility aliases are included in case export labels
change.

The TB/HIV view uses `newrel_hivtest` and `newrel_hivpos` to
calculate HIV testing coverage among notified TB cases and HIV positivity among
those tested. The current Kenya series does not provide a complete comparable
ART measure for the displayed period, so the app does not show ART coverage.

The age-and-sex notification profile uses:

```text
newrel_m014       boys aged 0–14
newrel_f014       girls aged 0–14
newrel_m15plus    men aged 15 and older
newrel_f15plus    women aged 15 and older
```

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

For TB/HIV cohorts, the application uses:

```text
tbhiv_coh
tbhiv_succ
tbhiv_died
tbhiv_fail
tbhiv_lost
```

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

The main selector is the **treatment cohort enrollment year** and includes only
years for which incidence, notifications and treatment-cohort outcomes are all
available. Outcomes occur later but remain attributed to the cohort's enrollment
year. Newer incidence and notification years remain available in the Trends tab;
the app never substitutes an earlier outcome cohort into a newer cascade.

The notification-to-cohort difference reconciles two aggregate definitions and
must not be interpreted as a count of people who were not treated. The residual
outcome is calculated as the treatment cohort minus the outcome categories
separately reported in the WHO export.

Population mortality is not a treatment outcome. Historical Trends presents
WHO-estimated TB mortality among HIV-negative people; TB/HIV Trends presents
WHO-estimated TB mortality among people living with HIV. Neither series should
be read as deaths recorded in the corresponding treatment cohort.

The age-and-sex tab describes notified case mix only. It should not be used to
infer age- or sex-specific TB incidence, risk, diagnostic access, or treatment
quality without appropriate population denominators and more granular data.

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
