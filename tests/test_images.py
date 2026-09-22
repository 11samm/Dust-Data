import pytest

from dust.model import parse_artwork_raw
from dust.normalize.images import normalize_image


@pytest.mark.parametrize(
    "images,license_status,expected",
    [
        ({"web": {"url": "https://example.com/x.jpg"}}, "CC0", "present"),
        ({}, "Copyrighted", "withheld_by_license"),
        ({}, "CC0", "absent"),
        (None, "Other", "absent"),
    ],
)
def test_image_state(images, license_status, expected):
    payload = {
        "id": 1,
        "accession_number": "TEST.1",
        "share_license_status": license_status,
    }
    if images is not None:
        payload["images"] = images
    raw = parse_artwork_raw(payload)
    assert normalize_image(raw) == expected
