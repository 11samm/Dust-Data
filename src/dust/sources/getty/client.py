"""Getty discovery, record, vocabulary, and IIIF acquisition."""

from __future__ import annotations

import time

import httpx

from dust.model import parse_artwork_raw
from dust.normalize.medium import normalize_medium
from dust.sources.getty.aat import AATResolver
from dust.sources.getty.adapter import adapt_record

SPARQL_URL = "https://data.getty.edu/museum/collection/sparql"
FEATURED_OBJECT_URI = "https://data.getty.edu/museum/collection/object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb"
QUERY = """SELECT DISTINCT ?object WHERE {
  ?object a <http://www.cidoc-crm.org/cidoc-crm/E22_Human-Made_Object> .
  FILTER(STRSTARTS(STR(?object), "https://data.getty.edu/museum/collection/object/"))
} ORDER BY ?object LIMIT {limit}"""


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

    def __init__(self, client: httpx.Client | None = None, resolver: AATResolver | None = None):
        self.client = client or httpx.Client(timeout=25, headers={"User-Agent": "DustAndData/2.0 (metadata research)"})
        self.resolver = resolver or AATResolver()

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

    def sample_ids(self, size: int) -> list[str]:
        if not 1 <= size <= 100:
            raise ValueError("Getty sample size must be 1–100")
        data = self._get(SPARQL_URL, params={"query": QUERY.replace("{limit}", str(size))}, headers={"Accept": "application/sparql-results+json"})
        discovered = [binding["object"]["value"] for binding in data["results"]["bindings"]]
        return [FEATURED_OBJECT_URI] + [uri for uri in discovered if uri != FEATURED_OBJECT_URI][: size - 1]

    def fetch_record(self, uri: str) -> dict:
        if not uri.startswith("https://data.getty.edu/museum/collection/object/"):
            raise ValueError("unexpected Getty object URI")
        return self._get(uri, headers={"Accept": "application/ld+json"})

    def fetch_cohort(self, *, size: int, mode: str = "stratified", department: str | None = None, type_: str | None = None) -> list[dict]:
        if mode != "stratified" or department or type_:
            raise ValueError("Getty exploratory cohort supports object discovery only")
        records = []
        for uri in self.sample_ids(size):
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
