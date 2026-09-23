"""Pure mapping from a Getty Linked.Art object to common score inputs."""

from __future__ import annotations

import re
from typing import Any


def _items(value: Any) -> list[dict]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _content(items: Any, label: str) -> str:
    for item in _items(items):
        if item.get("_label") == label and isinstance(item.get("content"), str):
            return item["content"].strip()
    return ""


def _year(value: Any) -> int | None:
    match = re.match(r"^(-?\d{1,6})", str(value or ""))
    return int(match.group(1)) if match else None


def _aat(items: Any, role: str) -> list[dict[str, str]]:
    return [
        {"role": role, "uri": str(item["id"]), "label": str(item.get("_label") or ""), "match_source": "embedded"}
        for item in _items(items)
        if str(item.get("id") or "").startswith("http://vocab.getty.edu/aat/")
    ]


def adapt_record(data: dict[str, Any]) -> dict[str, Any]:
    uri = str(data.get("id") or "")
    if data.get("type") != "HumanMadeObject" or not uri.startswith("https://data.getty.edu/museum/collection/object/"):
        raise ValueError("not a Getty Museum Collection object")

    identifiers = data.get("identified_by")
    title = _content(identifiers, "Preferred Title") or _content(identifiers, "Title")
    accession = _content(identifiers, "Accession Number")
    production = data.get("produced_by") if isinstance(data.get("produced_by"), dict) else {}
    timespan = production.get("timespan") if isinstance(production.get("timespan"), dict) else {}
    date_text = _content(timespan.get("identified_by"), "Dates") or _content(timespan.get("identified_by"), "Date")
    earliest = _year(timespan.get("begin_of_the_begin"))
    latest = _year(timespan.get("end_of_the_end"))
    creators = []
    for actor in _items(production.get("carried_out_by")):
        creators.append({"description": actor.get("_label") or "", "role": "maker"})
    if not creators:
        maker_name = _content(production.get("referred_to_by"), "Artist/Maker (Producer) Name")
        if maker_name:
            creators.append({"description": maker_name, "role": "maker"})

    notes = data.get("referred_to_by")
    medium = _content(notes, "Materials Description")
    object_type = _content(notes, "Object Type")
    description = next((x.get("content", "").strip() for x in _items(notes) if x.get("_label") == "Object Description" and x.get("format") == "text/markdown" and not x.get("content", "").startswith("[description text omitted")), "")
    department = next((x.get("_label") or "" for x in _items(data.get("current_keeper"))), "")
    subject_of = _items(data.get("subject_of"))
    public_url = next((x.get("id") or "" for x in subject_of if x.get("format") == "text/html"), "")
    manifest = next((x.get("id") or "" for x in subject_of if "/iiif/manifest/3/" in str(x.get("id") or "")), "")
    if not manifest:
        manifest = next((x.get("id") or "" for x in subject_of if "/iiif/manifest/" in str(x.get("id") or "")), "")
    representation = _items(data.get("representation"))
    image_url = next((x.get("id") or "" for x in representation if "/iiif/image/" in str(x.get("id") or "")), "")
    if image_url:
        image_url = image_url.replace("/full/full/", "/full/!400,400/")

    evidence = _aat(data.get("classified_as"), "object_type")
    evidence += _aat(data.get("made_of"), "material")
    for item in _items(production.get("technique")):
        evidence += _aat([item], "technique")

    warnings = []
    if not accession:
        warnings.append("Getty object has no accession identifier")
    if not title:
        warnings.append("Getty object has no preferred title")
    if not date_text and earliest is None:
        warnings.append("Getty production date unavailable")
    if not medium:
        warnings.append("Getty materials description unavailable")

    metadata_rights = next(
        (concept.get("id") or "" for right in _items(data.get("subject_to")) for concept in _items(right.get("classified_as")) if "creativecommons.org/" in str(concept.get("id") or "")),
        "",
    )

    return {
        "id": uri.rsplit("/", 1)[-1],
        "source_name": "getty",
        "source_uri": uri,
        "accession_number": accession or uri.rsplit("/", 1)[-1],
        "title": title or str(data.get("_label") or ""),
        "url": public_url or uri,
        "department": department,
        "type": object_type,
        "record_type": "object",
        "creation_date": date_text,
        "date_text": date_text,
        "creation_date_earliest": earliest,
        "creation_date_latest": latest,
        "creators": creators,
        "technique": medium,
        "description": description,
        "images": {"web": {"url": image_url}} if image_url else {},
        "iiif_manifest": manifest,
        "metadata_rights": metadata_rights,
        "aat_evidence": evidence,
        "parse_warnings": warnings,
        "source_record": data,
    }
