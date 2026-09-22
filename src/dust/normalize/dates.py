from __future__ import annotations

import re

from dust.model import ArtworkRaw

BAND_ORDER = [
    "missing",
    "undated_text",
    "multi_century",
    "century",
    "generation",
    "decade",
    "circa",
    "narrow_range",
    "exact",
]

BAND_RANK = {name: i for i, name in enumerate(BAND_ORDER)}

UNDATED_RE = re.compile(
    r"^(n\.?\s*d\.?|nd|no date|unknown|undated)\.?$",
    re.IGNORECASE,
)
HEDGE_RE = re.compile(r"(^|\b)(c\.?|ca\.?|circa|about|approximately|approx\.?)(\b|\s)", re.IGNORECASE)
DECADE_WORD_RE = re.compile(r"\b(\d{3}0s|the\s+\d{3}0s)\b", re.IGNORECASE)
CENTURY_WORD_RE = re.compile(
    r"(\b\d{1,2}(st|nd|rd|th)\s+century\b|\b\d{1,2}00s\b|"
    r"\b(early|mid|late)\s+\d{1,2}(st|nd|rd|th)\s+century\b)",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(\d{1,4})\s*(bce|bc|ce|ad)?\b", re.IGNORECASE)
RANGE_RE = re.compile(
    r"(\d{1,4}\s*(?:bce|bc|ce|ad)?)\s*(\-|/|to)\s*(\d{1,4}\s*(?:bce|bc|ce|ad)?)",
    re.IGNORECASE,
)


def _weaker(a: str, b: str) -> str:
    return a if BAND_RANK[a] <= BAND_RANK[b] else b


def _span_years(earliest: int | None, latest: int | None) -> int | None:
    if earliest is None or latest is None:
        return None
    return abs(latest - earliest)


def _span_class(span: int | None) -> str | None:
    if span is None:
        return None
    if span <= 1:
        return "exact_span"
    if span <= 7:
        return "narrow_span"
    if span <= 19:
        return "decade_span"
    if span <= 49:
        return "generation_span"
    if span <= 150:
        return "century_span"
    return "multi_span"


def _span_to_band(span_class: str | None) -> str:
    if span_class is None:
        return "missing"
    return {
        "exact_span": "exact",
        "narrow_span": "narrow_range",
        "decade_span": "decade",
        "generation_span": "generation",
        "century_span": "century",
        "multi_span": "multi_century",
    }[span_class]


def _classify_string(date_str: str) -> str:
    s = date_str.strip()
    if not s:
        return "blank"
    if UNDATED_RE.match(s):
        return "undated"
    if RANGE_RE.search(s):
        return "range_word"
    if HEDGE_RE.search(s):
        return "hedged"
    if DECADE_WORD_RE.search(s):
        return "decade_word"
    if CENTURY_WORD_RE.search(s):
        return "century_word"
    if YEAR_RE.search(s) and not re.search(r"[A-Za-z]{3,}", s.replace("BCE", "").replace("BC", "")):
        return "exact_word"
    if YEAR_RE.search(s):
        return "range_word" if RANGE_RE.search(s) else "exact_word"
    if re.search(r"[A-Za-z]", s):
        return "other_text"
    return "other_text"


def _string_to_band(string_class: str, has_years: bool) -> str:
    if string_class == "blank":
        return "missing"
    if string_class == "undated":
        return "undated_text"
    if string_class == "other_text":
        return "undated_text" if not has_years else "undated_text"
    if string_class == "century_word":
        return "century"
    if string_class == "decade_word":
        return "decade"
    if string_class == "exact_word":
        return "exact"
    if string_class == "range_word":
        return "narrow_range"
    if string_class == "hedged":
        return "circa"
    return "missing"


def normalize_dates(raw: ArtworkRaw) -> tuple[str, str, str, int | None, bool, list[str]]:
    """Returns date_state, date_band, date_display, date_span_years, date_conflict, warnings."""
    warnings: list[str] = list(raw.parse_warnings)
    display = raw.creation_date
    earliest, latest = raw.creation_date_earliest, raw.creation_date_latest
    span = _span_years(earliest, latest)
    span_class = _span_class(span)
    has_years = earliest is not None and latest is not None

    string_class = _classify_string(display)
    span_band = _span_to_band(span_class)
    has_years = earliest is not None and latest is not None

    date_conflict = False

    if string_class == "blank" and not has_years:
        return "missing", "missing", display, span, False, warnings

    if string_class == "undated":
        return "present", "undated_text", display, span, False, warnings

    if string_class == "blank" and has_years:
        warnings.append("display date missing")
        band = span_band
        state = "present" if band != "missing" else "missing"
        return state, band, display, span, False, warnings

    if string_class == "other_text" and not has_years:
        return "present", "undated_text", display, span, False, warnings

    string_band = _string_to_band(string_class, has_years)
    band = _weaker(string_band, span_band)

    if string_class == "century_word" and span_class == "exact_span" and has_years:
        date_conflict = True
        band = "century"

    if string_class == "century_word" and span_class in ("generation_span", "decade_span"):
        if BAND_RANK[span_band] > BAND_RANK[string_band]:
            band = span_band

    if string_class == "hedged":
        band = _weaker("circa", span_band)

    if string_class == "range_word" and not HEDGE_RE.search(display):
        band = _weaker("narrow_range", span_band)

    if string_class == "exact_word" and HEDGE_RE.search(display):
        band = "circa"

    if band == "missing" and has_years:
        band = span_band

    state = "present" if band != "missing" else "missing"
    return state, band, display, span, date_conflict, warnings
