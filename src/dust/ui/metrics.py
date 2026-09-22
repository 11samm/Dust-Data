from __future__ import annotations

import pandas as pd
import streamlit as st

from dust.ui.tokens import severity_for_rate, severity_for_score


def _metric_card(
    label: str,
    value: str,
    severity: str | None = None,
    detail: str | None = None,
) -> None:
    sev_class = f" sev-{severity}" if severity else ""
    detail_html = f'<div class="metric-detail">{detail}</div>' if detail else ""
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value{sev_class}">{value}</div>{detail_html}</div>',
        unsafe_allow_html=True,
    )


def render_health_row(frame: pd.DataFrame, threshold: int) -> None:
    if frame.empty:
        cols = st.columns(4)
        for i, label in enumerate(["Records in view", "Mean completeness", "Needs attention", "Public image"]):
            with cols[i]:
                _metric_card(label, "—")
        return

    n = len(frame)
    mean_c = frame["composite"].mean()
    below = (frame["composite"] <= threshold).sum()
    present = (frame["image_state"] == "present").mean() * 100

    cols = st.columns(4)
    with cols[0]:
        _metric_card("Records in view", str(n))
    with cols[1]:
        _metric_card("Mean completeness", f"{mean_c:.0f}", severity_for_score(mean_c), "out of 100")
    with cols[2]:
        share = below / n * 100
        _metric_card("Needs attention", str(below), severity_for_rate(100 - share), f"{share:.0f}% at or below {threshold}")
    with cols[3]:
        withheld = (frame["image_state"] == "withheld_by_license").sum()
        absent = (frame["image_state"] == "absent").sum()
        _metric_card(
            "Public image",
            f"{present:.0f}%",
            severity_for_rate(present),
            f"{withheld} withheld · {absent} absent",
        )


def render_rate_row(frame: pd.DataFrame) -> None:
    if frame.empty:
        return

    any_date = (frame["date_state"] == "present").mean() * 100
    year_level = frame["date_band"].isin(["circa", "narrow_range", "exact"]).mean() * 100
    specific_medium = (frame["medium_band"] == "specific").mean() * 100
    named = (frame["attribution_band"] == "named").mean() * 100
    desc = (frame["description_band"] == "present").mean() * 100

    labels = [
        ("Any date", any_date, "date"),
        ("Year-level date", year_level, "date"),
        ("Specific medium", specific_medium, "medium"),
        ("Named attribution", named, "attribution"),
        ("Present description", desc, "description"),
    ]
    cols = st.columns(5)
    from dust.ui.tokens import DIMENSION

    for col, (label, rate, dim) in zip(cols, labels):
        with col:
            bar = DIMENSION[dim]["label"]
            sev = severity_for_rate(rate)
            st.markdown(
                f'<div class="metric-card rate-card" style="--accent-bar:{bar}">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value sev-{sev}">{rate:.0f}%</div></div>',
                unsafe_allow_html=True,
            )
