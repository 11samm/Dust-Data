from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _absent(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return None
    return None


def _coerce_text(value: Any) -> str:
    if _absent(value):
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item).strip() for item in value if not _absent(item))
    return str(value).strip()


@dataclass
class CreatorRaw:
    description: str = ""
    qualifier: str = ""
    role: str = ""
    birth_year: int | None = None
    death_year: int | None = None


@dataclass
class ArtworkRaw:
    id: int
    accession_number: str
    title: str = ""
    url: str = ""
    department: str = ""
    collection: str = ""
    type: str = ""
    record_type: str = ""
    share_license_status: str = ""
    updated_at: str = ""
    creation_date: str = ""
    creation_date_earliest: int | None = None
    creation_date_latest: int | None = None
    date_text: str = ""
    creators: list[CreatorRaw] = field(default_factory=list)
    culture: str = ""
    technique: str = ""
    support_materials: list[str] = field(default_factory=list)
    description: str = ""
    images: dict[str, Any] = field(default_factory=dict)
    source: dict[str, Any] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class NormalizedRecord:
    id: int
    accession_number: str
    title: str
    url: str
    department: str
    type: str
    record_type: str
    share_license_status: str
    updated_at: str

    image_state: str
    date_state: str
    date_band: str
    date_span_years: int | None
    date_display: str
    date_conflict: bool

    medium_band: str
    medium_canonical: str
    medium_raw: str

    attribution_band: str
    attribution_label: str
    qualifier_raw: str

    description_band: str
    description_chars: int

    parse_warnings: list[str] = field(default_factory=list)
    unseen_medium: bool = False
    unseen_qualifier: bool = False


@dataclass
class DimensionScore:
    dimension_id: str
    band: str
    band_score: float
    weight: int
    weight_applied: bool
    contribution: float
    gap: str | None = None


@dataclass
class ScoredRecord:
    raw: ArtworkRaw
    normalized: NormalizedRecord
    dimensions: list[DimensionScore]
    composite: int
    composite_denominator: int
    n_dimensions_at_zero: int
    gaps: list[str]


@dataclass
class CohortMeta:
    mode: str
    size: int
    department: str | None
    type: str | None
    fetched_at: str
    cache_path: str
    banner: str


@dataclass
class CohortBundle:
    frame: Any
    records: dict[str, ScoredRecord]
    meta: CohortMeta
    policy_hash: str
    unseen_terms: Any


def parse_artwork_raw(data: dict[str, Any]) -> ArtworkRaw:
    warnings: list[str] = []
    earliest = _coerce_int(data.get("creation_date_earliest"))
    latest = _coerce_int(data.get("creation_date_latest"))
    if data.get("creation_date_earliest") not in (None, "") and earliest is None:
        warnings.append("creation_date_earliest unparseable")
    if data.get("creation_date_latest") not in (None, "") and latest is None:
        warnings.append("creation_date_latest unparseable")

    creators_raw = data.get("creators") or []
    creators: list[CreatorRaw] = []
    for c in creators_raw:
        if not isinstance(c, dict):
            continue
        creators.append(
            CreatorRaw(
                description="" if _absent(c.get("description")) else str(c.get("description")).strip(),
                qualifier="" if _absent(c.get("qualifier")) else str(c.get("qualifier")).strip(),
                role="" if _absent(c.get("role")) else str(c.get("role")).strip(),
                birth_year=_coerce_int(c.get("birth_year")),
                death_year=_coerce_int(c.get("death_year")),
            )
        )

    support = data.get("support_materials") or []
    if support is None:
        support = []
    support_list = [str(x).strip() for x in support if not _absent(x)]

    images = data.get("images")
    if images is None:
        images = {}
    if not isinstance(images, dict):
        images = {}

    art_id = data.get("id")
    if art_id is None:
        raise ValueError("artwork missing id")
    try:
        art_id_int = int(art_id)
    except (TypeError, ValueError) as e:
        raise ValueError("artwork id not an integer") from e

    acc = data.get("accession_number")
    if _absent(acc):
        acc = str(art_id_int)

    return ArtworkRaw(
        id=art_id_int,
        accession_number=str(acc).strip(),
        title="" if _absent(data.get("title")) else str(data.get("title")).strip(),
        url="" if _absent(data.get("url")) else str(data.get("url")).strip(),
        department="" if _absent(data.get("department")) else str(data.get("department")).strip(),
        collection="" if _absent(data.get("collection")) else str(data.get("collection")).strip(),
        type="" if _absent(data.get("type")) else str(data.get("type")).strip(),
        record_type="" if _absent(data.get("record_type")) else str(data.get("record_type")).strip(),
        share_license_status="" if _absent(data.get("share_license_status")) else str(data.get("share_license_status")).strip(),
        updated_at="" if _absent(data.get("updated_at")) else str(data.get("updated_at")).strip(),
        creation_date="" if _absent(data.get("creation_date")) else str(data.get("creation_date")).strip(),
        creation_date_earliest=earliest,
        creation_date_latest=latest,
        date_text="" if _absent(data.get("date_text")) else str(data.get("date_text")).strip(),
        creators=creators,
        culture=_coerce_text(data.get("culture")),
        technique="" if _absent(data.get("technique")) else str(data.get("technique")).strip(),
        support_materials=support_list,
        description="" if _absent(data.get("description")) else str(data.get("description")).strip(),
        images=images,
        source=dict(data),
        parse_warnings=warnings,
    )
