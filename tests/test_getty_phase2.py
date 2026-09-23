import json
import random
from pathlib import Path

import httpx

from dust.api.cache import read_cache, write_cache
from dust.model import parse_artwork_raw
from dust.normalize.medium import normalize_medium
from dust.score.run import load_cohort, score_artworks
from dust.sources.getty.aat import AATResolver
from dust.sources.getty.adapter import adapt_record
from dust.sources.getty.client import GettySource, reconcile_medium_record

FIXTURES = Path(__file__).parent / "fixtures" / "getty"


def _records():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    return [json.loads((FIXTURES / item["fixture"]).read_text(encoding="utf-8")) for item in manifest["records"]]


def test_real_getty_fixture_cohort_maps_and_scores_with_expected_bands():
    adapted = [adapt_record(item) for item in _records()]
    assert 20 <= len(adapted) <= 30
    assert all(item["source_name"] == "getty" for item in adapted)
    by_accession = {item["accession_number"]: item for item in adapted}
    photograph = by_accession["84.XT.1571.38"]
    assert photograph["technique"] == "Daguerreotype"
    assert photograph["iiif_manifest"].startswith("https://media.getty.edu/iiif/manifest/3/")
    assert photograph["images"]["web"]["url"].startswith("https://media.getty.edu/iiif/image/")
    assert photograph["metadata_rights"].endswith("/zero/1.0/")
    assert any(e["role"] == "object_type" for e in photograph["aat_evidence"])
    assert by_accession["83.AE.436.6526"]["images"] == {}

    bundle = score_artworks(adapted)
    assert len(bundle.frame) == len(bundle.records) == len(adapted)
    missing_image = bundle.frame[bundle.frame["accession_number"] == "83.AE.436.6526"].iloc[0]
    assert missing_image["image_state"] == "unassessed"
    assert bundle.records[f"getty:{by_accession['83.AE.436.6526']['id']}"].composite_denominator == 85
    expected = {
        "83.AE.436.6526": ("unassessed", "multi_century", "generic", "unknown", "missing"),
        "76.AD.11.6.172": ("unassessed", "century", "generic", "unknown", "missing"),
        "83.AE.435.1008": ("unassessed", "century", "generic", "unknown", "missing"),
        "75.NH.109.4248": ("unassessed", "generation", "material_only", "unknown", "missing"),
        "75.NH.109.4300": ("unassessed", "generation", "material_only", "unknown", "missing"),
        "75.NH.109.5135": ("unassessed", "generation", "material_only", "unknown", "missing"),
        "84.XT.1571.38": ("present", "circa", "generic", "unknown", "missing"),
        "81.AE.206.D.2065": ("unassessed", "century", "generic", "unknown", "present"),
        "84.XC.873.6123": ("present", "exact", "generic", "unknown", "missing"),
        "2003.214.9": ("present", "century", "material_only", "unknown", "present"),
        "81.AE.199.22": ("present", "generation", "generic", "unknown", "present"),
        "83.MG.82": ("present", "exact", "generic", "missing", "present"),
        "84.XC.873.6610": ("present", "circa", "generic", "named", "missing"),
        "84.XC.979.2712": ("present", "circa", "generic", "named", "missing"),
        "84.XO.734.4.3.24": ("present", "narrow_range", "generic", "named", "stub"),
        "81.AE.203.6.11": ("present", "generation", "generic", "named", "present"),
        "90.XM.64.75": ("present", "exact", "generic", "named", "stub"),
        "86.XA.750.5": ("present", "decade", "generic", "named", "present"),
        "84.XM.436.59": ("present", "narrow_range", "specific", "named", "missing"),
        "84.XB.1206.21": ("present", "exact", "generic", "named", "present"),
        "2004.54.3": ("present", "circa", "specific", "named", "present"),
        "2010.80.2": ("present", "circa", "specific", "named", "present"),
        "2021.28.453": ("present", "exact", "specific", "named", "present"),
        "90.PA.20": ("present", "exact", "specific", "named", "present"),
        "92.XM.23.34": ("present", "exact", "specific", "named", "present"),
        "99.XM.42.4": ("present", "exact", "specific", "named", "present"),
    }
    assert set(expected) == set(by_accession)
    for row in bundle.frame.itertuples():
        assert (row.image_state, row.date_band, row.medium_band, row.attribution_band, row.description_band) == expected[row.accession_number]
    assert bundle.frame.loc[bundle.frame["accession_number"] == "81.AE.206.D.2065", "date_display"].iloc[0] == "6th century B.C."
    irises = by_accession["90.PA.20"]
    assert any(e["role"] == "material" and e["match_source"] == "embedded" for e in irises["aat_evidence"])
    assert normalize_medium(parse_artwork_raw(irises))[0] == "specific"


def test_getty_cache_reloads_offline_and_accession_is_not_identity(tmp_path):
    adapted = [adapt_record(item) for item in _records()[:2]]
    adapted[1]["accession_number"] = adapted[0]["accession_number"]
    path = tmp_path / "getty.json"
    write_cache(path, {"source": "getty", "schema_version": 2, "fetched_at": "2026-09-23T00:00:00Z", "cohort": {"mode": "stratified", "size": 2}, "records": adapted})
    bundle = load_cohort(path)
    assert len(bundle.frame) == len(bundle.records) == 2
    assert all(key.startswith("getty:") for key in bundle.records)
    assert "exploratory" in bundle.meta.banner


def test_aat_remote_candidate_is_cached_without_second_request(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"q0": {"result": [{"id": "aat/300123456", "name": "terracotta (clay material)", "match": False}]}})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    resolver = AATResolver(tmp_path / "aat.json", client=client)
    first = resolver.resolve("Terracotta")
    second = AATResolver(tmp_path / "aat.json", client=client).resolve("Terracotta")
    assert first["match_source"] == "aat_candidate"
    assert first["resolution_status"] == "needs_review"
    assert second["match_source"] == "aat_cache"
    assert second["resolution_status"] == "needs_review"
    assert len(calls) == 1


def test_aat_service_failure_does_not_create_a_false_match(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(503)))
    resolver = AATResolver(tmp_path / "aat.json", client=client)
    result = resolver.resolve("unknown medium")
    assert result["match_source"] == "unresolved"
    assert result["uri"] == ""
    assert not (tmp_path / "aat.json").exists()


def test_invalid_getty_record_rejected():
    try:
        adapt_record({"id": "https://example.org/object/1", "type": "HumanMadeObject"})
    except ValueError:
        pass
    else:
        raise AssertionError("non-Getty URI accepted")


def test_getty_image_state_does_not_infer_absence_from_missing_manifest():
    item = adapt_record(_records()[2])
    raw = parse_artwork_raw(item)
    assert raw.source_name == "getty"
    assert raw.images == {}


def test_getty_medium_resolution_order():
    class Resolver:
        def __init__(self):
            self.calls = []

        def resolve(self, term):
            self.calls.append(term)
            return {"role": "medium", "label": term, "uri": "", "match_source": "unresolved"}

    resolver = Resolver()
    embedded = adapt_record(_records()[0])
    embedded["technique"] = "unlisted material"
    embedded["aat_evidence"].append({"role": "material", "label": "Oil Paint", "uri": "http://vocab.getty.edu/aat/300015050", "match_source": "embedded"})
    reconcile_medium_record(embedded, resolver)
    band, canonical, *_ = normalize_medium(parse_artwork_raw(embedded))
    assert (band, canonical) == ("material_only", "oil paint")
    assert resolver.calls == []

    local = adapt_record(_records()[1])
    reconcile_medium_record(local, resolver)
    assert local["aat_evidence"][-1]["match_source"] == "local_vocab"
    assert resolver.calls == []

    unresolved = adapt_record(_records()[2])
    reconcile_medium_record(unresolved, resolver)
    assert resolver.calls == ["Terracotta"]
    assert unresolved["aat_evidence"][-1]["match_source"] == "unresolved"


def test_getty_discovery_randomizes_and_excludes_previous_cohort():
    queries = []

    def respond(request):
        query = request.url.params["query"]
        queries.append(query)
        if "COUNT(DISTINCT" in query:
            return httpx.Response(200, json={"results": {"bindings": [{"total": {"value": "1000"}}]}})
        bindings = [
            {"object": {"value": f"https://data.getty.edu/museum/collection/object/{index:04d}"}}
            for index in range(300)
        ]
        return httpx.Response(200, json={"results": {"bindings": bindings}})

    client = httpx.Client(transport=httpx.MockTransport(respond))
    source = GettySource(client=client, rng=random.Random(7))
    first = source.sample_ids(100)
    second = source.sample_ids(100, exclude_ids=set(first))
    assert len(first) == len(second) == 100
    assert set(first).isdisjoint(second)
    assert source.sample_metadata["excluded_previous_ids"] == 100
    assert len([query for query in queries if "OFFSET" in query]) == 2
    assert all("LIMIT 300" in query for query in queries if "OFFSET" in query)


def test_getty_force_refresh_replaces_cohort_with_new_ids(tmp_path, monkeypatch):
    import dust.api.load as loading

    candidates = [adapt_record(item) for item in _records()[:10]]
    exclusions = []

    class FakeGettySource:
        def __init__(self):
            self.sample_metadata = {"method": "random_ordered_window"}

        def fetch_cohort(self, *, size, mode, department, type_, exclude_ids):
            exclusions.append(set(exclude_ids))
            return [item for item in candidates if item["source_uri"] not in exclude_ids][:size]

    monkeypatch.setattr(loading, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(loading, "GettySource", FakeGettySource)
    path = loading.ensure_cohort(source="getty", size=5, force_refresh=True)
    first = {item["source_uri"] for item in read_cache(path)["records"]}
    loading.ensure_cohort(source="getty", size=5, force_refresh=True)
    second_payload = read_cache(path)
    second = {item["source_uri"] for item in second_payload["records"]}
    assert len(first) == len(second) == 5
    assert first.isdisjoint(second)
    assert exclusions == [set(), first]
    assert second_payload["sampling"]["method"] == "random_ordered_window"


def test_getty_evidence_renders_compact_image():
    from streamlit.testing.v1 import AppTest
    fixture = FIXTURES / "c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb.json"
    src = Path(__file__).parents[1] / "src"
    script = f"""
import json
import sys
from pathlib import Path
sys.path.insert(0, {str(src)!r})
from dust.sources.getty.adapter import adapt_record
from dust.score.run import score_artworks
from dust.ui.queue import render_evidence
data = json.loads(Path({str(fixture)!r}).read_text(encoding="utf-8"))
record = next(iter(score_artworks([adapt_record(data)]).records.values()))
render_evidence(record)
"""
    at = AppTest.from_string(script).run(timeout=20)
    assert not at.exception
