from dust.model import parse_artwork_raw
from dust.normalize.medium import normalize_medium


def test_medium_specific_and_alias():
    raw = parse_artwork_raw(
        {"id": 1, "accession_number": "T", "technique": "Oil on Canvas", "type": "Painting"}
    )
    band, canonical, _raw, unseen, _w = normalize_medium(raw)
    assert band == "specific"
    assert canonical == "oil on canvas"
    assert unseen is False

    raw2 = parse_artwork_raw(
        {"id": 2, "accession_number": "T2", "technique": "oil on canvas", "type": "Painting"}
    )
    _b, canonical2, *_ = normalize_medium(raw2)
    assert canonical2 == canonical


def test_medium_generic_type_match():
    raw = parse_artwork_raw({"id": 1, "accession_number": "T", "technique": "painting", "type": "Painting"})
    band, *_ = normalize_medium(raw)
    assert band == "generic"


def test_detailed_bronze_medium_is_specific():
    raw = parse_artwork_raw(
        {
            "id": 3,
            "accession_number": "1918.926",
            "technique": "bronze with traces of gilding and silver, and garnets",
            "type": "Jewelry",
        }
    )
    band, canonical, _raw, unseen, _warnings = normalize_medium(raw)
    assert band == "specific"
    assert canonical == "bronze with traces of gilding and silver, and garnets"
    assert unseen is False
