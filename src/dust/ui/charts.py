from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from dust.ui.tokens import DIMENSION, SEVERITY, severity_for_score

# Facet panel colors (matches earlier Altair categorical look)
DIM_CHART_COLORS = {name: tokens["label"] for name, tokens in DIMENSION.items()}

FACET_ORDER_TOP = ("attribution", "description")
FACET_ORDER_BOTTOM = ("date", "medium")


def render_histogram(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.caption("No records match the current filters.")
        return
    df = frame.copy()
    df["bin"] = (df["composite"] // 10 * 10).astype(int)
    counts = df.groupby("bin").size().reset_index(name="count")
    counts["severity"] = counts["bin"].apply(lambda b: severity_for_score(b + 5))
    counts["color"] = counts["severity"].map(lambda s: SEVERITY[s]["ink"])

    chart = (
        alt.Chart(counts)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("bin:O", title="Composite score"),
            y=alt.Y("count:Q", title="Records"),
            color=alt.Color("color:N", scale=None, legend=None),
        )
        .properties(height=260)
    )
    st.altair_chart(chart, width="stretch")


def _band_panel(data: pd.DataFrame, dimension: str) -> alt.Chart:
    subset = data[data["dimension"] == dimension]
    color = DIM_CHART_COLORS[dimension]
    return (
        alt.Chart(subset)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, color=color)
        .encode(
            x=alt.X("count:Q", title="Records", axis=alt.Axis(tickMinStep=1)),
            y=alt.Y("band:N", sort="-x", title=None),
        )
        .properties(title=dimension.title(), height=115)
    )


def render_band_counts(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.caption("No records match the current filters.")
        return

    rows = []
    for dim_name, col in [
        ("date", "date_band"),
        ("medium", "medium_band"),
        ("attribution", "attribution_band"),
        ("description", "description_band"),
    ]:
        for band, count in frame[col].value_counts().items():
            rows.append(
                {
                    "dimension": dim_name,
                    "band": str(band).replace("_", " ").capitalize(),
                    "count": int(count),
                }
            )
    if not rows:
        return

    data = pd.DataFrame(rows)
    top = alt.hconcat(
        *[_band_panel(data, d) for d in FACET_ORDER_TOP],
        spacing=12,
    )
    bottom = alt.hconcat(
        *[_band_panel(data, d) for d in FACET_ORDER_BOTTOM],
        spacing=12,
    )
    chart = (
        alt.vconcat(top, bottom, spacing=12)
        .resolve_scale(x="independent", y="independent")
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, width="stretch")


def render_department_chart(frame: pd.DataFrame, single_department: bool) -> None:
    if frame.empty:
        return
    if single_department:
        grouped = frame.groupby("type", dropna=False)["composite"].agg(["mean", "count"]).reset_index()
        x_field = "type"
        title = "Mean composite by type"
    else:
        grouped = frame.groupby("department", dropna=False)["composite"].agg(["mean", "count"]).reset_index()
        x_field = "department"
        title = "Mean composite by department"

    grouped["severity"] = grouped["mean"].apply(severity_for_score)
    grouped["color"] = grouped["severity"].map(lambda s: SEVERITY[s]["ink"])

    chart = (
        alt.Chart(grouped)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            y=alt.Y(f"{x_field}:N", sort="-x", title=None),
            x=alt.X("mean:Q", title="Mean completeness score", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("color:N", scale=None, legend=None),
            tooltip=[x_field, alt.Tooltip("mean:Q", format=".0f"), "count"],
        )
        .properties(title=title, height=max(280, len(grouped) * 24))
    )
    st.altair_chart(chart, width="stretch")
