import re

from dust.model import parse_artwork_raw
from dust.score.explain import build_gaps
from dust.score.policy import composite_score
from dust.score.run import score_one


def test_composite_perfect_record():
    raw = parse_artwork_raw(
        {
            "id": 1,
            "accession_number": "T.1",
            "creation_date": "1890",
            "creation_date_earliest": 1890,
            "creation_date_latest": 1890,
            "technique": "oil on canvas",
            "creators": [{"description": "Jane Doe Smith", "qualifier": ""}],
            "description": " ".join(["word"] * 12),
            "images": {"web": {"url": "https://example.com/a.jpg"}},
            "share_license_status": "CC0",
        }
    )
    scored = score_one(raw)
    assert scored.composite == 100
    assert scored.gaps == []


def test_copyrighted_image_weight_excluded():
    raw = parse_artwork_raw(
        {
            "id": 2,
            "accession_number": "T.2",
            "creation_date": "1890",
            "creation_date_earliest": 1890,
            "creation_date_latest": 1890,
            "technique": "oil on canvas",
            "creators": [{"description": "Jane Doe Smith", "qualifier": ""}],
            "description": " ".join(["word"] * 12),
            "images": {},
            "share_license_status": "Copyrighted",
        }
    )
    scored = score_one(raw)
    assert scored.composite == 100
    assert scored.composite_denominator == 85
    assert any("withheld by license" in g for g in scored.gaps)


def test_gap_text_has_raw_not_band_code():
    raw = parse_artwork_raw(
        {
            "id": 3,
            "accession_number": "T.3",
            "creation_date": "19th century",
            "creation_date_earliest": 1800,
            "creation_date_latest": 1899,
            "technique": "mixed media",
            "type": "Mixed Media",
        }
    )
    scored = score_one(raw)
    joined = " ".join(scored.gaps).lower()
    assert "century" in joined
    assert "century-level" in joined or "century" in joined
    assert "multi_century" not in joined


def test_gap_contains_raw_date_string():
    raw = parse_artwork_raw(
        {
            "id": 4,
            "accession_number": "T.4",
            "creation_date": "19th century",
            "creation_date_earliest": 1800,
            "creation_date_latest": 1899,
        }
    )
    gaps = build_gaps(score_one(raw).normalized)
    assert any('19th century' in g for g in gaps)


def test_half_point_composite_rounds_up():
    raw = parse_artwork_raw(
        {
            "id": 5,
            "accession_number": "T.5",
            "creation_date": "unknown",
            "technique": "mixed media",
            "type": "Mixed Media",
            "creators": [],
            "culture": "French",
            "description": "",
            "images": {"web": {"url": "https://example.com/a.jpg"}},
            "share_license_status": "CC0",
        }
    )
    assert score_one(raw).composite == 35


def test_eagle_fibula_scoring_regression():
    raw = parse_artwork_raw(
        {
            "id": 99387,
            "accession_number": "1918.926",
            "title": "Eagle-Shaped Fibula",
            "creation_date": "500s",
            "creation_date_earliest": 500,
            "creation_date_latest": 599,
            "culture": ["Frankish, Migration period"],
            "technique": "bronze with traces of gilding and silver, and garnets",
            "type": "Jewelry",
            "description": None,
            "images": {"web": {"url": "https://example.com/fibula.jpg"}},
            "share_license_status": "CC0",
            "creators": [],
        }
    )
    scored = score_one(raw)
    assert scored.normalized.date_band == "century"
    assert scored.normalized.medium_band == "specific"
    assert scored.normalized.attribution_label == "Frankish, Migration period"
    assert scored.composite == 55
