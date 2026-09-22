from dust.model import parse_artwork_raw
from dust.normalize import normalize_record


def test_normalize_record_roundtrip():
    raw = parse_artwork_raw(
        {
            "id": 1953.129,
            "accession_number": "1953.129",
            "title": "Test",
            "creation_date": "1890",
            "creation_date_earliest": 1890,
            "creation_date_latest": 1890,
            "technique": "oil on canvas",
            "creators": [{"description": "Artist Name Here", "qualifier": "by"}],
            "description": " ".join(["word"] * 12),
            "images": {"web": {"url": "https://example.com/a.jpg"}},
            "share_license_status": "CC0",
        }
    )
    norm = normalize_record(raw)
    assert norm.date_band == "exact"
    assert norm.medium_band == "specific"
    assert norm.attribution_band == "named"
    assert norm.description_band == "present"
    assert norm.image_state == "present"
