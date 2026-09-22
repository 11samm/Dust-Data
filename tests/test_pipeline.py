import json
from pathlib import Path

from dust.api.cache import write_cache
from dust.config import CACHE_DIR
from dust.score.run import load_cohort, score_artworks


def test_score_artworks_from_fixture():
    fixture = Path(__file__).parent / "fixtures" / "sample_records.json"
    records = json.loads(fixture.read_text(encoding="utf-8"))
    bundle = score_artworks(records)
    assert len(bundle.frame) == 1
    row = bundle.frame.iloc[0]
    assert row["composite"] < 100
    assert bool(row["has_gap_image"])


def test_load_cohort_from_written_cache(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "sample_records.json"
    records = json.loads(fixture.read_text(encoding="utf-8"))
    cache_file = tmp_path / "cohort-test.json"
    write_cache(
        cache_file,
        {
            "fetched_at": "2026-09-22T10:00:00Z",
            "cohort": {"mode": "stratified", "size": 1},
            "records": records,
        },
    )
    bundle = load_cohort(cache_file)
    assert len(bundle.frame) == 1
    assert "stratified" in bundle.meta.banner
