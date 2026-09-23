from __future__ import annotations

import html
import hashlib
import math
import re
from collections.abc import Mapping

import pandas as pd
import streamlit as st

from dust.config import QUEUE_PAGE_SIZE  # default 15 records per queue page
from dust.model import ScoredRecord
from dust.ui.tokens import DIMENSION, SEVERITY, severity_for_score

_SAFE_KEY = re.compile(r"[^A-Za-z0-9]+")


def _format_band_score(value: float) -> str:
    return f"{value * 100:.0f}/100"


def _rights_label(uri: str) -> str:
    if "/publicdomain/zero/1.0/" in uri:
        return "CC0 / public domain"
    if "/vocab/InC/" in uri:
        return "In copyright"
    if "/licenses/by/4.0/" in uri:
        return "CC BY 4.0"
    return uri


def paginate_frame(frame: pd.DataFrame, page: int, page_size: int = QUEUE_PAGE_SIZE) -> tuple[pd.DataFrame, int, int]:
    """Returns (page_slice, total_pages, clamped_page_index)."""
    total = len(frame)
    if total == 0:
        return frame, 1, 0
    total_pages = max(1, math.ceil(total / page_size))
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    end = min(start + page_size, total)
    return frame.iloc[start:end].reset_index(drop=True), total_pages, page


def _chip_html(text: str, dimension: str, composite: int) -> str:
    dim = DIMENSION.get(dimension, DIMENSION["description"])
    sev = severity_for_score(composite)
    sev_ink = SEVERITY[sev]["ink"]
    return (
        f'<span class="gap-chip" style="background:{dim["tint"]};color:{dim["label"]};'
        f'--chip-sev:{sev_ink}">{html.escape(text)}</span>'
    )


def _gap_dimension(gap: str) -> str:
    if gap.startswith("No public image"):
        return "image"
    if gap.startswith("Date"):
        return "date"
    if gap.startswith("Medium"):
        return "medium"
    if gap.startswith("Attribution"):
        return "attribution"
    return "description"


def _row_key(record_key: str) -> str:
    readable = _SAFE_KEY.sub("_", record_key).strip("_")[:48]
    digest = hashlib.sha256(record_key.encode("utf-8")).hexdigest()[:12]
    return f"qrow_{readable}_{digest}"


def _row_html(row, rank: int, selected: bool) -> str:
    acc = str(row.accession_number)
    sev = severity_for_score(row.composite)
    gaps = [g for g in str(row.gaps_display or "").split("; ") if g]
    chips = "".join(_chip_html(g, _gap_dimension(g), row.composite) for g in gaps)
    selected_cls = " queue-row-selected" if selected else ""
    title = html.escape(str(row.title or "—"))
    dept = html.escape(str(row.department or ""))
    if row.url:
        acc_html = (
            f'<a href="{html.escape(str(row.url), quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{html.escape(acc)}</a>'
        )
    else:
        acc_html = html.escape(acc)
    chips_block = f'<div class="queue-chips">{chips}</div>' if chips else '<div class="queue-chips"></div>'
    return (
        f'<div class="queue-row{selected_cls}">'
        f'<div class="queue-rank">{rank}</div>'
        f'<div class="queue-id">{acc_html}</div>'
        f'<div class="queue-meta"><div class="queue-title">{title}</div>'
        f'<div class="muted">{dept}</div></div>'
        f"{chips_block}"
        f'<span class="pill pill-{sev}">{row.composite}</span>'
        f"</div>"
    )


def render_queue(frame: pd.DataFrame, records: Mapping[str, ScoredRecord]) -> None:
    if frame.empty:
        st.info("No records match the active filters.")
        return

    if "queue_page" not in st.session_state:
        st.session_state.queue_page = 0

    total = len(frame)
    total_pages = max(1, math.ceil(total / QUEUE_PAGE_SIZE))
    if "queue_pager" in st.session_state:
        current = int(st.session_state.queue_pager or 1)
        clamped = max(1, min(current, total_pages))
        if clamped != current:
            st.session_state.queue_pager = clamped

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        caption_slot = st.empty()
        page_1 = st.pagination(total_pages, key="queue_pager", width="content")

    page_slice, total_pages, page = paginate_frame(frame, page_1 - 1, page_size=QUEUE_PAGE_SIZE)
    st.session_state.queue_page = page
    start_rank = page * QUEUE_PAGE_SIZE + 1
    end_rank = min((page + 1) * QUEUE_PAGE_SIZE, total)
    selected = st.session_state.get("selected_record_key")
    caption_slot.caption(
        f"Showing ranks **{start_rank}–{end_rank}** of **{total}** · page **{page + 1}** of **{total_pages}**"
    )

    with st.container(gap="xsmall", key="queue_list"):
        for offset, row in enumerate(page_slice.itertuples(index=False)):
            rank = start_rank + offset
            acc = str(row.accession_number)
            record_key = str(row.record_key)
            is_selected = record_key == selected
            with st.container(
                gap="small",
                border=True,
                key=_row_key(record_key),
            ):
                st.html(_row_html(row, rank, is_selected), width="stretch")
                show_evidence = st.button(
                    "Evidence",
                    key=f"evidence_{_row_key(record_key)}",
                    type="primary" if is_selected else "tertiary",
                    icon=":material/info:",
                    width="content",
                )
                if show_evidence:
                    st.session_state.selected_record_key = record_key
                    render_evidence_dialog(records.get(record_key))


@st.dialog("Scoring evidence", width="large")
def render_evidence_dialog(rec: ScoredRecord | None) -> None:
    render_evidence(rec)


def render_evidence(rec: ScoredRecord | None) -> None:
    if rec is None:
        st.caption("Select a record in the queue and click **Evidence** to inspect scoring details.")
        return

    norm = rec.normalized
    image_url = (rec.raw.images.get("web") or {}).get("url")
    if rec.raw.source_name == "getty" and image_url:
        details, picture = st.columns([3, 1], gap="medium")
    else:
        details, picture = st.container(), None
    with details:
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.subheader(norm.title or norm.accession_number, anchor=False)
            st.badge(f"Score {rec.composite}", color="green" if rec.composite >= 75 else "orange" if rec.composite >= 50 else "red")
        st.caption(f"{rec.raw.source_name.title()} · Accession {norm.accession_number} · {norm.department or 'Department unavailable'}")
        if rec.raw.source_uri:
            st.caption(f"Object URI: {rec.raw.source_uri}")
        if norm.url:
            st.link_button("Open collection record", norm.url, icon=":material/open_in_new:")
        if rec.raw.metadata_rights:
            st.caption(f"Metadata rights: {_rights_label(rec.raw.metadata_rights)}")
        if rec.raw.iiif_manifest:
            st.link_button("IIIF manifest", rec.raw.iiif_manifest, icon=":material/open_in_new:")
    if picture is not None:
        with picture:
            st.image(image_url, caption="Getty IIIF view", width=200)
            if rec.raw.image_rights:
                st.caption(f"Image rights: {_rights_label(rec.raw.image_rights)}")
            original_image = next((item.get("id") for item in rec.raw.source.get("representation", []) if isinstance(item, dict) and item.get("id")), "")
            if original_image:
                st.link_button("Full image", original_image, icon=":material/open_in_new:")
    elif rec.raw.image_rights:
        st.caption(f"Image rights: {_rights_label(rec.raw.image_rights)}")
    if rec.raw.aat_evidence:
        st.markdown("**Medium and AAT evidence**")
        for concept in rec.raw.aat_evidence:
            status = concept.get("resolution_status") or ("resolved" if concept.get("match_source") == "embedded" else "unresolved")
            st.caption(f"{concept.get('role', 'medium')}: {concept.get('label', '—')} · {concept.get('uri') or 'no URI'} · {concept.get('match_source', 'embedded')} · {status.replace('_', ' ')}")

    for dim in rec.dimensions:
        weight_note = "" if dim.weight_applied else " (excluded from composite)"
        score_note = _format_band_score(dim.band_score) if dim.weight_applied else "not scored"
        st.markdown(
            f"**{dim.dimension_id.title()}** · {dim.band.replace('_', ' ')} · {score_note} · "
            f"weight {dim.weight}{weight_note}"
        )
        if dim.gap:
            st.markdown(dim.gap)

    st.markdown("**Source and normalized values**")
    st.markdown(
        f'<div class="evidence-pair"><strong>Date</strong> {html.escape(norm.date_display or "—")} → '
        f"{norm.date_band}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="evidence-pair"><strong>Medium</strong> {html.escape(norm.medium_raw or "—")} → '
        f"{html.escape(norm.medium_canonical or '—')} ({norm.medium_band})</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="evidence-pair"><strong>Attribution</strong> {html.escape(norm.attribution_label or "—")} '
        f"→ {norm.attribution_band}</div>",
        unsafe_allow_html=True,
    )

    if rec.raw.source_name == "getty":
        source = rec.raw.source
        identifiers = [item for item in (source.get("identified_by") or []) if isinstance(item, dict) and item.get("_label") in {"Accession Number", "Preferred Title"}]
        notes = [item for item in (source.get("referred_to_by") or []) if isinstance(item, dict) and item.get("_label") in {"Materials Description", "Object Type"}]
        production = source.get("produced_by") or {}
        with st.expander("Getty source fields"):
            st.json({
                "identified_by": identifiers,
                "referred_to_by": notes,
                "production_timespan": production.get("timespan"),
                "production_creators": production.get("carried_out_by"),
            })

    if norm.date_conflict:
        st.warning("Date conflict between display text and year span.")
    for w in norm.parse_warnings:
        st.warning(w)
