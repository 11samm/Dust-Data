from dust.model import CreatorRaw, parse_artwork_raw
from dust.normalize.attribution import normalize_attribution


def test_attribution_named():
    raw = parse_artwork_raw(
        {
            "id": 1,
            "accession_number": "T",
            "creators": [{"description": "Song Xu", "qualifier": "", "role": "artist"}],
        }
    )
    band, label, *_ = normalize_attribution(raw)
    assert band == "named"
    assert label == "Song Xu"


def test_attribution_qualified():
    raw = parse_artwork_raw(
        {
            "id": 1,
            "accession_number": "T",
            "creators": [{"description": "Rembrandt", "qualifier": "circle of", "role": ""}],
        }
    )
    band, label, *_ = normalize_attribution(raw)
    assert band == "qualified"
    assert "circle of" in label.lower()


def test_unmapped_qualifier_not_named():
    raw = parse_artwork_raw(
        {
            "id": 1,
            "accession_number": "T",
            "creators": [{"description": "Jane Doe", "qualifier": "copy after", "role": ""}],
        }
    )
    band, *_ = normalize_attribution(raw)
    assert band == "attributed"


def test_null_creators_and_images_do_not_raise():
    raw = parse_artwork_raw(
        {
            "id": 1,
            "accession_number": "T",
            "creators": None,
            "images": None,
            "culture": "",
        }
    )
    band, *_ = normalize_attribution(raw)
    assert band == "missing"


def test_culture_list_is_displayed_as_plain_text():
    raw = parse_artwork_raw(
        {
            "id": 2,
            "accession_number": "1918.926",
            "creators": [],
            "culture": ["Frankish, Migration period"],
        }
    )
    band, label, *_ = normalize_attribution(raw)
    assert band == "culture_only"
    assert label == "Frankish, Migration period"
