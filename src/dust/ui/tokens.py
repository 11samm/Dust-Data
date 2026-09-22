SEVERITY = {
    "poor": {"ink": "#9C4A3C", "fill": "#F8E8E4"},
    "partial": {"ink": "#8A6420", "fill": "#F8F0DC"},
    "strong": {"ink": "#1F6B56", "fill": "#E3F2EC"},
    "withheld": {"ink": "#4E5C6A", "fill": "#E8EDF1"},
}

DIMENSION = {
    "image": {"label": "#3E5278", "tint": "#E6EAF2"},
    "date": {"label": "#7A5340", "tint": "#F3EBE4"},
    "medium": {"label": "#3E6156", "tint": "#E5F0EB"},
    "attribution": {"label": "#5E486C", "tint": "#EFE8F3"},
    "description": {"label": "#2F5C70", "tint": "#E4EEF3"},
}


def severity_for_score(value: float) -> str:
    if value < 50:
        return "poor"
    if value < 75:
        return "partial"
    return "strong"


def severity_for_rate(rate_pct: float) -> str:
    return severity_for_score(rate_pct)
