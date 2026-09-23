from __future__ import annotations

from typing import Protocol


class MuseumSource(Protocol):
    source_id: str

    def fetch_cohort(self, *, size: int, mode: str = "stratified", department: str | None = None, type_: str | None = None) -> list[dict]: ...
