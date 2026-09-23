import pandas as pd

from dust.config import QUEUE_PAGE_SIZE, TYPES
from dust.ui.queue import _format_band_score, _row_key, paginate_frame


def test_paginate_clamps_page():
    frame = pd.DataFrame({"accession_number": [str(i) for i in range(20)]})
    slice0, pages, page = paginate_frame(frame, 0, page_size=15)
    assert pages == 2
    assert page == 0
    assert len(slice0) == 15

    slice1, _, page1 = paginate_frame(frame, 99, page_size=15)
    assert page1 == 1
    assert len(slice1) == 5


def test_queue_page_size_is_fifteen():
    assert QUEUE_PAGE_SIZE == 15


def test_row_key_is_stable_and_distinguishes_punctuation():
    assert _row_key("cleveland:1939.509").startswith("qrow_cleveland_1939_509_")
    assert _row_key("cleveland:1939.509") == _row_key("cleveland:1939.509")
    assert _row_key("cleveland:1939.509") != _row_key("cleveland:1939-509")


def test_band_score_display_uses_percentage_scale():
    assert _format_band_score(1.0) == "100/100"
    assert _format_band_score(0.35) == "35/100"


def test_types_include_appendix_c_values():
    assert "Painting" in TYPES
    assert "Print" in TYPES
    assert "Photograph" in TYPES
    assert "Sculpture" in TYPES
    assert len(TYPES) >= 60
    assert len(TYPES) == len(set(TYPES))
