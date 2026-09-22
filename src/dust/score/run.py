from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from dust.config import CACHE_DIR, VOCAB_DIR, WEIGHTS
from dust.model import ArtworkRaw, CohortBundle, CohortMeta, DimensionScore, ScoredRecord, parse_artwork_raw
from dust.normalize import normalize_record
from dust.score.explain import build_gaps, gap_for_dimension, gap_flags
from dust.score.policy import DIMENSION_ORDER, band_score_for, composite_score, n_dimensions_at_zero


def policy_fingerprint() -> str:
    source_root = Path(__file__).resolve().parents[1]
    policy_inputs = [
        VOCAB_DIR / "medium.yml",
        VOCAB_DIR / "attribution.yml",
        source_root / "normalize" / "dates.py",
        source_root / "normalize" / "medium.py",
        source_root / "normalize" / "attribution.py",
        Path(__file__).resolve().parent / "policy.py",
    ]
    policy_bytes = b"".join(path.read_bytes() for path in policy_inputs)
    weights = json.dumps(WEIGHTS, sort_keys=True).encode("utf-8")
    return hashlib.sha256(policy_bytes + weights).hexdigest()


def _band_for_dimension(norm, dimension: str) -> str:
    if dimension == "image":
        return norm.image_state
    if dimension == "date":
        return norm.date_band
    if dimension == "medium":
        return norm.medium_band
    if dimension == "attribution":
        return norm.attribution_band
    if dimension == "description":
        return norm.description_band
    raise ValueError(dimension)


def score_one(raw: ArtworkRaw) -> ScoredRecord:
    norm = normalize_record(raw)
    gaps = build_gaps(norm)
    composite, denom = composite_score(norm)
    n_zero = n_dimensions_at_zero(norm)

    from dust.config import WEIGHTS

    dimensions: list[DimensionScore] = []
    for dim in DIMENSION_ORDER:
        band_score, applied = band_score_for(norm, dim)
        weight = WEIGHTS[dim]
        contribution = weight * band_score if applied else 0.0
        dimensions.append(
            DimensionScore(
                dimension_id=dim,
                band=_band_for_dimension(norm, dim),
                band_score=band_score,
                weight=weight,
                weight_applied=applied,
                contribution=contribution,
                gap=gap_for_dimension(norm, dim),
            )
        )

    return ScoredRecord(
        raw=raw,
        normalized=norm,
        dimensions=dimensions,
        composite=composite,
        composite_denominator=denom,
        n_dimensions_at_zero=n_zero,
        gaps=gaps,
    )


def _unseen_terms(records: list[ScoredRecord]) -> pd.DataFrame:
    medium_counter: Counter[str] = Counter()
    medium_example: dict[str, str] = {}
    qual_counter: Counter[str] = Counter()
    qual_example: dict[str, str] = {}

    for rec in records:
        norm = rec.normalized
        if norm.unseen_medium and norm.medium_canonical:
            key = norm.medium_canonical
            medium_counter[key] += 1
            medium_example.setdefault(key, norm.accession_number)
        if norm.unseen_qualifier and norm.qualifier_raw:
            key = norm.qualifier_raw
            qual_counter[key] += 1
            qual_example.setdefault(key, norm.accession_number)

    rows = []
    for term, count in medium_counter.most_common():
        rows.append(
            {"term": term, "kind": "medium", "count": count, "example_accession": medium_example[term]}
        )
    for term, count in qual_counter.most_common():
        rows.append(
            {"term": term, "kind": "qualifier", "count": count, "example_accession": qual_example[term]}
        )
    return pd.DataFrame(rows)


def _write_unseen_csv(df: pd.DataFrame) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / "unseen_terms.csv"
    if df.empty:
        df = pd.DataFrame(columns=["term", "kind", "count", "example_accession"])
    df.to_csv(path, index=False)


def score_artworks(raw_records: list[dict]) -> CohortBundle:
    scored: list[ScoredRecord] = []
    for item in raw_records:
        try:
            raw = parse_artwork_raw(item)
            scored.append(score_one(raw))
        except ValueError:
            continue

    records_map = {str(r.raw.accession_number): r for r in scored}
    frame = _build_frame(scored)
    unseen = _unseen_terms(scored)
    _write_unseen_csv(unseen)

    meta = CohortMeta(
        mode="unknown",
        size=len(scored),
        department=None,
        type=None,
        fetched_at="",
        cache_path="",
        banner="",
    )
    return CohortBundle(
        frame=frame,
        records=records_map,
        meta=meta,
        policy_hash=policy_fingerprint(),
        unseen_terms=unseen,
    )


def _build_frame(scored: list[ScoredRecord]) -> pd.DataFrame:
    rows = []
    for rec in scored:
        norm = rec.normalized
        flags = gap_flags(norm)
        rows.append(
            {
                "id": norm.id,
                "accession_number": norm.accession_number,
                "title": norm.title,
                "url": norm.url,
                "department": norm.department,
                "type": norm.type,
                "record_type": norm.record_type,
                "share_license_status": norm.share_license_status,
                "updated_at": norm.updated_at,
                "composite": rec.composite,
                "n_dimensions_at_zero": rec.n_dimensions_at_zero,
                "gaps_display": "; ".join(rec.gaps),
                "image_state": norm.image_state,
                "date_state": norm.date_state,
                "date_band": norm.date_band,
                "medium_band": norm.medium_band,
                "attribution_band": norm.attribution_band,
                "description_band": norm.description_band,
                "date_conflict": norm.date_conflict,
                "attribution_label": norm.attribution_label,
                "date_display": norm.date_display,
                "medium_raw": norm.medium_raw,
                **flags,
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(
            by=["composite", "n_dimensions_at_zero", "accession_number"],
            ascending=[True, False, True],
        ).reset_index(drop=True)
    return df


def load_cohort(
    cache_path: Path | None = None,
    meta: CohortMeta | None = None,
) -> CohortBundle:
    from dust.api.cache import read_cache

    if cache_path is None:
        raise ValueError("cache_path required")

    payload = read_cache(cache_path)
    records_raw = payload.get("records") or []
    bundle = score_artworks(records_raw)
    bundle.policy_hash = policy_fingerprint()

    if meta is None:
        cohort = payload.get("cohort") or {}
        fetched = payload.get("fetched_at", "")
        mode = cohort.get("mode", "stratified")
        size = cohort.get("size", len(records_raw))
        dept = cohort.get("department")
        typ = cohort.get("type")
        banner = _format_banner(mode, size, fetched, dept, typ)
        meta = CohortMeta(
            mode=mode,
            size=size,
            department=dept,
            type=typ,
            fetched_at=fetched,
            cache_path=str(cache_path),
            banner=banner,
        )
    bundle.meta = meta
    return bundle


def _format_banner(mode: str, size: int, fetched_at: str, department: str | None, typ: str | None) -> str:
    date_part = fetched_at[:10] if fetched_at else "unknown date"
    if mode == "department" and department:
        return f"{department}, first {size} returned by the API, fetched {date_part}"
    if mode == "type" and typ:
        return f"Type {typ}, first {size} returned by the API, fetched {date_part}"
    return f"{size} records, stratified by department, fetched {date_part}"
