from __future__ import annotations

from dust.model import NormalizedRecord
from dust.score.policy import WORST_DATE_BANDS, band_score_for

MEDIUM_LABEL = {
    "missing": "missing",
    "generic": "generic",
    "material_only": "material-only",
}

ATTRIBUTION_LABEL = {
    "missing": "missing",
    "unknown": "unknown",
    "culture_only": "culture-only",
    "qualified": "qualified",
    "attributed": "attributed",
}


def _date_gap(norm: NormalizedRecord) -> str | None:
    raw = norm.date_display or "(empty)"
    span = norm.date_span_years
    band = norm.date_band
    if band == "missing":
        return "Date missing"
    if band == "undated_text":
        return f'Date unparsed: "{raw}"'
    if band == "multi_century" and span is not None:
        return f'Date spans {span + 1} years: "{raw}"'
    if band == "multi_century":
        return f'Date spans many years: "{raw}"'
    if band == "century":
        return f'Date is century-level: "{raw}"'
    if band == "generation":
        return f'Date is a generation-wide range: "{raw}"'
    if band == "decade":
        return f'Date is decade-level: "{raw}"'
    if band == "circa":
        return f'Date is approximate: "{raw}"'
    if band == "narrow_range":
        return f'Date is a short range: "{raw}"'
    return None


def _medium_gap(norm: NormalizedRecord) -> str | None:
    if norm.medium_band == "specific":
        return None
    label = MEDIUM_LABEL.get(norm.medium_band, norm.medium_band)
    technique = norm.medium_raw or "(empty)"
    return f'Medium is {label}: "{technique}"'


def _attribution_gap(norm: NormalizedRecord) -> str | None:
    if norm.attribution_band == "named":
        return None
    label = ATTRIBUTION_LABEL.get(norm.attribution_band, norm.attribution_band)
    text = norm.attribution_label or "(empty)"
    return f'Attribution is {label}: "{text}"'


def _description_gap(norm: NormalizedRecord) -> str | None:
    if norm.description_band == "present":
        return None
    if norm.description_band == "stub":
        return "Description is a stub"
    return "No description"


def _image_gap(norm: NormalizedRecord) -> str | None:
    if norm.image_state == "present":
        return None
    if norm.image_state == "unassessed":
        return "Image availability unassessed"
    if norm.image_state == "withheld_by_license":
        lic = norm.share_license_status or "Copyrighted"
        return f"No public image — withheld by license ({lic})"
    return "No public image"


def gap_for_dimension(norm: NormalizedRecord, dimension: str) -> str | None:
    if dimension == "image":
        return _image_gap(norm)
    if dimension == "date":
        return _date_gap(norm)
    if dimension == "medium":
        return _medium_gap(norm)
    if dimension == "attribution":
        return _attribution_gap(norm)
    if dimension == "description":
        return _description_gap(norm)
    raise ValueError(dimension)


def build_gaps(norm: NormalizedRecord) -> list[str]:
    gaps: list[str] = []
    for fn in (_image_gap, _date_gap, _medium_gap, _attribution_gap, _description_gap):
        text = fn(norm)
        if text:
            gaps.append(text)
    return gaps


def gap_flags(norm: NormalizedRecord) -> dict[str, bool]:
    date_score, _ = band_score_for(norm, "date")
    return {
        "has_gap_image": norm.image_state in ("absent", "withheld_by_license"),
        "has_gap_date": date_score < 1.0,
        "has_gap_date_century_or_worse": norm.date_band in WORST_DATE_BANDS,
        "has_gap_medium": norm.medium_band != "specific",
        "has_gap_attribution": norm.attribution_band != "named",
        "has_gap_description": norm.description_band != "present",
    }
