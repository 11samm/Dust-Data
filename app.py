from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from dust.api.load import ensure_cohort, load_or_fetch_cohort
from dust.config import APP_TITLE, CACHE_DIR, COHORT_SIZE, COHORT_SIZES, DEPARTMENTS, TYPES, WEIGHTS
from dust.score.run import load_cohort, policy_fingerprint
from dust.ui.charts import render_band_counts, render_department_chart, render_histogram
from dust.ui.filters import apply_filters
from dust.ui.metrics import render_health_row, render_rate_row
from dust.ui.queue import render_queue

THEME_CSS = ROOT / "src" / "dust" / "ui" / "theme.css"


@st.cache_data(show_spinner="Scoring cohort…", max_entries=12)
def cached_bundle(
    mode: str,
    department: str | None,
    type_: str | None,
    size: int,
    cache_mtime: float,
    policy_hash: str,
):
    return load_or_fetch_cohort(
        mode=mode,
        department=department,
        type_=type_,
        size=size,
        force_refresh=False,
    )


def clear_filters() -> None:
    for key in (
        "include_parts",
        "gap_image",
        "gap_date",
        "gap_medium",
        "gap_attribution",
        "gap_description",
        "department_filter",
        "type_filter",
        "license_filter",
        "max_completeness",
    ):
        st.session_state.pop(key, None)


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":material/museum:",
        layout="wide",
    )
    st.html(f"<style>{THEME_CSS.read_text(encoding='utf-8')}</style>")

    if "selected_accession" not in st.session_state:
        st.session_state.selected_accession = None
    if "queue_page" not in st.session_state:
        st.session_state.queue_page = 0
    if "queue_list_key" not in st.session_state:
        st.session_state.queue_list_key = None

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        st.title(APP_TITLE, anchor=False, width="content")
        if st.button("Reload scores", icon=":material/refresh:", type="tertiary"):
            st.cache_data.clear()
            st.rerun()
    st.caption("Find incomplete collection records, understand the gaps, and decide what to fix first.")

    with st.sidebar:
        st.header("Sample", anchor=False)
        mode = (
            st.segmented_control(
                "Sample mode",
                ["stratified", "department", "type"],
                default="stratified",
                format_func=lambda value: value.capitalize(),
                required=True,
                width="stretch",
                key="sample_mode",
            )
            or "stratified"
        )
        department = None
        type_ = None
        if mode == "department":
            department = st.selectbox("Department", DEPARTMENTS, key="sample_department")
        elif mode == "type":
            type_ = st.selectbox("Type", TYPES, index=TYPES.index("Painting"), key="sample_type")

        refresh = st.button(
            "Refresh sample",
            type="primary",
            icon=":material/sync:",
            width="stretch",
        )
        sample_size = (
            st.segmented_control(
                "Sample size",
                list(COHORT_SIZES),
                default=COHORT_SIZE,
                format_func=lambda value: f"{value:,}",
                help="250 is fastest, 500 is the balanced default, and 1,000 is best for a deeper audit.",
                required=True,
                width="stretch",
                key="sample_size",
            )
            or COHORT_SIZE
        )

        from dust.api.cache import cache_path_for_key, cohort_key, read_cache

        ck = cohort_key(mode, size=sample_size, department=department, type_=type_ or None)
        cache_path = cache_path_for_key(ck, CACHE_DIR)
        cache_age = "no cache yet"
        if cache_path.exists():
            payload = read_cache(cache_path)
            cache_age = payload.get("fetched_at", "unknown")[:10]

        st.caption(f"Sample updated: {cache_age}")

        st.header("Triage", anchor=False)
        threshold = st.slider(
            "Needs-attention threshold",
            0,
            100,
            50,
            help="Records at or below this score are counted as needing attention.",
        )
        include_parts = st.checkbox("Include parts and components", value=False, key="include_parts")

        st.subheader("Required gaps", anchor=False)
        st.caption("Selecting more than one gap narrows the queue to records with every selected issue.")
        gap_image = st.checkbox("Missing public image", key="gap_image")
        gap_date = st.checkbox("Date is century-level or worse", key="gap_date")
        gap_medium = st.checkbox("Medium is not specific", key="gap_medium")
        gap_attribution = st.checkbox("Attribution is not named", key="gap_attribution")
        gap_description = st.checkbox("Description is missing", key="gap_description")

        with st.expander("Scoring policy", icon=":material/balance:"):
            st.caption("Read-only weights: " + ", ".join(f"{k} {v}%" for k, v in WEIGHTS.items()))

    refresh_error = None
    if refresh:
        try:
            with st.spinner("Refreshing the museum sample…"):
                ensure_cohort(
                    mode=mode,
                    department=department,
                    type_=type_ or None,
                    size=sample_size,
                    force_refresh=True,
                )
            st.cache_data.clear()
            st.toast("New randomized sample loaded", icon=":material/check_circle:")
        except Exception as exc:
            refresh_error = exc

    if not cache_path.exists():
        try:
            with st.spinner("Building the first sample from the museum API…"):
                ensure_cohort(
                    mode=mode,
                    department=department,
                    type_=type_ or None,
                    size=sample_size,
                )
        except Exception as exc:
            st.error("The museum API could not be reached and there is no cached sample to show.", icon=":material/error:")
            st.caption(f"Technical detail: {exc}")
            st.stop()

    if refresh_error is not None:
        st.warning("The refresh failed, so the last cached sample is being shown.", icon=":material/cloud_off:")
        bundle = load_cohort(cache_path)
    else:
        if not cache_path.exists():
            st.error("No sample is available.")
            st.stop()
        mtime = cache_path.stat().st_mtime if cache_path.exists() else 0.0
        ph = policy_fingerprint()
        try:
            bundle = cached_bundle(mode, department, type_ or None, sample_size, mtime, ph)
        except Exception:
            st.warning("Live data is temporarily unavailable, so the last cached sample is being shown.", icon=":material/cloud_off:")
            bundle = load_cohort(cache_path)
    st.caption(bundle.meta.banner)

    frame = bundle.frame
    departments_in = sorted(frame["department"].dropna().unique()) if not frame.empty else []
    types_in = sorted(frame["type"].dropna().unique()) if not frame.empty else []

    with st.sidebar:
        st.header("Results", anchor=False)
        dept_filter = st.multiselect("Departments", departments_in, default=[], key="department_filter")
        type_filter = st.multiselect("Object types", types_in, default=[], key="type_filter")
        license_filter = st.multiselect(
            "License status",
            sorted(frame["share_license_status"].dropna().unique()) if not frame.empty else [],
            default=[],
            key="license_filter",
        )
        max_comp = st.slider("Maximum completeness score", 0, 100, 100, key="max_completeness")
        st.button(
            "Clear result filters",
            icon=":material/filter_alt_off:",
            on_click=clear_filters,
            width="stretch",
        )

    filtered = apply_filters(
        frame,
        include_parts=include_parts,
        departments=dept_filter or None,
        types=type_filter or None,
        licenses=license_filter or None,
        max_composite=max_comp if max_comp < 100 else None,
        gap_image=gap_image,
        gap_date_century=gap_date,
        gap_medium=gap_medium,
        gap_attribution=gap_attribution,
        gap_description=gap_description,
    )

    list_key = (
        len(filtered),
        tuple(dept_filter),
        tuple(type_filter),
        tuple(license_filter),
        max_comp,
        include_parts,
        gap_image,
        gap_date,
        gap_medium,
        gap_attribution,
        gap_description,
        mode,
        department,
        type_,
        sample_size,
    )
    if st.session_state.queue_list_key != list_key:
        previous_key = st.session_state.queue_list_key
        st.session_state.queue_list_key = list_key
        st.session_state.queue_page = 0
        if previous_key is not None and "queue_pager" in st.session_state:
            st.session_state.queue_pager = 1

    render_health_row(filtered, threshold)

    triage_tab, overview_tab = st.tabs(
        [":material/format_list_numbered: Triage queue", ":material/analytics: Overview"]
    )

    with triage_tab:
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.subheader("Records to review", anchor=False)
            export_columns = [
                "accession_number",
                "title",
                "department",
                "type",
                "composite",
                "gaps_display",
                "url",
            ]
            export_frame = filtered[[column for column in export_columns if column in filtered.columns]].copy()
            export_frame = export_frame.rename(columns={"composite": "completeness_score", "gaps_display": "gaps"})
            st.download_button(
                "Export queue",
                export_frame.to_csv(index=False).encode("utf-8"),
                file_name="dust-and-data-triage.csv",
                mime="text/csv",
                icon=":material/download:",
                disabled=export_frame.empty,
                width="content",
            )
        st.caption("Lowest completeness scores appear first. Open evidence to inspect how a record was scored.")
        render_queue(filtered, bundle.records)

    with overview_tab:
        st.subheader("Metadata coverage", anchor=False)
        render_rate_row(filtered)
        st.subheader("Score distribution", anchor=False)
        render_histogram(filtered)
        st.subheader("Band counts", anchor=False)
        render_band_counts(filtered)

        single_dept = mode == "department" or (dept_filter and len(dept_filter) == 1)
        render_department_chart(filtered, single_department=single_dept)

        review_count = len(bundle.unseen_terms) if bundle.unseen_terms is not None else 0
        with st.expander(f"Vocabulary review ({review_count})", expanded=False, icon=":material/rule:"):
            if review_count == 0:
                st.caption("No unseen media or qualifiers in this score run.")
            else:
                st.dataframe(bundle.unseen_terms, width="stretch")
                csv_path = CACHE_DIR / "unseen_terms.csv"
                if csv_path.exists():
                    st.download_button(
                        "Download unseen terms",
                        csv_path.read_bytes(),
                        file_name="unseen_terms.csv",
                        icon=":material/download:",
                    )


if __name__ == "__main__":
    main()
