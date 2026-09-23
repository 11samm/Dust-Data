from __future__ import annotations

from dust.api.client import ApiClient
from dust.api.cohort import fetch_filtered_cohort


class ClevelandSource:
    source_id = "cleveland"

    def fetch_cohort(self, *, size: int, mode: str = "stratified", department: str | None = None, type_: str | None = None) -> list[dict]:
        return fetch_filtered_cohort(ApiClient(), mode=mode, department=department, type_=type_, limit=size)
