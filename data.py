from __future__ import annotations

from io import StringIO
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd
import requests
import streamlit as st


WHO_ENDPOINTS = {
    "estimates": "https://extranet.who.int/tme/generateCSV.asp?ds=estimates",
    "notifications": "https://extranet.who.int/tme/generateCSV.asp?ds=notifications",
    "outcomes": "https://extranet.who.int/tme/generateCSV.asp?ds=outcomes",
}

WHO_DATA_PAGE = (
    "https://www.who.int/teams/global-programme-on-tuberculosis-and-lung-health/data"
)


class DataLoadError(RuntimeError):
    pass


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_who_csv(dataset: str) -> pd.DataFrame:
    if dataset not in WHO_ENDPOINTS:
        raise ValueError(f"Unknown WHO dataset: {dataset}")

    url = WHO_ENDPOINTS[dataset]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; KenyaTBCascade/1.0; "
            "+https://www.who.int/)"
        ),
        "Accept": "text/csv,text/plain,*/*",
    }

    try:
        response = requests.get(url, headers=headers, timeout=45)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DataLoadError(
            f"Could not download WHO {dataset} data. {exc}"
        ) from exc

    text = response.content.decode("utf-8-sig", errors="replace")
    if not text.strip():
        raise DataLoadError(f"WHO {dataset} endpoint returned an empty file.")

    try:
        df = pd.read_csv(StringIO(text), low_memory=False)
    except Exception as exc:
        raise DataLoadError(
            f"WHO {dataset} file could not be parsed as CSV."
        ) from exc

    return _clean_columns(df)


def load_all_who_data() -> Dict[str, pd.DataFrame]:
    return {name: fetch_who_csv(name) for name in WHO_ENDPOINTS}


def find_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    lookup = {str(c).lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    return None


def country_column(df: pd.DataFrame) -> Optional[str]:
    return find_column(df, ["country", "location_name", "entity"])


def iso3_column(df: pd.DataFrame) -> Optional[str]:
    return find_column(df, ["iso3", "country_code", "iso_3"])


def year_column(df: pd.DataFrame) -> Optional[str]:
    return find_column(df, ["year"])


def list_countries(datasets: Dict[str, pd.DataFrame]) -> list[str]:
    names = set()
    for df in datasets.values():
        ccol = country_column(df)
        if ccol:
            names.update(
                str(v).strip()
                for v in df[ccol].dropna().unique()
                if str(v).strip()
            )
    return sorted(names)


def filter_country(df: pd.DataFrame, country: str) -> pd.DataFrame:
    ccol = country_column(df)
    if not ccol:
        return df.iloc[0:0].copy()
    mask = df[ccol].astype(str).str.strip().str.casefold() == country.casefold()
    return df.loc[mask].copy()


def available_years(*frames: pd.DataFrame) -> list[int]:
    year_sets = []
    for df in frames:
        ycol = year_column(df)
        if not ycol or df.empty:
            continue
        years = pd.to_numeric(df[ycol], errors="coerce").dropna().astype(int)
        year_sets.append(set(years.tolist()))
    if not year_sets:
        return []
    return sorted(set.union(*year_sets))


def numeric_value(row: pd.Series, candidates: Iterable[str]) -> Optional[float]:
    for col in candidates:
        if col in row.index:
            val = pd.to_numeric(pd.Series([row[col]]), errors="coerce").iloc[0]
            if pd.notna(val):
                return float(val)
    return None


def row_for_year(df: pd.DataFrame, year: int, fallback_to_latest_prior: bool = False) -> Tuple[Optional[pd.Series], Optional[int]]:
    if df.empty:
        return None, None
    ycol = year_column(df)
    if not ycol:
        return None, None

    years = pd.to_numeric(df[ycol], errors="coerce")
    exact = df.loc[years == year]
    if not exact.empty:
        return exact.iloc[0], year

    if fallback_to_latest_prior:
        eligible = df.loc[years <= year].copy()
        if not eligible.empty:
            eligible["_year_numeric"] = pd.to_numeric(
                eligible[ycol], errors="coerce"
            )
            eligible = eligible.sort_values("_year_numeric")
            row = eligible.iloc[-1]
            return row, int(row["_year_numeric"])

    return None, None


def incidence_metrics(row: Optional[pd.Series]) -> dict:
    if row is None:
        return {}
    return {
        "incidence": numeric_value(row, ["e_inc_num"]),
        "incidence_lo": numeric_value(row, ["e_inc_num_lo"]),
        "incidence_hi": numeric_value(row, ["e_inc_num_hi"]),
        "incidence_rate": numeric_value(row, ["e_inc_100k"]),
        "tb_mortality": numeric_value(row, ["e_mort_num"]),
        "tb_mortality_lo": numeric_value(row, ["e_mort_num_lo"]),
        "tb_mortality_hi": numeric_value(row, ["e_mort_num_hi"]),
        "tbhiv_incidence": numeric_value(row, ["e_inc_tbhiv_num"]),
        "tbhiv_incidence_lo": numeric_value(row, ["e_inc_tbhiv_num_lo"]),
        "tbhiv_incidence_hi": numeric_value(row, ["e_inc_tbhiv_num_hi"]),
        "tbhiv_mortality": numeric_value(row, ["e_mort_tbhiv_num"]),
        "tbhiv_mortality_lo": numeric_value(row, ["e_mort_tbhiv_num_lo"]),
        "tbhiv_mortality_hi": numeric_value(row, ["e_mort_tbhiv_num_hi"]),
        "population": numeric_value(row, ["e_pop_num"]),
        "cdr": numeric_value(row, ["c_cdr"]),
    }


def notification_metrics(row: Optional[pd.Series]) -> dict:
    if row is None:
        return {}

    notified = numeric_value(
        row,
        [
            "c_newinc",
            "newrel",
            "newrel_total",
            "newrel_notified",
        ],
    )

    return {
        "notified": notified,
        "pulmonary_bac_confirmed": numeric_value(
            row, ["new_labconf", "new_sp", "c_newlabconf"]
        ),
        "hiv_positive": numeric_value(
            row, ["newrel_hivpos", "c_newrel_hivpos"]
        ),
        "hiv_tested": numeric_value(row, ["newrel_hivtest"]),
        "boys_0_14": numeric_value(row, ["newrel_m014"]),
        "girls_0_14": numeric_value(row, ["newrel_f014"]),
        "men_15_plus": numeric_value(row, ["newrel_m15plus"]),
        "women_15_plus": numeric_value(row, ["newrel_f15plus"]),
    }


def outcome_metrics(row: Optional[pd.Series]) -> dict:
    if row is None:
        return {}

    cohort = numeric_value(row, ["newrel_coh", "c_newrel_coh"])
    success = numeric_value(row, ["newrel_succ", "c_newrel_succ"])
    died = numeric_value(row, ["newrel_died", "c_newrel_died"])
    failed = numeric_value(row, ["newrel_fail", "c_newrel_fail"])
    lost = numeric_value(
        row,
        [
            "newrel_lost",
            "newrel_ltfu",
            "c_newrel_lost",
            "c_newrel_ltfu",
        ],
    )
    not_evaluated = numeric_value(
        row, ["newrel_neval", "c_newrel_neval"]
    )

    # Some WHO exports contain a cohort and success but omit a residual field.
    known = [v for v in [success, died, failed, lost, not_evaluated] if v is not None]
    residual = None
    if cohort is not None and known:
        residual = max(cohort - sum(known), 0)

    return {
        "cohort": cohort,
        "success": success,
        "died": died,
        "failed": failed,
        "lost": lost,
        "not_evaluated": not_evaluated,
        "other_or_unclassified": residual,
    }


def tbhiv_outcome_metrics(row: Optional[pd.Series]) -> dict:
    """Return WHO treatment outcomes for the TB/HIV cohort."""
    if row is None:
        return {}

    cohort = numeric_value(row, ["tbhiv_coh"])
    success = numeric_value(row, ["tbhiv_succ"])
    died = numeric_value(row, ["tbhiv_died"])
    failed = numeric_value(row, ["tbhiv_fail"])
    lost = numeric_value(row, ["tbhiv_lost"])
    known = [v for v in [success, died, failed, lost] if v is not None]
    residual = max(cohort - sum(known), 0) if cohort is not None and known else None

    return {
        "cohort": cohort,
        "success": success,
        "died": died,
        "failed": failed,
        "lost": lost,
        "other_or_unclassified": residual,
    }


def build_country_year_table(
    estimates: pd.DataFrame,
    notifications: pd.DataFrame,
    outcomes: pd.DataFrame,
    country: str,
) -> pd.DataFrame:
    est = filter_country(estimates, country)
    notif = filter_country(notifications, country)
    out = filter_country(outcomes, country)

    years = available_years(est, notif, out)
    records = []

    for year in years:
        erow, _ = row_for_year(est, year)
        nrow, _ = row_for_year(notif, year)
        orow, _ = row_for_year(out, year)

        im = incidence_metrics(erow)
        nm = notification_metrics(nrow)
        om = outcome_metrics(orow)
        tbhiv_om = tbhiv_outcome_metrics(orow)
        age_sex_values = [
            nm.get("boys_0_14"), nm.get("girls_0_14"),
            nm.get("men_15_plus"), nm.get("women_15_plus"),
        ]
        age_sex_total = sum(age_sex_values) if all(value is not None for value in age_sex_values) else None
        children_notified = (
            nm.get("boys_0_14") + nm.get("girls_0_14")
            if nm.get("boys_0_14") is not None and nm.get("girls_0_14") is not None
            else None
        )

        incidence = im.get("incidence")
        notified = nm.get("notified")
        gap = None
        coverage = None
        if incidence is not None and notified is not None and incidence > 0:
            gap = max(incidence - notified, 0)
            coverage = 100 * notified / incidence

        cohort = om.get("cohort")
        success = om.get("success")
        tsr = (
            100 * success / cohort
            if cohort not in (None, 0) and success is not None
            else None
        )
        cohort_notification_difference = (
            cohort - notified
            if cohort is not None and notified is not None
            else None
        )
        cohort_notification_difference_pct = (
            100 * cohort_notification_difference / notified
            if notified not in (None, 0)
            and cohort_notification_difference is not None
            else None
        )

        records.append(
            {
                "year": year,
                "estimated_incidence": incidence,
                "estimated_incidence_low": im.get("incidence_lo"),
                "estimated_incidence_high": im.get("incidence_hi"),
                "estimated_tb_mortality": im.get("tb_mortality"),
                "estimated_tb_mortality_low": im.get("tb_mortality_lo"),
                "estimated_tb_mortality_high": im.get("tb_mortality_hi"),
                "estimated_tbhiv_incidence": im.get("tbhiv_incidence"),
                "estimated_tbhiv_incidence_low": im.get("tbhiv_incidence_lo"),
                "estimated_tbhiv_incidence_high": im.get("tbhiv_incidence_hi"),
                "estimated_tbhiv_mortality": im.get("tbhiv_mortality"),
                "estimated_tbhiv_mortality_low": im.get("tbhiv_mortality_lo"),
                "estimated_tbhiv_mortality_high": im.get("tbhiv_mortality_hi"),
                "notifications": notified,
                "hiv_tested": nm.get("hiv_tested"),
                "hiv_positive_notifications": nm.get("hiv_positive"),
                "hiv_testing_coverage_pct": (
                    100 * nm.get("hiv_tested") / notified
                    if notified not in (None, 0) and nm.get("hiv_tested") is not None
                    else None
                ),
                "hiv_positivity_among_tested_pct": (
                    100 * nm.get("hiv_positive") / nm.get("hiv_tested")
                    if nm.get("hiv_tested") not in (None, 0)
                    and nm.get("hiv_positive") is not None
                    else None
                ),
                "boys_0_14": nm.get("boys_0_14"),
                "girls_0_14": nm.get("girls_0_14"),
                "men_15_plus": nm.get("men_15_plus"),
                "women_15_plus": nm.get("women_15_plus"),
                "age_sex_reported_total": age_sex_total,
                "age_sex_reporting_coverage_pct": (
                    100 * age_sex_total / notified
                    if age_sex_total is not None and notified not in (None, 0)
                    else None
                ),
                "children_notification_share_pct": (
                    100 * children_notified / age_sex_total
                    if children_notified is not None and age_sex_total not in (None, 0)
                    else None
                ),
                "adult_male_to_female_ratio": (
                    nm.get("men_15_plus") / nm.get("women_15_plus")
                    if nm.get("men_15_plus") is not None and nm.get("women_15_plus") not in (None, 0)
                    else None
                ),
                "notification_gap": gap,
                "notification_coverage_pct": coverage,
                "treatment_cohort": cohort,
                "cohort_notification_difference": cohort_notification_difference,
                "cohort_notification_difference_pct": cohort_notification_difference_pct,
                "treatment_success": success,
                "treatment_success_pct": tsr,
                "died": om.get("died"),
                "failed": om.get("failed"),
                "lost_to_follow_up": om.get("lost"),
                "not_evaluated": om.get("not_evaluated"),
                "other_or_unclassified": om.get("other_or_unclassified"),
                "tbhiv_treatment_cohort": tbhiv_om.get("cohort"),
                "tbhiv_treatment_success": tbhiv_om.get("success"),
                "tbhiv_died": tbhiv_om.get("died"),
                "tbhiv_failed": tbhiv_om.get("failed"),
                "tbhiv_lost_to_follow_up": tbhiv_om.get("lost"),
                "tbhiv_other_or_unclassified": tbhiv_om.get("other_or_unclassified"),
            }
        )

    return pd.DataFrame(records)
