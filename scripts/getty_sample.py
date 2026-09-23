"""Capture a small, reproducible Getty Museum Collection sample for adapter tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

SPARQL_URL = "https://data.getty.edu/museum/collection/sparql"
SAMPLE_LIMIT = 25
QUERY = f"""SELECT DISTINCT ?object WHERE {{
  ?object a <http://www.cidoc-crm.org/cidoc-crm/E22_Human-Made_Object> .
  FILTER(STRSTARTS(STR(?object), "https://data.getty.edu/museum/collection/object/"))
}} ORDER BY ?object LIMIT {SAMPLE_LIMIT}"""
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "getty"
FEATURED_OBJECT_URI = "https://data.getty.edu/museum/collection/object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=45, headers={"User-Agent": "DustAndData/2.0 (research fixture capture)"}) as client:
        response = client.get(SPARQL_URL, params={"query": QUERY}, headers={"Accept": "application/sparql-results+json"})
        response.raise_for_status()
        uris = list(dict.fromkeys(
            [item["object"]["value"] for item in response.json()["results"]["bindings"]]
            + [FEATURED_OBJECT_URI]
        ))
        manifest = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "query": QUERY, "records": []}
        for uri in uris:
            record_response = client.get(uri, headers={"Accept": "application/ld+json"})
            record_response.raise_for_status()
            data = record_response.json()
            # Fixture projection preserves the Linked.Art paths used by the adapter.
            # Some long narrative text carries separate rights; retain only a short
            # placeholder so the repo does not republish it.
            for note in data.get("referred_to_by", []):
                if isinstance(note, dict) and isinstance(note.get("content"), str):
                    rights = [
                        concept.get("id", "")
                        for item in note.get("subject_to", [])
                        for concept in item.get("classified_as", [])
                    ]
                    licensed_description = note.get("_label") == "Object Description" and note.get("format") == "text/markdown" and any("creativecommons.org/licenses/by/4.0/" in uri or "creativecommons.org/publicdomain/zero/1.0/" in uri for uri in rights)
                    if note.get("_label") not in {"Materials Description", "Object Type"} and not licensed_description:
                        note["content"] = "[description text omitted from fixture]"
            for key in list(data):
                if key not in {
                    "id", "type", "_label", "classified_as", "identified_by",
                    "referred_to_by", "made_of", "produced_by", "current_keeper",
                    "subject_of", "representation", "subject_to", "shows",
                }:
                    del data[key]
            path = OUT / f"{uri.rsplit('/', 1)[-1]}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest["records"].append({"url": uri, "fixture": path.name, "status": record_response.status_code})
            print(uri, list(data), path.stat().st_size)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
