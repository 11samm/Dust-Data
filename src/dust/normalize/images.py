from __future__ import annotations

from dust.model import ArtworkRaw


def normalize_image(raw: ArtworkRaw) -> str:
    web = raw.images.get("web") if isinstance(raw.images.get("web"), dict) else {}
    url = web.get("url") if isinstance(web, dict) else ""
    if isinstance(url, str) and url.strip():
        return "present"

    if raw.source_name == "getty":
        return "unassessed"

    license_status = raw.share_license_status.strip()
    if license_status == "Copyrighted":
        return "withheld_by_license"
    return "absent"
