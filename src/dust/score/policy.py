from __future__ import annotations

import math

from dust.config import WEIGHTS
from dust.model import NormalizedRecord

DATE_BAND_SCORE = {
    "missing": 0.0,
    "undated_text": 0.15,
    "multi_century": 0.30,
    "century": 0.45,
    "generation": 0.65,
    "decade": 0.80,
    "circa": 0.90,
    "narrow_range": 0.95,
    "exact": 1.0,
}

MEDIUM_BAND_SCORE = {
    "missing": 0.0,
    "generic": 0.35,
    "material_only": 0.60,
    "specific": 1.0,
}

ATTRIBUTION_BAND_SCORE = {
    "missing": 0.0,
    "unknown": 0.15,
    "culture_only": 0.35,
    "qualified": 0.55,
    "attributed": 0.75,
    "named": 1.0,
}

DESCRIPTION_BAND_SCORE = {
    "missing": 0.0,
    "stub": 0.40,
    "present": 1.0,
}

IMAGE_STATE_SCORE = {
    "present": 1.0,
    "absent": 0.0,
    "withheld_by_license": 0.0,
}

DIMENSION_ORDER = ("image", "date", "medium", "attribution", "description")

WORST_DATE_BANDS = {"missing", "undated_text", "multi_century", "century"}


def band_score_for(norm: NormalizedRecord, dimension: str) -> tuple[float, bool]:
    """Returns (band_score, weight_applied)."""
    if dimension == "image":
        state = norm.image_state
        if state == "withheld_by_license":
            return 0.0, False
        return IMAGE_STATE_SCORE[state], True
    if dimension == "date":
        return DATE_BAND_SCORE[norm.date_band], True
    if dimension == "medium":
        return MEDIUM_BAND_SCORE[norm.medium_band], True
    if dimension == "attribution":
        return ATTRIBUTION_BAND_SCORE[norm.attribution_band], True
    if dimension == "description":
        return DESCRIPTION_BAND_SCORE[norm.description_band], True
    raise ValueError(f"unknown dimension {dimension}")


def composite_score(norm: NormalizedRecord) -> tuple[int, int]:
    total_weight = 0
    weighted = 0.0
    for dim in DIMENSION_ORDER:
        score, applied = band_score_for(norm, dim)
        weight = WEIGHTS[dim]
        if applied:
            total_weight += weight
            weighted += weight * score
    if total_weight == 0:
        return 0, 0
    composite = math.floor(100 * weighted / total_weight + 0.5)
    return composite, total_weight


def n_dimensions_at_zero(norm: NormalizedRecord) -> int:
    count = 0
    for dim in DIMENSION_ORDER:
        score, applied = band_score_for(norm, dim)
        if applied and score == 0.0:
            count += 1
    return count
