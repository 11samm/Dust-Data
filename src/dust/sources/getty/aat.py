"""Conservative, cached exact-label AAT reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from dust.config import CACHE_DIR

ENDPOINT = "https://services.getty.edu/vocab/reconcile/"


class AATResolver:
    def __init__(self, cache_path: Path | None = None, client: httpx.Client | None = None):
        self.cache_path = cache_path or CACHE_DIR / "aat.json"
        self.client = client
        try:
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.cache = {}

    def resolve(self, term: str) -> dict[str, str]:
        key = " ".join(term.lower().split())
        if not key:
            return {"role": "medium", "label": term, "uri": "", "match_source": "unresolved", "resolution_status": "unresolved"}
        if key in self.cache:
            cached = self.cache[key]
            status = cached.get("resolution_status") or ("needs_review" if cached.get("uri") else "unresolved")
            return {**cached, "match_source": "aat_cache", "resolution_status": status}
        payload = {"queries": json.dumps({"q0": {"query": term, "type": "/aat"}})}
        try:
            if self.client is None:
                with httpx.Client(timeout=12, headers={"User-Agent": "DustAndData/2.0"}) as client:
                    response = client.post(ENDPOINT, data=payload)
            else:
                response = self.client.post(ENDPOINT, data=payload)
            response.raise_for_status()
            matches = response.json().get("q0", {}).get("result", [])
        except (httpx.HTTPError, ValueError, KeyError):
            return {"role": "medium", "label": term, "uri": "", "match_source": "unresolved", "resolution_status": "unresolved"}
        exact = [item for item in matches if item.get("name", "").split(" (")[0].casefold() == key]
        if len(exact) == 1:
            item = exact[0]
            result = {"role": "medium", "label": item["name"], "uri": "http://vocab.getty.edu/" + item["id"], "match_source": "aat_candidate", "resolution_status": "needs_review"}
        elif matches:
            result = {"role": "medium", "label": term, "uri": "", "match_source": "ambiguous", "resolution_status": "ambiguous"}
        else:
            result = {"role": "medium", "label": term, "uri": "", "match_source": "no_match", "resolution_status": "unresolved"}
        self.cache[key] = result
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
