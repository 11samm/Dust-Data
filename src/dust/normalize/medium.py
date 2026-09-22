from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from dust.config import VOCAB_DIR
from dust.model import ArtworkRaw

MISSING_TOKENS = {
    "unknown",
    "unidentified",
    "n/a",
    "na",
    "none",
    "various",
    "various materials",
}


def _normalize_medium_text(text: str) -> str:
    s = text.strip().lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u2014", "-").replace("\u2013", "-")
    s = re.sub(r"\s+", " ", s)
    return s.rstrip(".")


def _split_parts(text: str) -> list[str]:
    return [p.strip() for p in text.split(";") if p.strip()]


@lru_cache
def _load_vocab() -> tuple[set[str], set[str], set[str], dict[str, str]]:
    path = VOCAB_DIR / "medium.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    generic = {str(x).lower() for x in data.get("generic", [])}
    material = {str(x).lower() for x in data.get("material_only", [])}
    specific = {str(x).lower() for x in data.get("specific", [])}
    aliases = {str(k).lower(): str(v).lower() for k, v in (data.get("aliases") or {}).items()}
    return generic, material, specific, aliases


def normalize_medium(raw: ArtworkRaw) -> tuple[str, str, str, bool, list[str]]:
    warnings: list[str] = []
    technique = raw.technique
    medium_raw = technique
    generic, material, specific, aliases = _load_vocab()

    if not technique or not technique.strip():
        band, canonical, unseen = _score_key("", raw, generic, material, specific, aliases)
        return band, canonical, medium_raw, unseen, warnings

    parts = _split_parts(_normalize_medium_text(technique))
    best_band = "missing"
    best_rank = -1
    best_canonical = ""
    unseen = False
    band_rank = {"missing": 0, "generic": 1, "material_only": 2, "specific": 3}

    for part in parts:
        band, canonical, part_unseen = _score_key(part, raw, generic, material, specific, aliases)
        if band_rank[band] > best_rank:
            best_rank = band_rank[band]
            best_band = band
            best_canonical = canonical
            unseen = unseen or part_unseen

    if best_band in ("missing", "generic") and _support_bump(raw, material):
        warnings.append("support materials supplied the material")
        best_band = "material_only" if best_band == "missing" else "material_only"

    return best_band, best_canonical, medium_raw, unseen, warnings


def _support_bump(raw: ArtworkRaw, material: set[str]) -> bool:
    for item in raw.support_materials:
        key = _normalize_medium_text(item)
        if key in material:
            return True
    return False


def _score_key(
    part: str,
    raw: ArtworkRaw,
    generic: set[str],
    material: set[str],
    specific: set[str],
    aliases: dict[str, str],
) -> tuple[str, str, bool]:
    if not part:
        return "missing", "", False

    if part in MISSING_TOKENS:
        return "missing", part, False

    key = aliases.get(part, part)
    if key in specific:
        return "specific", key, False
    if key in generic:
        return "generic", key, False
    if key in material:
        return "material_only", key, False

    record_type = raw.type.strip().lower()
    if record_type and key == record_type:
        return "generic", key, False

    if len(key.split()) == 1 and key in material:
        return "material_only", key, False

    if len(key.split()) == 1:
        return "generic", key, True

    return "generic", key, True
