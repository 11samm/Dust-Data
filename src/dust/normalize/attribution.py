from __future__ import annotations

import re
from functools import lru_cache

import yaml

from dust.config import VOCAB_DIR
from dust.model import ArtworkRaw, CreatorRaw

BAND_RANK = {
    "missing": 0,
    "unknown": 1,
    "culture_only": 2,
    "qualified": 3,
    "attributed": 4,
    "named": 5,
}

CEILING_RANK = {
    "missing": 0,
    "unknown": 1,
    "culture_only": 2,
    "qualified": 3,
    "attributed": 4,
    "named": 5,
}


def _norm_qualifier(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


@lru_cache
def _load_vocab() -> tuple[dict[str, str], set[str], set[str]]:
    data = yaml.safe_load((VOCAB_DIR / "attribution.yml").read_text(encoding="utf-8"))
    ceilings_raw = data.get("ceilings") or {}
    ceilings = {_norm_qualifier(str(k)): str(v) for k, v in ceilings_raw.items()}
    unknown = {str(x).strip().lower() for x in data.get("unknown_phrases", [])}
    culture = {str(x).strip().lower() for x in data.get("culture_tokens", [])}
    return ceilings, unknown, culture


def _is_unknown_description(desc: str, unknown_phrases: set[str]) -> bool:
    d = desc.strip().lower()
    return d in unknown_phrases


def _name_check(description: str, culture_tokens: set[str]) -> bool:
    desc = description.strip()
    if not desc:
        return False
    lower = desc.lower()
    if lower in culture_tokens:
        return False

    if re.search(r"\(\s*[^)]*\d{3,4}", desc):
        tokens = re.findall(r"[A-Za-z]+", desc)
        if len(tokens) >= 1:
            return True

    tokens = re.findall(r"[A-Za-z]+", desc)
    if len(tokens) >= 2:
        if all(t.lower() in culture_tokens for t in tokens):
            return False
        return True
    return False


def _creator_band(
    creator: CreatorRaw,
    ceilings: dict[str, str],
    unknown_phrases: set[str],
    culture_tokens: set[str],
) -> tuple[str, str, str, bool, list[str]]:
    warnings: list[str] = []
    desc = creator.description
    qual_raw = creator.qualifier
    qual_norm = _norm_qualifier(qual_raw)

    if _is_unknown_description(desc, unknown_phrases):
        return "unknown", desc, qual_raw, False, warnings

    unseen = False
    if qual_norm in ceilings:
        ceiling = ceilings[qual_norm]
    else:
        ceiling = "attributed"
        if qual_norm:
            unseen = True
            warnings.append(f"unmapped qualifier: {qual_raw}")

    if ceiling == "named" and not _name_check(desc, culture_tokens):
        if qual_norm:
            return "qualified", desc, qual_raw, unseen, warnings
        return "culture_only", desc, qual_raw, unseen, warnings

    band = ceiling
    if ceiling == "named" and not creator.role.strip():
        warnings.append("role missing")

    label = desc
    if qual_raw.strip():
        label = f"{qual_raw} {desc}".strip()

    return band, label, qual_raw, unseen, warnings


def min_band(a: str, b: str) -> str:
    return a if CEILING_RANK[a] <= CEILING_RANK[b] else b


def normalize_attribution(raw: ArtworkRaw) -> tuple[str, str, str, bool, list[str]]:
    ceilings, unknown_phrases, culture_tokens = _load_vocab()
    warnings: list[str] = []
    unseen = False

    if not raw.creators:
        if raw.culture.strip():
            return "culture_only", raw.culture.strip(), "", False, warnings
        return "missing", "", "", False, warnings

    best_band = "missing"
    best_label = ""
    best_qual = ""

    for creator in raw.creators:
        band, label, qual, creator_unseen, creator_warnings = _creator_band(
            creator, ceilings, unknown_phrases, culture_tokens
        )
        warnings.extend(creator_warnings)
        unseen = unseen or creator_unseen
        if BAND_RANK[band] > BAND_RANK[best_band]:
            best_band = band
            best_label = label
            best_qual = qual
        elif BAND_RANK[band] == BAND_RANK[best_band] and not best_label:
            best_label = label
            best_qual = qual

    return best_band, best_label, best_qual, unseen, warnings
