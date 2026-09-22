import pytest

from dust.api.client import ApiClient


@pytest.mark.live
def test_live_limit_one_contract():
    client = ApiClient()
    data = client.get_artworks(limit=1)
    assert "info" in data
    assert "total" in data["info"]
    assert "data" in data
    assert len(data["data"]) >= 1
    row = data["data"][0]
    assert "id" in row
