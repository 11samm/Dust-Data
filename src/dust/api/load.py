from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dust.api.cache import cache_path_for_key, cohort_key, read_cache, write_cache
from dust.api.client import ApiClient
from dust.api.cohort import fetch_filtered_cohort
from dust.config import API_BASE, CACHE_DIR, COHORT_SIZE
from dust.score.run import load_cohort, policy_fingerprint


def ensure_cohort(
    *,
    mode: str = "stratified",
    department: str | None = None,
    type_: str | None = None,
    size: int = COHORT_SIZE,
    force_refresh: bool = False,
) -> Path:
    from dust.api.cache import cache_is_fresh

    key = cohort_key(mode, size=size, department=department, type_=type_)
    path = cache_path_for_key(key, CACHE_DIR)

    if not force_refresh and cache_is_fresh(path):
        return path

    client = ApiClient()
    records = fetch_filtered_cohort(
        client, mode=mode, department=department, type_=type_, limit=size
    )
    payload = {
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "cohort": {
            "mode": mode,
            "size": size,
            "department": department,
            "type": type_,
        },
        "cohort_key": key,
        "policy_hash": policy_fingerprint(),
        "api": API_BASE,
        "records": records,
    }
    write_cache(path, payload)
    return path


def load_or_fetch_cohort(**kwargs):
    path = ensure_cohort(**kwargs)
    return load_cohort(path)
