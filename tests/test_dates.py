import pytest

from dust.model import parse_artwork_raw
from dust.normalize.dates import normalize_dates


def _date(creation_date, earliest=None, latest=None):
    raw = parse_artwork_raw(
        {
            "id": 1,
            "accession_number": "TEST.1",
            "creation_date": creation_date,
            "creation_date_earliest": earliest,
            "creation_date_latest": latest,
        }
    )
    _state, band, _display, _span, conflict, _warnings = normalize_dates(raw)
    return band, conflict


@pytest.mark.parametrize(
    "creation_date,earliest,latest,expected_band,expected_conflict",
    [
        ("", None, None, "missing", False),
        ("n.d.", None, None, "undated_text", False),
        ("19th century", 1800, 1899, "century", False),
        ("1500s", 1525, 1599, "century", False),
        ("500s", 500, 599, "century", False),
        ("c. 1550-1650", 1550, 1650, "century", False),
        ("late 19th century", 1870, 1899, "generation", False),
        ("1890s", 1890, 1899, "decade", False),
        ("c. 1890", 1888, 1892, "circa", False),
        ("c. 1890", 1890, 1890, "circa", False),
        ("1890-1895", 1890, 1895, "narrow_range", False),
        ("1890", 1890, 1890, "exact", False),
        ("460 BCE", -460, -460, "exact", False),
        ("19th century", 1890, 1890, "century", True),
        ("", 1890, 1890, "exact", False),
        ("Qing dynasty", None, None, "undated_text", False),
    ],
)
def test_date_bands(creation_date, earliest, latest, expected_band, expected_conflict):
    band, conflict = _date(creation_date, earliest, latest)
    assert band == expected_band
    assert conflict is expected_conflict
