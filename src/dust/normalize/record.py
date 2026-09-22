from __future__ import annotations

from dust.model import ArtworkRaw, NormalizedRecord
from dust.normalize.attribution import normalize_attribution
from dust.normalize.dates import normalize_dates
from dust.normalize.description import normalize_description
from dust.normalize.images import normalize_image
from dust.normalize.medium import normalize_medium


def normalize_record(raw: ArtworkRaw) -> NormalizedRecord:
    image_state = normalize_image(raw)
    date_state, date_band, date_display, date_span, date_conflict, date_warnings = normalize_dates(raw)
    medium_band, medium_canonical, medium_raw, unseen_medium, medium_warnings = normalize_medium(raw)
    attribution_band, attribution_label, qualifier_raw, unseen_qualifier, attr_warnings = normalize_attribution(
        raw
    )
    description_band, description_chars = normalize_description(raw)

    warnings: list[str] = []
    warnings.extend(date_warnings)
    warnings.extend(medium_warnings)
    warnings.extend(attr_warnings)
    warnings.extend(raw.parse_warnings)

    return NormalizedRecord(
        id=raw.id,
        accession_number=raw.accession_number,
        title=raw.title,
        url=raw.url,
        department=raw.department,
        type=raw.type,
        record_type=raw.record_type,
        share_license_status=raw.share_license_status,
        updated_at=raw.updated_at,
        image_state=image_state,
        date_state=date_state,
        date_band=date_band,
        date_span_years=date_span,
        date_display=date_display,
        date_conflict=date_conflict,
        medium_band=medium_band,
        medium_canonical=medium_canonical,
        medium_raw=medium_raw,
        attribution_band=attribution_band,
        attribution_label=attribution_label,
        qualifier_raw=qualifier_raw,
        description_band=description_band,
        description_chars=description_chars,
        parse_warnings=warnings,
        unseen_medium=unseen_medium,
        unseen_qualifier=unseen_qualifier,
    )
