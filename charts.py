from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go


BLUE = "#1558D6"
BLUE_LIGHT = "#A8C7FA"
GREEN = "#146C2E"
GREEN_LIGHT = "#C4EED0"
AMBER = "#EAA937"
ORANGE = "#D85900"
RED = "#C0151D"
PURPLE = "#681DA8"
GREY = "#9AA0A6"
GREY_LIGHT = "#DADCE0"
INK = "#172033"


def _fmt(value: Optional[float]) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{value:,.0f}"


def cascade_sankey(
    incidence: float,
    notified: float,
    outcome_metrics: dict,
    cohort_year: Optional[int],
    compact: bool = False,
) -> go.Figure:
    incidence = max(float(incidence or 0), 0)
    notified = max(float(notified or 0), 0)
    cohort = max(float(outcome_metrics.get("cohort") or 0), 0)
    notification_gap = max(incidence - notified, 0)
    notification_excess = max(notified - incidence, 0)

    outcomes = [
        ("Treatment success", "success", GREEN, "rgba(20,108,46,0.34)"),
        ("Died", "died", ORANGE, "rgba(216,89,0,0.30)"),
        ("Lost to follow-up", "lost", AMBER, "rgba(234,169,55,0.34)"),
        ("Treatment failed", "failed", RED, "rgba(192,21,29,0.28)"),
        ("Not evaluated", "not_evaluated", PURPLE, "rgba(104,29,168,0.26)"),
        (
            "Residual / unclassified",
            "other_or_unclassified",
            "#7C8799",
            "rgba(124,135,153,0.28)",
        ),
    ]
    outcomes = [
        (label, max(float(outcome_metrics.get(key) or 0), 0), color, link_color)
        for label, key, color, link_color in outcomes
        if outcome_metrics.get(key) is not None
        and float(outcome_metrics.get(key) or 0) > 0
    ]

    labels = [
        f"{'Incidence' if compact else 'Estimated incidence'}<br><b>{_fmt(incidence)}</b>",
        f"{'Notified' if compact else 'Notified cases'}<br><b>{_fmt(notified)}</b>",
        f"{'Cohort' if compact else 'Outcome cohort'}<br><b>{_fmt(cohort)}</b>",
    ]
    node_colors = [BLUE, "#2E7D6E", PURPLE]
    node_x = [0.04, 0.30, 0.55]
    node_y = [0.08, 0.08, 0.08]
    node_customdata = [
        "WHO modelled incidence point estimate",
        "New, recurrent and unknown previous-treatment-history cases reported",
        "New-and-recurrent cohort included in treatment-outcome reporting",
    ]

    sources: list[int] = []
    targets: list[int] = []
    values: list[float] = []
    link_colors: list[str] = []
    link_customdata: list[str] = []

    if notification_excess > 0:
        excess_index = len(labels)
        labels.append(
            ("Above est.<br>" if compact else "Notifications above<br>incidence estimate<br>")
            + f"<b>{_fmt(notification_excess)}</b>"
        )
        node_colors.append("#CBD1D9")
        node_x.append(0.04)
        node_y.append(0.74 if compact else 0.70)
        node_customdata.append(
            "Reported notifications exceed the WHO incidence point estimate; "
            "a reconciliation item, not a patient group"
        )
        sources.extend([0, excess_index])
        targets.extend([1, 1])
        values.extend([incidence, notification_excess])
        link_colors.extend(["rgba(46,125,110,0.32)", "rgba(180,187,197,0.30)"])
        link_customdata.extend(
            ["WHO incidence point estimate", "Notifications above incidence point estimate"]
        )
    else:
        sources.append(0)
        targets.append(1)
        values.append(notified)
        link_colors.append("rgba(46,125,110,0.32)")
        link_customdata.append("Reported notifications")
        if notification_gap > 0:
            gap_index = len(labels)
            labels.append(
                ("Est. gap<br>" if compact else "Estimated notification gap<br>")
                + f"<b>{_fmt(notification_gap)}</b>"
            )
            node_colors.append("#CBD1D9")
            node_x.append(0.30)
            node_y.append(0.72 if compact else 0.68)
            node_customdata.append(
                "Incidence point estimate minus notifications; not a counted outcome"
            )
            sources.append(0)
            targets.append(gap_index)
            values.append(notification_gap)
            link_colors.append("rgba(180,187,197,0.28)")
            link_customdata.append("Estimated notification gap")

    if notified >= cohort:
        reconciliation = notified - cohort
        sources.append(1)
        targets.append(2)
        values.append(cohort)
        link_colors.append("rgba(104,29,168,0.28)")
        link_customdata.append("Included in outcome cohort")
        if reconciliation > 0:
            reconciliation_index = len(labels)
            labels.append(
                ("Recon.<br>" if compact else "Notification–cohort<br>reconciliation<br>")
                + f"<b>{_fmt(reconciliation)}</b>"
            )
            node_colors.append("#E7E9ED")
            node_x.append(0.55)
            node_y.append(0.79 if compact else 0.74)
            node_customdata.append(
                "Aggregate definition and reporting difference; not a treatment outcome"
            )
            sources.append(1)
            targets.append(reconciliation_index)
            values.append(reconciliation)
            link_colors.append("rgba(190,195,203,0.30)")
            link_customdata.append("Notification–cohort reconciliation")
    else:
        reconciliation = cohort - notified
        reconciliation_index = len(labels)
        labels.append(
            ("Recon.<br>" if compact else "Additional cohort<br>reconciliation<br>")
            + f"<b>{_fmt(reconciliation)}</b>"
        )
        node_colors.append("#E7E9ED")
        node_x.append(0.30)
        node_y.append(0.79 if compact else 0.74)
        node_customdata.append(
            "Outcome cohort exceeds the notification aggregate; not a treatment outcome"
        )
        sources.extend([1, reconciliation_index])
        targets.extend([2, 2])
        values.extend([notified, reconciliation])
        link_colors.extend(["rgba(104,29,168,0.28)", "rgba(190,195,203,0.30)"])
        link_customdata.extend(
            ["Reported notifications", "Additional cohort reconciliation"]
        )

    outcome_y = (
        [0.03, 0.53, 0.64, 0.74, 0.82, 0.87]
        if compact
        else [0.03, 0.50, 0.61, 0.71, 0.79, 0.84]
    )
    for index, (label, value, color, link_color) in enumerate(outcomes):
        outcome_index = len(labels)
        share = 100 * value / cohort if cohort else 0
        compact_label = {
            "Treatment success": "Success",
            "Lost to follow-up": "Lost",
            "Treatment failed": "Failed",
            "Residual / unclassified": "Residual",
        }.get(label, label)
        shown_label = compact_label if compact else label
        labels.append(f"{shown_label}<br><b>{_fmt(value)} · {share:.1f}%</b>")
        node_colors.append(color)
        node_x.append(0.91 if compact else 0.96)
        node_y.append(outcome_y[min(index, len(outcome_y) - 1)])
        node_customdata.append(f"{share:.1f}% of the outcome cohort")
        sources.append(2)
        targets.append(outcome_index)
        values.append(value)
        link_colors.append(link_color)
        link_customdata.append(label)

    fig = go.Figure(
        go.Sankey(
            arrangement="fixed",
            valueformat=",.0f",
            node=dict(
                pad=20,
                thickness=20,
                line=dict(color="rgba(255,255,255,0.92)", width=1),
                label=labels,
                color=node_colors,
                x=node_x,
                y=node_y,
                customdata=node_customdata,
                hovertemplate=(
                    "<b>%{label}</b><br>%{customdata}<extra></extra>"
                ),
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                customdata=link_customdata,
                hovertemplate=(
                    "%{source.label} → %{target.label}"
                    "<br><b>%{value:,.0f}</b><br>%{customdata}<extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(
        font=dict(size=9 if compact else 11, color=INK),
        margin=(
            dict(l=12, r=24, t=28, b=24)
            if compact
            else dict(l=34, r=18, t=28, b=32)
        ),
        height=540 if compact else 560,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig
def trend_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year"]).copy()
    frame = frame.dropna(
        subset=["estimated_incidence", "notifications"], how="all"
    )

    fig = go.Figure()
    has_bounds = (
        {"estimated_incidence_low", "estimated_incidence_high"}
        <= set(frame.columns)
        and frame[["estimated_incidence_low", "estimated_incidence_high"]]
        .notna()
        .any(axis=None)
    )
    if has_bounds:
        fig.add_trace(
            go.Scatter(
                x=frame["year"],
                y=frame["estimated_incidence_low"],
                mode="lines",
                line=dict(color="rgba(21,88,214,0)", width=0),
                showlegend=False,
                hoverinfo="skip",
                name="Incidence lower bound",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=frame["year"],
                y=frame["estimated_incidence_high"],
                mode="lines",
                line=dict(color="rgba(21,88,214,0)", width=0),
                fill="tonexty",
                fillcolor="rgba(21,88,214,0.14)",
                name="WHO uncertainty range",
                hoverinfo="skip",
            )
        )

    bounds = list(
        zip(
            frame.get(
                "estimated_incidence_low",
                pd.Series(index=frame.index, dtype=float),
            ),
            frame.get(
                "estimated_incidence_high",
                pd.Series(index=frame.index, dtype=float),
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["year"],
            y=frame["estimated_incidence"],
            mode="lines+markers",
            name="Estimated incidence",
            line=dict(color=BLUE, width=3),
            marker=dict(size=6),
            customdata=bounds,
            hovertemplate=(
                "%{x}<br>Estimated incidence: %{y:,.0f}"
                "<br>WHO range: %{customdata[0]:,.0f}–%{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["year"],
            y=frame["notifications"],
            mode="lines+markers",
            name="Notifications",
            line=dict(color=GREEN, width=3),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Notifications: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Estimated incidence and notified cases",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0),
        margin=dict(l=15, r=15, t=80, b=20),
        height=430,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="People", gridcolor="#E8ECF2", zeroline=False),
        font=dict(color=INK),
    )
    return fig

def cohort_reconciliation_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(
        subset=["year", "notifications", "treatment_cohort"]
    ).copy()
    if "cohort_notification_difference" not in frame.columns:
        frame["cohort_notification_difference"] = (
            frame["treatment_cohort"] - frame["notifications"]
        )
    if "cohort_notification_difference_pct" not in frame.columns:
        frame["cohort_notification_difference_pct"] = (
            100
            * frame["cohort_notification_difference"]
            / frame["notifications"].replace(0, pd.NA)
        )

    differences = frame["cohort_notification_difference"]
    colors = [
        PURPLE if value > 0 else "#A9B1BD" if value < 0 else GREY_LIGHT
        for value in differences
    ]
    customdata = list(
        zip(
            frame["notifications"],
            frame["treatment_cohort"],
            frame["cohort_notification_difference_pct"],
        )
    )
    fig = go.Figure(
        go.Bar(
            x=frame["year"],
            y=differences,
            marker=dict(color=colors),
            text=[
                f"{value:+,.0f}" if value != 0 else "0"
                for value in differences
            ],
            textposition="outside",
            cliponaxis=False,
            customdata=customdata,
            hovertemplate=(
                "%{x}<br>Notifications: %{customdata[0]:,.0f}"
                "<br>Outcome cohort: %{customdata[1]:,.0f}"
                "<br>Difference: %{y:+,.0f}"
                "<br>Share of notifications: %{customdata[2]:+.1f}%"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Outcome cohort minus notifications",
        margin=dict(l=15, r=15, t=65, b=20),
        height=390,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False, dtick=1),
        yaxis=dict(
            title="People (signed difference)",
            gridcolor="#E8ECF2",
            zeroline=True,
            zerolinecolor="#697386",
            zerolinewidth=1.5,
        ),
        font=dict(color=INK),
        showlegend=False,
    )
    return fig


def mortality_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "estimated_tb_mortality"]).copy()
    has_bounds = (
        {"estimated_tb_mortality_low", "estimated_tb_mortality_high"}
        <= set(frame.columns)
        and frame[["estimated_tb_mortality_low", "estimated_tb_mortality_high"]]
        .notna()
        .any(axis=None)
    )

    fig = go.Figure()
    if has_bounds:
        fig.add_trace(
            go.Scatter(
                x=frame["year"],
                y=frame["estimated_tb_mortality_low"],
                mode="lines",
                line=dict(color="rgba(216,89,0,0)", width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=frame["year"],
                y=frame["estimated_tb_mortality_high"],
                mode="lines",
                line=dict(color="rgba(216,89,0,0)", width=0),
                fill="tonexty",
                fillcolor="rgba(216,89,0,0.14)",
                name="WHO uncertainty range",
                hoverinfo="skip",
            )
        )

    bounds = list(
        zip(
            frame.get(
                "estimated_tb_mortality_low",
                pd.Series(index=frame.index, dtype=float),
            ),
            frame.get(
                "estimated_tb_mortality_high",
                pd.Series(index=frame.index, dtype=float),
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["year"],
            y=frame["estimated_tb_mortality"],
            mode="lines+markers",
            name="Estimated TB mortality",
            line=dict(color=ORANGE, width=3),
            marker=dict(size=6),
            customdata=bounds,
            hovertemplate=(
                "%{x}<br>Estimated TB mortality: %{y:,.0f}"
                "<br>WHO range: %{customdata[0]:,.0f}–%{customdata[1]:,.0f}"
                "<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Estimated TB mortality (HIV-negative people)",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0),
        margin=dict(l=15, r=15, t=80, b=20),
        height=400,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="People", gridcolor="#E8ECF2", zeroline=False),
        font=dict(color=INK),
    )
    return fig


def tbhiv_burden_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "estimated_tbhiv_incidence"]).copy()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["year"], y=frame["estimated_tbhiv_incidence_low"], mode="lines",
            line=dict(color="rgba(21,88,214,0)", width=0), showlegend=False, hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["year"], y=frame["estimated_tbhiv_incidence_high"], mode="lines",
            line=dict(color="rgba(21,88,214,0)", width=0), fill="tonexty",
            fillcolor="rgba(21,88,214,0.14)", name="WHO uncertainty range", hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=frame["year"], y=frame["estimated_tbhiv_incidence"], mode="lines+markers",
            name="Estimated TB incidence among people living with HIV",
            line=dict(color=BLUE, width=3), marker=dict(size=6),
            customdata=list(zip(frame["estimated_tbhiv_incidence_low"], frame["estimated_tbhiv_incidence_high"])),
            hovertemplate="%{x}<br>Estimated TB/HIV incidence: %{y:,.0f}<br>WHO range: %{customdata[0]:,.0f}–%{customdata[1]:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(
            text="Estimated TB incidence among people living with HIV",
            x=0,
            xanchor="left",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h", x=0, xanchor="left", y=1.12, yanchor="bottom"
        ),
        margin=dict(l=15, r=15, t=150, b=20),
        height=440, paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False), yaxis=dict(title="People", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK),
    )
    return fig


def tbhiv_care_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year"]).copy()
    fig = go.Figure()
    for column, label, color, hover in [
        ("hiv_testing_coverage_pct", "HIV testing coverage among notified TB cases", "#2E7D6E", "HIV testing coverage"),
        ("hiv_positivity_among_tested_pct", "HIV positivity among tested TB cases", PURPLE, "HIV positivity among tested"),
    ]:
        subset = frame.dropna(subset=[column])
        fig.add_trace(go.Scatter(
            x=subset["year"], y=subset[column], mode="lines+markers", name=label,
            line=dict(color=color, width=3), marker=dict(size=6),
            hovertemplate=f"%{{x}}<br>{hover}: %{{y:.1f}}%<extra></extra>",
        ))
    fig.update_layout(
        title=dict(
            text="HIV testing and positivity among notified TB cases",
            x=0,
            xanchor="left",
        ),
        hovermode="x unified",
        # Both charts in this pair use the same title and legend band.
        legend=dict(
            orientation="h", x=0, xanchor="left", y=1.12, yanchor="bottom"
        ),
        margin=dict(l=15, r=15, t=150, b=20),
        height=440, paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False), yaxis=dict(title="Percent", range=[0, 100], ticksuffix="%", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK),
    )
    return fig


def tbhiv_mortality_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "estimated_tbhiv_mortality"]).copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame["year"], y=frame["estimated_tbhiv_mortality_low"], mode="lines", line=dict(color="rgba(104,29,168,0)", width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=frame["year"], y=frame["estimated_tbhiv_mortality_high"], mode="lines", line=dict(color="rgba(104,29,168,0)", width=0), fill="tonexty", fillcolor="rgba(104,29,168,0.14)", name="WHO uncertainty range", hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=frame["year"], y=frame["estimated_tbhiv_mortality"], mode="lines+markers", name="Estimated TB mortality among people living with HIV",
        line=dict(color=PURPLE, width=3), marker=dict(size=6), customdata=list(zip(frame["estimated_tbhiv_mortality_low"], frame["estimated_tbhiv_mortality_high"])),
        hovertemplate="%{x}<br>Estimated TB/HIV mortality: %{y:,.0f}<br>WHO range: %{customdata[0]:,.0f}–%{customdata[1]:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="Estimated TB mortality among people living with HIV", hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=15, r=15, t=80, b=20),
        height=400, paper_bgcolor="white", plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False), yaxis=dict(title="People", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK),
    )
    return fig


def tbhiv_outcome_composition_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "tbhiv_treatment_cohort"]).copy()
    frame = frame.loc[frame["tbhiv_treatment_cohort"] > 0]
    categories = [
        ("Treatment success", "tbhiv_treatment_success", GREEN, ""),
        ("Died", "tbhiv_died", ORANGE, "/"),
        ("Lost to follow-up", "tbhiv_lost_to_follow_up", AMBER, "."),
        ("Treatment failed", "tbhiv_failed", RED, "x"),
        ("Residual / unclassified", "tbhiv_other_or_unclassified", "#7C8799", "-"),
    ]
    fig = go.Figure()
    for label, column, color, pattern in categories:
        counts = pd.to_numeric(frame[column], errors="coerce")
        shares = 100 * counts / frame["tbhiv_treatment_cohort"]
        fig.add_trace(go.Bar(
            x=frame["year"], y=shares, name=label,
            marker=dict(color=color, pattern=dict(shape=pattern, solidity=0.16)),
            text=[f"{share:.1f}%" if pd.notna(share) and share >= 8 else "" for share in shares], textposition="inside",
            textfont=dict(color="white" if label == "Treatment success" else INK, size=11),
            customdata=list(zip(counts, frame["tbhiv_treatment_cohort"])),
            hovertemplate="%{x}<br>" + label + ": %{customdata[0]:,.0f}<br>%{y:.1f}% of TB/HIV cohort<br>Cohort: %{customdata[1]:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        title="TB/HIV treatment outcome composition by cohort year", barmode="stack", hovermode="closest",
        legend=dict(
            orientation="h", x=0, xanchor="left", y=1.03, yanchor="bottom",
            traceorder="normal", font=dict(size=10),
        ),
        margin=dict(l=15, r=15, t=145, b=24),
        height=485, paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(title=None, showgrid=False, dtick=1),
        yaxis=dict(title="Share of TB/HIV treatment cohort", range=[0, 100], ticksuffix="%", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK),
    )
    return fig


def age_sex_composition_chart(df: pd.DataFrame) -> go.Figure:
    columns = ["boys_0_14", "girls_0_14", "men_15_plus", "women_15_plus"]
    frame = df.dropna(subset=["year", *columns]).copy()
    frame["age_sex_total"] = frame[columns].sum(axis=1)
    categories = [
        ("Boys, 0–14", "boys_0_14", "#2D6CDF"),
        ("Girls, 0–14", "girls_0_14", "#8B6FC4"),
        ("Men, 15+", "men_15_plus", "#2E7D6E"),
        ("Women, 15+", "women_15_plus", "#D1783C"),
    ]
    fig = go.Figure()
    for label, column, color in categories:
        shares = 100 * frame[column] / frame["age_sex_total"]
        fig.add_trace(go.Bar(
            x=frame["year"], y=shares, name=label, marker=dict(color=color),
            text=[f"{share:.0f}%" if share >= 12 else "" for share in shares],
            textposition="inside", textfont=dict(color="white", size=11),
            customdata=list(zip(frame[column], frame["age_sex_total"])),
            hovertemplate="%{x}<br>" + label + ": %{customdata[0]:,.0f}<br>%{y:.1f}% of age/sex-reported notifications<br>Reported groups: %{customdata[1]:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        title="Age and sex composition of notified TB cases", barmode="stack", hovermode="closest",
        legend=dict(orientation="h", y=1.16, x=0), margin=dict(l=15, r=15, t=105, b=20),
        height=455, paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(title=None, showgrid=False, dtick=1),
        yaxis=dict(title="Share of age/sex-reported notifications", range=[0, 100], ticksuffix="%", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK),
    )
    return fig


def child_share_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "children_notification_share_pct"]).copy()
    fig = go.Figure(go.Scatter(
        x=frame["year"], y=frame["children_notification_share_pct"], mode="lines+markers",
        line=dict(color="#2D6CDF", width=3), marker=dict(size=6), fill="tozeroy", fillcolor="rgba(45,108,223,0.10)",
        hovertemplate="%{x}<br>Children aged 0–14: %{y:.1f}% of notified cases<extra></extra>",
    ))
    fig.update_layout(
        title="Children aged 0–14 among notified TB cases", margin=dict(l=15, r=15, t=65, b=20), height=360,
        paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="Percent", ticksuffix="%", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK), showlegend=False,
    )
    return fig


def adult_sex_ratio_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "adult_male_to_female_ratio"]).copy()
    fig = go.Figure(go.Scatter(
        x=frame["year"], y=frame["adult_male_to_female_ratio"], mode="lines+markers",
        line=dict(color="#2E7D6E", width=3), marker=dict(size=6), fill="tozeroy", fillcolor="rgba(46,125,110,0.10)",
        hovertemplate="%{x}<br>Adult male-to-female notification ratio: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(y=1, line_dash="dot", line_color="#8A94A6", annotation_text="Equal reported counts", annotation_position="bottom right")
    fig.update_layout(
        title="Adult male-to-female notification ratio", margin=dict(l=15, r=15, t=65, b=20), height=360,
        paper_bgcolor="white", plot_bgcolor="white", xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="Ratio", gridcolor="#E8ECF2", zeroline=False), font=dict(color=INK), showlegend=False,
    )
    return fig


def outcome_composition_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["year", "treatment_cohort"]).copy()
    frame = frame.loc[frame["treatment_cohort"] > 0]
    categories = [
        ("Treatment success", "treatment_success", GREEN, ""),
        ("Died", "died", ORANGE, "/"),
        ("Lost to follow-up", "lost_to_follow_up", AMBER, "."),
        ("Treatment failed", "failed", RED, "x"),
        ("Not evaluated", "not_evaluated", GREY, "\\"),
        ("Residual / unclassified", "other_or_unclassified", "#7C8799", "-"),
    ]

    fig = go.Figure()
    for label, column, color, pattern in categories:
        if column not in frame.columns or not frame[column].notna().any():
            continue
        counts = pd.to_numeric(frame[column], errors="coerce")
        shares = 100 * counts / frame["treatment_cohort"]
        text = [
            f"{share:.1f}%" if pd.notna(share) and share >= 8 else ""
            for share in shares
        ]
        fig.add_trace(
            go.Bar(
                x=frame["year"],
                y=shares,
                name=label,
                marker=dict(
                    color=color,
                    pattern=dict(shape=pattern, solidity=0.16),
                ),
                text=text,
                textposition="inside",
                textfont=dict(
                    color="white" if label == "Treatment success" else INK,
                    size=11,
                ),
                customdata=list(zip(counts, frame["treatment_cohort"])),
                hovertemplate=(
                    "%{x}<br>" + label + ": %{customdata[0]:,.0f}"
                    "<br>%{y:.1f}% of cohort"
                    "<br>Cohort: %{customdata[1]:,.0f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="Treatment outcome composition by cohort year",
        barmode="stack",
        hovermode="closest",
        legend=dict(
            orientation="h", x=0, xanchor="left", y=1.03, yanchor="bottom",
            traceorder="normal", font=dict(size=10),
        ),
        margin=dict(l=15, r=15, t=145, b=24),
        height=485,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False, dtick=1),
        yaxis=dict(
            title="Share of treatment cohort",
            range=[0, 100],
            ticksuffix="%",
            gridcolor="#E8ECF2",
            zeroline=False,
        ),
        font=dict(color=INK),
    )
    return fig

def coverage_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(subset=["notification_coverage_pct"]).copy()
    fig = go.Figure(
        go.Scatter(
            x=frame["year"],
            y=frame["notification_coverage_pct"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color=BLUE, width=3),
            fillcolor="rgba(21,88,214,0.10)",
            hovertemplate="%{x}<br>Notification coverage: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Notifications as a share of estimated incidence",
        margin=dict(l=15, r=15, t=65, b=20),
        height=390,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(
            title="Percent",
            ticksuffix="%",
            gridcolor="#E8ECF2",
            zeroline=False,
        ),
        font=dict(color=INK),
    )
    return fig

# End of chart definitions.
