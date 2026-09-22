from __future__ import annotations

import time
from typing import Any

import httpx

from dust.config import API_BASE, FIELDS

USER_AGENT = "DustAndData/1.0 (metadata completeness triage)"


class ApiClient:
    def __init__(self, timeout: float = 20.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries

    def get_artworks(
        self,
        *,
        limit: int = 1,
        skip: int = 0,
        department: str | None = None,
        type_: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "limit": limit,
            "skip": skip,
            "fields": ",".join(FIELDS),
        }
        if department:
            params["department"] = department
        if type_:
            params["type"] = type_

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout, headers={"User-Agent": USER_AGENT}) as client:
                    response = client.get(API_BASE, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "retryable", request=response.request, response=response
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                if attempt + 1 >= self.max_retries:
                    break
                time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def department_total(self, department: str) -> int:
        data = self.get_artworks(limit=1, department=department)
        info = data.get("info") or {}
        return int(info.get("total") or 0)

    def fetch_department_records(
        self,
        department: str,
        slots: int,
        *,
        skip: int = 0,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        offset = skip
        while len(records) < slots:
            batch = min(1000, slots - len(records))
            data = self.get_artworks(limit=batch, skip=offset, department=department)
            chunk = data.get("data") or []
            if not chunk:
                break
            records.extend(chunk)
            offset += len(chunk)
            if len(chunk) < batch:
                break
        return records[:slots]

    def type_total(self, type_: str) -> int:
        data = self.get_artworks(limit=1, type_=type_)
        info = data.get("info") or {}
        return int(info.get("total") or 0)

    def fetch_type_records(self, type_: str, slots: int, *, skip: int = 0) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        offset = skip
        while len(records) < slots:
            batch = min(1000, slots - len(records))
            data = self.get_artworks(limit=batch, skip=offset, type_=type_)
            chunk = data.get("data") or []
            if not chunk:
                break
            records.extend(chunk)
            offset += len(chunk)
            if len(chunk) < batch:
                break
        return records[:slots]
