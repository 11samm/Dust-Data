from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dust.config import CACHE_TTL_HOURS, COHORT_SIZE, FIELDS


def cohort_key(
    mode: str,
    size: int = COHORT_SIZE,
    department: str | None = None,
    type_: str | None = None,
    source: str = "cleveland",
) -> str:
    payload = {
        "department": department,
        "fields": sorted(FIELDS),
        "mode": mode,
        "size": size,
        "type": type_,
    }
    if source != "cleveland":
        payload["source"] = source
        payload["fields"] = []
        payload["schema_version"] = 5
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def cache_path_for_key(key: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"cohort-{key}.json"


def read_cache(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def cache_is_fresh(path: Path, ttl_hours: int = CACHE_TTL_HOURS) -> bool:
    if not path.exists():
        return False
    payload = read_cache(path)
    fetched = payload.get("fetched_at")
    if not fetched:
        return False
    try:
        ts = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
    except ValueError:
        return False
    age = datetime.now(timezone.utc) - ts
    return age.total_seconds() < ttl_hours * 3600
