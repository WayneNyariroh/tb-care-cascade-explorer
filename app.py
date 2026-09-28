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
    initial_sidebar_state="collapsed",
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


def cascade_detail_table(
    title: str,
    period: str,
    sections: list[tuple[str, list[tuple[str, str, str, str]]]],
    note: str = "",
) -> None:
    body_parts = []
    for section, rows in sections:
        body_parts.append(
            f"<tr class='detail-section'><th colspan='4'>{section}</th></tr>"
        )
        body_parts.extend(
            "<tr>"
            f"<th scope='row'>{label}</th>"
            f"<td>{value}</td><td>{share}</td><td>{denominator}</td>"
            "</tr>"
            for label, value, share, denominator in rows
        )
    body = "".join(body_parts)
    note_html = f"<p class='detail-note'>{note}</p>" if note else ""
    st.markdown(
        f"""
        <div class="detail-table-card">
          <div class="detail-table-heading">
            <div>{title}</div><span>{period}</span>
          </div>
          <div class="detail-table-scroll">
            <table class="detail-table">
              <thead>
                <tr><th>Stage or outcome</th><th>People</th><th>Share</th><th>Denominator</th></tr>
              </thead>
              <tbody>{body}</tbody>
            </table>
          </div>
          {note_html}
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

current_year = datetime.now(timezone.utc).year
estimate_years = set(available_years(country_est))
notification_years = set(available_years(country_notif))
outcome_years = set(available_years(country_out))

years = []
for year in sorted(estimate_years & notification_years & outcome_years):
    if not 2015 <= year <= current_year:
        continue
    candidate_est, _ = row_for_year(country_est, year)
    candidate_notif, _ = row_for_year(country_notif, year)
    candidate_out, _ = row_for_year(country_out, year)
    if (
        incidence_metrics(candidate_est).get("incidence") is not None
        and notification_metrics(candidate_notif).get("notified") is not None
        and outcome_metrics(candidate_out).get("cohort") is not None
    ):
        years.append(year)

if not years:
    st.error(
        f"No complete cascade cohort from 2015 through {current_year} was found for {country}."
    )
    st.stop()

reporting_years = [
    year
    for year in sorted(estimate_years & notification_years)
    if 2015 <= year <= current_year
]
latest_reporting_year = max(reporting_years) if reporting_years else None
latest_complete_cohort_year = max(years)

with st.sidebar:
    selected_year = st.selectbox(
        "Treatment cohort enrollment year",
        sorted(years, reverse=True),
        index=0,
    )
    if latest_reporting_year and latest_reporting_year > latest_complete_cohort_year:
        st.caption(
            f"Burden and notifications extend to {latest_reporting_year}. "
            f"The latest complete outcome cohort is {latest_complete_cohort_year}."
        )

est_row, est_year = row_for_year(country_est, selected_year)
notif_row, notif_year = row_for_year(country_notif, selected_year)
out_row, outcome_year = row_for_year(country_out, selected_year)

im = incidence_metrics(est_row)
nm = notification_metrics(notif_row)
om = outcome_metrics(out_row)

incidence = im.get("incidence")
notified = nm.get("notified")
cohort = om.get("cohort")
success = om.get("success")

if incidence is None or notified is None:
    st.warning(
        f"The selected year ({selected_year}) does not contain both estimated incidence "
        "and notification counts. Try another year."
    )
    st.stop()

if cohort is None:
    st.warning(
        f"The selected cohort year ({selected_year}) does not contain a treatment cohort. "
        "Try another year."
    )
    st.stop()

notification_gap = max(incidence - notified, 0)
notification_coverage = 100 * notified / incidence if incidence else None

treatment_success_pct = (
    100 * success / cohort
    if cohort not in (None, 0) and success is not None
    else None
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
    metric_card(
        "Notified cases",
        fmt_int(notified),
        f"Reported · {selected_year}",
    )
with c3:
    metric_card(
        "Notification coverage",
        fmt_pct(notification_coverage),
        "Notifications ÷ estimated incidence",
    )
with c4:
    metric_card(
        "Treatment success",
        fmt_pct(treatment_success_pct),
        (
         f"WHO treatment cohort · {outcome_year or 'N/A'}"
        ),
    )

tabs = st.tabs(
    ["Cascade", "Trends", "Outcomes", "Data notes"]
)

with tabs[0]:
    st.markdown(f"## {selected_year} TB care cascade — cohort aligned")
    st.caption(
        f"{country}. Incidence and notification describe calendar year {selected_year}. "
        f"Treatment outcomes relate to people enrolled in the {selected_year} cohort "
        "and were observed later. These are aligned aggregates, not person-linked records."
    )

    st.markdown(
        """
        <div class="cascade-stage-rail" aria-label="Cascade stages">
          <div><span>01</span>Burden</div>
          <div><span>02</span>Notification</div>
          <div><span>03</span><span class="stage-long">Outcome cohort</span><span class="stage-short">Cohort</span></div>
          <div><span>04</span><span class="stage-long">Treatment outcomes</span><span class="stage-short">Outcomes</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        cascade_sankey(
            incidence=incidence,
            notified=notified,
            outcome_metrics=om,
            cohort_year=selected_year,
        ),
        width="stretch",
        config={"displayModeBar": False},
        key="cascade_sankey_desktop",
    )
    st.plotly_chart(
        cascade_sankey(
            incidence=incidence,
            notified=notified,
            outcome_metrics=om,
            cohort_year=selected_year,
            compact=True,
        ),
        width="stretch",
        config={"displayModeBar": False},
        key="cascade_sankey_mobile",
    )

    gap_pct = 100 * notification_gap / incidence if incidence else None
    notification_cohort_difference = notified - cohort
    reconciliation_value = abs(notification_cohort_difference)
    reconciliation_pct = 100 * reconciliation_value / notified if notified else None
    if notification_cohort_difference >= 0:
        reconciliation_label = "Not included in outcome-cohort aggregate"
    else:
        reconciliation_label = "Additional records in outcome-cohort aggregate"

    incidence_range = ""
    if im.get("incidence_lo") is not None and im.get("incidence_hi") is not None:
        incidence_range = (
            f"WHO-reported uncertainty range: {fmt_int(im.get('incidence_lo'))}–"
            f"{fmt_int(im.get('incidence_hi'))}."
        )

    outcome_rows = []
    for label, key in [
        ("Treatment success", "success"),
        ("Died", "died"),
        ("Lost to follow-up", "lost"),
        ("Treatment failed", "failed"),
        ("Not evaluated", "not_evaluated"),
        ("Residual / not separately classified", "other_or_unclassified"),
    ]:
        value = om.get(key)
        if value is None or value <= 0:
            continue
        share = 100 * value / cohort if cohort else None
        outcome_rows.append((label, fmt_int(value), fmt_pct(share), "Outcome cohort"))

    cascade_detail_table(
        "Cascade detail",
        f"Cohort {selected_year}",
        [
            (
                "Burden and notification",
                [
                    ("Estimated incidence", fmt_int(incidence), "100.0%", "Incidence point estimate"),
                    ("Notified cases", fmt_int(notified), fmt_pct(notification_coverage), "Incidence point estimate"),
                    ("Estimated notification gap", fmt_int(notification_gap), fmt_pct(gap_pct), "Incidence point estimate"),
                ],
            ),
            (
                "Cohort reconciliation",
                [
                    ("Outcome cohort", fmt_int(cohort), "100.0%", "Outcome cohort"),
                    (reconciliation_label, fmt_int(reconciliation_value), fmt_pct(reconciliation_pct), "Notifications"),
                ],
            ),
            ("Treatment outcomes", outcome_rows),
        ],
        (
            f"{incidence_range} The notification–cohort difference reconciles two "
            "aggregate definitions; it is not a treatment outcome. Residual is the "
            "cohort total minus the outcome categories separately reported in the export."
        ),
    )

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
                Of the notifications, <b>{fmt_int(cohort)}</b> are represented in the
                new-and-recurrent outcome cohort. The <b>{fmt_int(reconciliation_value)}</b>
                difference is an aggregate reconciliation item—not evidence that those
                people were untreated. Only the outcome cohort feeds the treatment outcomes.
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
        "Use the latest time series as a coherent series rather than mixing releases. "
        f"Burden and notification data extend to {latest_reporting_year or 'the latest available year'}; "
        f"the latest complete treatment-outcome cohort is {latest_complete_cohort_year}."
    )
    st.plotly_chart(
        trend_chart(history),
        width="stretch",
        config={"displayModeBar": False},
        key="trend_chart",
    )
    st.plotly_chart(
        coverage_chart(history),
        width="stretch",
        config={"displayModeBar": False},
        key="coverage_chart",
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
        "other_or_unclassified",
    ]
    downloadable = history.reindex(columns=export_cols).sort_values("year")
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
                width="stretch",
                config={"displayModeBar": False},
                key="outcomes_tab_chart",
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
                  <div class="summary-row"><span>Residual / unclassified</span><b>{fmt_int(om.get("other_or_unclassified"))}</b></div>
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

        The cascade aligns modelled burden, notifications and the treatment cohort to the
        same enrollment year. Treatment outcomes occur later but remain attributed to the
        year in which the cohort was enrolled. The selector therefore includes only years
        with a complete outcome cohort; newer burden and notification data remain visible
        in Trends.
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
        - **Notification–cohort reconciliation** is the difference between the notification
          aggregate and the outcome-cohort aggregate. It is not labelled as untreated.
        - **Residual / not separately classified** is calculated as the outcome cohort minus
          the outcome categories separately reported in the WHO export.
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
