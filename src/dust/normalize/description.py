from __future__ import annotations

import re

from dust.model import ArtworkRaw


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def normalize_description(raw: ArtworkRaw) -> tuple[str, int]:
    text = raw.description
    if not text or not text.strip():
        return "missing", 0

    chars = len(text.strip())
    words = _word_count(text)
    if words < 8 or chars < 40:
        return "stub", chars
    return "present", chars
