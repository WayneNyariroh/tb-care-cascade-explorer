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
        f"{'Est. gap' if compact else 'Estimated notification gap'}<br><b>{_fmt(notification_gap)}</b>",
        f"{'Cohort' if compact else 'Outcome cohort'}<br><b>{_fmt(cohort)}</b>",
    ]
    node_colors = [BLUE, "#2E7D6E", "#CBD1D9", PURPLE]
    node_x = [0.01, 0.31, 0.31, 0.59]
    node_y = [0.10, 0.04, 0.72 if compact else 0.68, 0.04]
    node_customdata = [
        "WHO modelled incidence point estimate",
        "New, recurrent and unknown previous-treatment-history cases reported",
        "Point estimate minus notifications; not a counted outcome",
        "New-and-recurrent cohort included in treatment-outcome reporting",
    ]

    sources = [0, 0]
    targets = [1, 2]
    values = [notified, notification_gap]
    link_colors = ["rgba(46,125,110,0.32)", "rgba(180,187,197,0.28)"]
    link_customdata = [
        "Reported notifications",
        "Estimated notification gap",
    ]

    if notified >= cohort:
        reconciliation = notified - cohort
        labels.append(
            ("Recon.<br>" if compact else "Notification–cohort<br>reconciliation<br>")
            + f"<b>{_fmt(reconciliation)}</b>"
        )
        node_colors.append("#E7E9ED")
        node_x.append(0.59)
        node_y.append(0.88 if compact else 0.77)
        node_customdata.append(
            "Aggregate definition and reporting difference; not a treatment outcome"
        )
        sources.extend([1, 1])
        targets.extend([3, 4])
        values.extend([cohort, reconciliation])
        link_colors.extend(["rgba(104,29,168,0.28)", "rgba(190,195,203,0.30)"])
        link_customdata.extend(
            ["Included in outcome cohort", "Notification–cohort reconciliation"]
        )
    else:
        reconciliation = cohort - notified
        labels.append(
            ("Recon.<br>" if compact else "Additional cohort<br>reconciliation<br>")
            + f"<b>{_fmt(reconciliation)}</b>"
        )
        node_colors.append("#E7E9ED")
        node_x.append(0.31)
        node_y.append(0.88 if compact else 0.77)
        node_customdata.append(
            "Outcome cohort exceeds the notification aggregate; not a treatment outcome"
        )
        sources.extend([1, 4])
        targets.extend([3, 3])
        values.extend([notified, reconciliation])
        link_colors.extend(["rgba(104,29,168,0.28)", "rgba(190,195,203,0.30)"])
        link_customdata.extend(
            ["Reported notifications", "Additional cohort reconciliation"]
        )

    outcome_y = (
        [0.01, 0.56, 0.66, 0.75, 0.81, 0.84]
        if compact
        else [0.01, 0.48, 0.58, 0.67, 0.74, 0.80]
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
        node_x.append(0.91)
        node_y.append(outcome_y[min(index, len(outcome_y) - 1)])
        node_customdata.append(f"{share:.1f}% of the outcome cohort")
        sources.append(3)
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
            dict(l=12, r=66, t=28, b=24)
            if compact
            else dict(l=34, r=152, t=28, b=32)
        ),
        height=540 if compact else 560,
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def trend_chart(df: pd.DataFrame) -> go.Figure:
    frame = df.dropna(
        subset=["year", "estimated_incidence", "notifications"], how="all"
    ).copy()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["year"],
            y=frame["estimated_incidence"],
            mode="lines+markers",
            name="Estimated incidence",
            line=dict(color=BLUE, width=3),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Estimated incidence: %{y:,.0f}<extra></extra>",
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


def outcome_bar(metrics: dict, year: Optional[int]) -> go.Figure:
    cohort = metrics.get("cohort")
    labels = [
        "Treatment success",
        "Died",
        "Treatment failed",
        "Lost to follow-up",
        "Not evaluated",
        "Residual / unclassified",
    ]
    values = [
        metrics.get("success"),
        metrics.get("died"),
        metrics.get("failed"),
        metrics.get("lost"),
        metrics.get("not_evaluated"),
        metrics.get("other_or_unclassified"),
    ]
    colors = [GREEN, ORANGE, RED, AMBER, GREY, GREY_LIGHT]
    clean = [
        (label, float(value), color)
        for label, value, color in zip(labels, values, colors)
        if value is not None and float(value) > 0
    ]
    labels = [item[0] for item in clean]
    values = [item[1] for item in clean]
    colors = [item[2] for item in clean]
    percentages = [
        100 * value / cohort if cohort not in (None, 0) else None
        for value in values
    ]
    text = [
        f"{value:,.0f} · {percentage:.1f}%"
        if percentage is not None
        else f"{value:,.0f}"
        for value, percentage in zip(values, percentages)
    ]
    text_positions = [
        "inside" if percentage is not None and percentage >= 20 else "outside"
        for percentage in percentages
    ]
    text_colors = [
        "white" if position == "inside" else INK
        for position in text_positions
    ]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=text,
            textposition=text_positions,
            textfont=dict(color=text_colors),
            insidetextanchor="end",
            cliponaxis=False,
            customdata=percentages,
            hovertemplate=(
                "%{y}<br><b>%{x:,.0f}</b>"
                "<br>%{customdata:.1f}% of cohort<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=f"Treatment outcomes{f' · cohort {year}' if year else ''}",
        margin=dict(l=128, r=106, t=65, b=28),
        height=420,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title="People", gridcolor="#E8ECF2", rangemode="tozero"),
        yaxis=dict(title=None, autorange="reversed"),
        font=dict(size=12, color=INK),
        showlegend=False,
    )
    return fig
