from dust.model import parse_artwork_raw
from dust.normalize.description import normalize_description


def test_description_bands():
    raw = parse_artwork_raw({"id": 1, "accession_number": "T", "description": ""})
    assert normalize_description(raw) == ("missing", 0)

    raw = parse_artwork_raw({"id": 1, "accession_number": "T", "description": "See inscription."})
    band, chars = normalize_description(raw)
    assert band == "stub"
    assert chars < 40

    text = " ".join(["word"] * 10)
    raw = parse_artwork_raw({"id": 1, "accession_number": "T", "description": text})
    band, _chars = normalize_description(raw)
    assert band == "present"
