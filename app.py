from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from charts import cascade_sankey, coverage_chart, outcome_bar, trend_chart
from data import (
    WHO_DATA_PAGE,
    DataLoadError,
    available_years,
    build_country_year_table,
    filter_country,
    incidence_metrics,
    list_countries,
    load_all_who_data,
    notification_metrics,
    outcome_metrics,
    row_for_year,
)


st.set_page_config(
    page_title="Kenya TB Care Cascade Explorer",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> None:
    with open("assets/styles.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def fmt_int(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):,.0f}"


def fmt_pct(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.1f}%"


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


load_css()

st.markdown(
    """
    <div class="eyebrow">PUBLIC HEALTH ANALYTICS | WAYNE WILLIS OMONDI</div>
    <h1>Kenya TB Care Cascade Explorer</h1>
    <p class="hero-copy">
      Tracking the path from estimated tuberculosis burden to notification,
      treatment and treatment outcomes.
    </p>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Data controls")
    st.caption("WHO Global TB Database")

try:
    with st.spinner("Loading current WHO tuberculosis datasets…"):
        datasets = load_all_who_data()
except DataLoadError as exc:
    st.error(
        "The app could not retrieve the WHO CSV files. "
        "No substitute values have been inserted."
    )
    st.code(str(exc))
    st.info(
        "Check the network connection or WHO endpoint availability, then rerun the app."
    )
    st.stop()

EAST_AFRICAN_COUNTRIES = [
    "Burundi",
    "Democratic Republic of the Congo",
    "Kenya",
    "Rwanda",
    "Somalia",
    "South Sudan",
    "Tanzania",
    "Uganda",
]

all_countries = list_countries(datasets)

countries = [country for country in EAST_AFRICAN_COUNTRIES if country in all_countries]

default_country = "Kenya" if "Kenya" in countries else (countries[0] if countries else None)

if not default_country:
    st.error("No country names were found in the WHO files.")
    st.stop()

with st.sidebar:
    country = st.selectbox(
        "Country",
        countries,
        index=countries.index(default_country),
    )

country_est = filter_country(datasets["estimates"], country)
country_notif = filter_country(datasets["notifications"], country)
country_out = filter_country(datasets["outcomes"], country)

years = available_years(country_est, country_notif)
if not years:
    st.error(f"No usable annual data were found for {country}.")
    st.stop()

with st.sidebar:
    selected_year = st.selectbox(
        "Reporting year",
        sorted(years, reverse=True),
        index=0,
    )

est_row, est_year = row_for_year(country_est, selected_year)
notif_row, notif_year = row_for_year(country_notif, selected_year)
out_row, outcome_year = row_for_year(
    country_out, selected_year, fallback_to_latest_prior=True
)

im = incidence_metrics(est_row)
nm = notification_metrics(notif_row)
om = outcome_metrics(out_row)

incidence = im.get("incidence")
notified = nm.get("notified")

if incidence is None or notified is None:
    st.warning(
        f"The selected year ({selected_year}) does not contain both estimated incidence "
        "and notification counts. Try another year."
    )
    st.stop()

notification_gap = max(incidence - notified, 0)
notification_coverage = 100 * notified / incidence if incidence else None

cohort = om.get("cohort")
success = om.get("success")
treatment_success_pct = (
    100 * success / cohort
    if cohort not in (None, 0) and success is not None
    else None
)

sankey_values = dict(
        incidence=incidence,
        notified=notified,
        cohort=cohort,
        success=success,
        died=om.get("died"),
        failed=om.get("failed"),
        lost=om.get("lost"),
        not_evaluated=om.get("not_evaluated"),
    )

if country != "Kenya":
    st.info(
        "The app is branded around Kenya, but the WHO data controls allow country comparison."
    )

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card(
        "Estimated TB incidence",
        fmt_int(incidence),
        f"WHO estimate · {selected_year}",
    )
with c2:
    shown_notified = sankey_values["notified"] 
    metric_card(
        "Notified cases",
        fmt_int(shown_notified),
        f"Reported · {selected_year}",
    )
with c3:
    shown_coverage = (
        100 * shown_notified / incidence if incidence else None
    )
    metric_card(
        "Notification coverage",
        fmt_pct(shown_coverage),
        "Notifications ÷ estimated incidence",
    )
with c4:
    shown_success = (
        100 * sankey_values["success"] / sankey_values["cohort"]
        if sankey_values["cohort"]
        else None
    )
    metric_card(
        "Treatment success",
        fmt_pct(shown_success),
        (
         f"WHO treatment cohort · {outcome_year or 'N/A'}"
        ),
    )

tabs = st.tabs(
    ["Care cascade", "Historical trends", "Treatment outcomes", "About the data"]
)

with tabs[0]:
    st.markdown("## From TB burden to treatment outcomes")
    st.caption(
        f"{country}, {selected_year}. "
        + (
            f"Treatment outcomes use the latest available cohort at or before "
            f"{selected_year}: {outcome_year}."
            if outcome_year and outcome_year != selected_year
            else f"Treatment outcome cohort: {outcome_year or 'not available'}."
        )
    )

    fig = cascade_sankey(
        outcome_year=outcome_year,
        **sankey_values,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
            f"""
            <div class="interpretation">
              <div class="interpretation-title">What this view says</div>
              <p>
                WHO estimates <b>{fmt_int(incidence)}</b> people developed TB in
                {country} in {selected_year}, while <b>{fmt_int(notified)}</b>
                new and relapse cases were notified. The arithmetic difference,
                <b>{fmt_int(notification_gap)}</b>, is shown as a notification gap.
                It should not be interpreted as a direct count of undiagnosed people.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tabs[1]:
    history = build_country_year_table(
        datasets["estimates"],
        datasets["notifications"],
        datasets["outcomes"],
        country,
    )
    st.markdown("## Historical trends")
    st.caption(
        "WHO re-estimates historical TB burden when methods or evidence change. "
        "Use the latest time series as a coherent series rather than mixing releases."
    )
    st.plotly_chart(
        trend_chart(history),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    st.plotly_chart(
        coverage_chart(history),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    export_cols = [
        "year",
        "estimated_incidence",
        "notifications",
        "notification_gap",
        "notification_coverage_pct",
        "treatment_cohort",
        "treatment_success",
        "treatment_success_pct",
        "died",
        "failed",
        "lost_to_follow_up",
        "not_evaluated",
    ]
    downloadable = history[export_cols].sort_values("year")
    st.download_button(
        "Download country time series (.csv)",
        downloadable.to_csv(index=False).encode("utf-8"),
        file_name=f"{country.lower().replace(' ', '_')}_tb_cascade_timeseries.csv",
        mime="text/csv",
    )

with tabs[2]:
    st.markdown("## Treatment outcomes")
    if cohort is None:
        st.info("No compatible new-and-relapse treatment cohort was available.")
    else:
        oc1, oc2 = st.columns([1.6, 1])
        with oc1:
            st.plotly_chart(
                outcome_bar(om, outcome_year),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with oc2:
            st.markdown(
                f"""
                <div class="outcome-summary">
                  <div class="metric-label">Treatment cohort</div>
                  <div class="big-number">{fmt_int(cohort)}</div>
                  <div class="metric-note">Cohort year {outcome_year}</div>
                  <hr>
                  <div class="summary-row"><span>Successful</span><b>{fmt_int(success)}</b></div>
                  <div class="summary-row"><span>Died</span><b>{fmt_int(om.get("died"))}</b></div>
                  <div class="summary-row"><span>Failed</span><b>{fmt_int(om.get("failed"))}</b></div>
                  <div class="summary-row"><span>Lost to follow-up</span><b>{fmt_int(om.get("lost"))}</b></div>
                  <div class="summary-row"><span>Not evaluated</span><b>{fmt_int(om.get("not_evaluated"))}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

with tabs[3]:
    st.markdown("## Executive summary")
    st.write(
        f"""
        The {country} TB Care Cascade Explorer examines how estimated tuberculosis
        burden relates to case notification and treatment outcomes. The application
        combines WHO modelled burden estimates with country-reported surveillance
        data and presents them as an interactive care cascade and historical time series.

        The Sankey view is designed to make losses between stages visible while keeping
        modelled estimates separate from reported programme counts. Treatment outcomes
        are linked to their own cohort year because these data may become available later
        than incidence and notification data.
        """
    )

    st.markdown("### Definitions and interpretation")
    st.markdown(
        """
        - **Estimated incidence** is a WHO modelled estimate of the number of people
          developing TB during the year.
        - **Notified cases** are new and relapse TB cases diagnosed and officially
          reported to national authorities.
        - **Notification gap** is calculated here as estimated incidence minus notified
          cases. It is an analytical gap, not a direct enumeration of undiagnosed people.
        - **Treatment success** uses the WHO new-and-relapse treatment cohort where
          available.
        """
    )

    st.markdown("### Data provenance")
    st.code(
        "\n".join(
            [
                "WHO TB burden estimates:",
                "  https://extranet.who.int/tme/generateCSV.asp?ds=estimates",
                "WHO case notifications:",
                "  https://extranet.who.int/tme/generateCSV.asp?ds=notifications",
                "WHO treatment outcomes:",
                "  https://extranet.who.int/tme/generateCSV.asp?ds=outcomes",
            ]
        ),
        language=None,
    )
    st.markdown(f"[WHO tuberculosis data page]({WHO_DATA_PAGE})")

    st.markdown("### Refresh behaviour")
    st.write(
        "The application downloads WHO CSV files at runtime and caches them for six "
        "hours. Restarting the app or clearing Streamlit's cache forces a fresh retrieval of the data."
    )

st.markdown(
    f"""
    <div class="footer">
      Data source: WHO Global TB Database · App retrieval time:
      {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    </div>
    """,
    unsafe_allow_html=True,
)
