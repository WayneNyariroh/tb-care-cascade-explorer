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
    cohort: Optional[float],
    success: Optional[float],
    died: Optional[float],
    failed: Optional[float],
    lost: Optional[float],
    not_evaluated: Optional[float],
    outcome_year: Optional[int],
) -> go.Figure:
    incidence = max(float(incidence or 0), 0)
    notified = max(min(float(notified or 0), incidence), 0)
    missing = max(incidence - notified, 0)

    cohort = max(float(cohort or notified), 0)
    success = max(float(success or 0), 0)
    died = max(float(died or 0), 0)
    failed = max(float(failed or 0), 0)
    lost = max(float(lost or 0), 0)
    not_evaluated = max(float(not_evaluated or 0), 0)

    known_outcomes = success + died + failed + lost + not_evaluated
    other = max(cohort - known_outcomes, 0)

    labels = [
        "Estimated TB incidence",
        "Notified cases",
        "Notification gap",
        f"Treatment cohort{f' ({outcome_year})' if outcome_year else ''}",
        "Treatment success",
        "Died",
        "Treatment failed",
        "Lost to follow-up",
        "Not evaluated",
        "Other / unclassified",
    ]

    sources = [0, 0, 1, 3, 3, 3, 3, 3, 3]
    targets = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    values = [
        notified,
        missing,
        max(min(cohort, notified), 0),
        success,
        died,
        failed,
        lost,
        not_evaluated,
        other,
    ]

    node_colors = [
        BLUE,
        BLUE_LIGHT,
        GREY,
        PURPLE,
        GREEN,
        ORANGE,
        RED,
        AMBER,
        GREY,
        GREY_LIGHT,
    ]

    link_colors = [
        "rgba(21,88,214,0.34)",
        "rgba(154,160,166,0.26)",
        "rgba(104,29,168,0.28)",
        "rgba(20,108,46,0.34)",
        "rgba(216,89,0,0.30)",
        "rgba(192,21,29,0.30)",
        "rgba(234,169,55,0.34)",
        "rgba(154,160,166,0.28)",
        "rgba(218,220,224,0.55)",
    ]

    title = "Observed-data care cascade"
    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            valueformat=",.0f",
            node=dict(
                pad=26,
                thickness=20,
                line=dict(color="rgba(0,0,0,0)", width=0),
                label=labels,
                color=node_colors,
                customdata=[
                    _fmt(incidence),
                    _fmt(notified),
                    _fmt(missing),
                    _fmt(cohort),
                    _fmt(success),
                    _fmt(died),
                    _fmt(failed),
                    _fmt(lost),
                    _fmt(not_evaluated),
                    _fmt(other),
                ],
                hovertemplate="<b>%{label}</b><br>%{customdata}<extra></extra>",
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color=link_colors,
                hovertemplate=(
                    "%{source.label} → %{target.label}"
                    "<br><b>%{value:,.0f}</b><extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=18)),
        font=dict(size=12, color=INK),
        margin=dict(l=18, r=18, t=60, b=20),
        height=560,
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
    labels = [
        "Treatment success",
        "Died",
        "Treatment failed",
        "Lost to follow-up",
        "Not evaluated",
    ]
    values = [
        metrics.get("success"),
        metrics.get("died"),
        metrics.get("failed"),
        metrics.get("lost"),
        metrics.get("not_evaluated"),
    ]
    clean = [(l, v) for l, v in zip(labels, values) if v is not None]
    labels = [x[0] for x in clean]
    values = [x[1] for x in clean]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=[GREEN, ORANGE, RED, AMBER, GREY][: len(values)],
            text=[f"{v:,.0f}" for v in values],
            textposition="outside",
            hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=f"Treatment outcomes{f' · cohort {year}' if year else ''}",
        margin=dict(l=15, r=60, t=65, b=20),
        height=390,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(title="People", gridcolor="#E8ECF2"),
        yaxis=dict(title=None, autorange="reversed"),
        font=dict(color=INK),
    )
    return fig
