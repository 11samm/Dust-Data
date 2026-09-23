"""Getty discovery, record, vocabulary, and IIIF acquisition."""

from __future__ import annotations

import random
import time

import httpx

from dust.model import parse_artwork_raw
from dust.normalize.medium import normalize_medium
from dust.sources.getty.aat import AATResolver
from dust.sources.getty.adapter import adapt_record

SPARQL_URL = "https://data.getty.edu/museum/collection/sparql"
OBJECT_PATTERN = """?object a <http://www.cidoc-crm.org/cidoc-crm/E22_Human-Made_Object> .
  FILTER(STRSTARTS(STR(?object), "https://data.getty.edu/museum/collection/object/"))"""
COUNT_QUERY = "SELECT (COUNT(DISTINCT ?object) AS ?total) WHERE { " + OBJECT_PATTERN + " }"
QUERY = "SELECT DISTINCT ?object WHERE { " + OBJECT_PATTERN + " } ORDER BY ?object OFFSET {offset} LIMIT {limit}"
MIN_CANDIDATE_POOL = 250


def reconcile_medium_record(record: dict, resolver: AATResolver) -> None:
    """Getty embedded ID → local vocabulary → AAT cache/remote → unresolved."""
    embedded = [
        ref for ref in record["aat_evidence"]
        if ref.get("role") in {"material", "technique"}
        and ref.get("match_source") == "embedded"
        and str(ref.get("uri") or "").startswith("http://vocab.getty.edu/aat/")
    ]
    if embedded:
        return
    band, canonical, _text, unseen, _warnings = normalize_medium(parse_artwork_raw(record))
    if band != "missing" and not unseen:
        record["aat_evidence"].append({"role": "medium", "label": canonical, "uri": "", "match_source": "local_vocab", "resolution_status": "resolved"})
    elif record["technique"] and unseen:
        record["aat_evidence"].append(resolver.resolve(record["technique"]))
    else:
        record["aat_evidence"].append({"role": "medium", "label": record["technique"], "uri": "", "match_source": "unresolved", "resolution_status": "unresolved"})


class GettySource:
    source_id = "getty"

    def __init__(self, client: httpx.Client | None = None, resolver: AATResolver | None = None, rng: random.Random | None = None):
        self.client = client or httpx.Client(timeout=25, headers={"User-Agent": "DustAndData/2.0 (metadata research)"})
        self.resolver = resolver or AATResolver()
        self.rng = rng or random.SystemRandom()
        self.sample_metadata: dict = {}

    def _get(self, url: str, **kwargs):
        for attempt in range(3):
            try:
                response = self.client.get(url, **kwargs)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError):
                if attempt == 2:
                    raise
                time.sleep(2**attempt)

    def sample_ids(self, size: int, *, exclude_ids: set[str] | None = None) -> list[str]:
        if not 1 <= size <= 100:
            raise ValueError("Getty sample size must be 1–100")
        headers = {"Accept": "application/sparql-results+json"}
        count_data = self._get(SPARQL_URL, params={"query": COUNT_QUERY}, headers=headers)
        total = int(count_data["results"]["bindings"][0]["total"]["value"])
        if total < size:
            raise ValueError(f"Getty has only {total} discoverable objects for a sample of {size}")

        pool_size = min(total, max(MIN_CANDIDATE_POOL, size * 3))
        excluded = exclude_ids or set()
        candidates: list[str] = []
        seen = set(excluded)
        offsets: list[int] = []
        for _ in range(3):
            offset = self.rng.randint(0, total - pool_size)
            offsets.append(offset)
            query = QUERY.replace("{offset}", str(offset)).replace("{limit}", str(pool_size))
            data = self._get(SPARQL_URL, params={"query": query}, headers=headers)
            for binding in data["results"]["bindings"]:
                uri = binding["object"]["value"]
                if uri.startswith("https://data.getty.edu/museum/collection/object/") and uri not in seen:
                    candidates.append(uri)
                    seen.add(uri)
            if len(candidates) >= size:
                break
        if len(candidates) < size:
            raise ValueError(f"Getty returned only {len(candidates)} new object IDs for a sample of {size}")

        self.sample_metadata = {
            "method": "random_ordered_window",
            "total_discoverable_objects": total,
            "candidate_pool_size": pool_size,
            "offsets": offsets,
            "excluded_previous_ids": len(excluded),
        }
        return self.rng.sample(candidates, size)

    def fetch_record(self, uri: str) -> dict:
        if not uri.startswith("https://data.getty.edu/museum/collection/object/"):
            raise ValueError("unexpected Getty object URI")
        return self._get(uri, headers={"Accept": "application/ld+json"})

    def fetch_cohort(self, *, size: int, mode: str = "stratified", department: str | None = None, type_: str | None = None, exclude_ids: set[str] | None = None) -> list[dict]:
        if mode != "stratified" or department or type_:
            raise ValueError("Getty exploratory cohort supports object discovery only")
        records = []
        for uri in self.sample_ids(size, exclude_ids=exclude_ids):
            try:
                record = adapt_record(self.fetch_record(uri))
                reconcile_medium_record(record, self.resolver)
                manifest_uri = record["iiif_manifest"]
                if manifest_uri:
                    try:
                        manifest = self._get(manifest_uri)
                        record["image_rights"] = str(manifest.get("rights") or "")
                    except (httpx.HTTPError, ValueError):
                        record["parse_warnings"].append("Getty IIIF manifest unavailable")
                records.append(record)
            except (httpx.HTTPError, ValueError):
                continue
        return records
