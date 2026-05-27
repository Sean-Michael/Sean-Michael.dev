from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.tides import noaa, stations


@pytest.fixture
def fake_noaa(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the NOAA fetch with deterministic extrema (no network)."""

    async def _fake(station_id: str, begin: str, end: str) -> list[noaa.Extremum]:
        base = datetime.now().replace(hour=1, minute=0, second=0, microsecond=0) - timedelta(days=2)
        return [
            noaa.Extremum(
                t=base + timedelta(hours=6 * i),
                height=8.0 if i % 2 == 0 else 2.0,
                kind="H" if i % 2 == 0 else "L",
            )
            for i in range(40)
        ]

    monkeypatch.setattr(noaa, "fetch_extrema", _fake)


def test_tides_page_renders(client: TestClient) -> None:
    res = client.get("/tides")
    assert res.status_code == 200
    assert 'id="tides-root"' in res.text


def test_js_bundles_revalidate(client: TestClient) -> None:
    # Unhashed bundles must carry no-cache so deploys aren't masked by caching.
    res = client.get("/js/tides.js")
    assert res.headers.get("cache-control") == "no-cache"


def test_widget_payload(client: TestClient, fake_noaa: None) -> None:
    res = client.get("/api/tides/widget")
    assert res.status_code == 200
    body = res.json()
    assert body["station"] == "Bellingham"
    assert body["trend"] in {"rising", "falling", "slack"}
    assert isinstance(body["height"], (int, float))
    assert len(body["samples"]) == 49
    assert {"t", "v"} <= body["samples"][0].keys()


def test_fetch_extrema_serves_stale_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from app.tides import noaa as noaa_mod

    noaa_mod.clear_cache()
    calls = {"n": 0}
    good = [noaa.Extremum(t=datetime(2026, 5, 27, 1, 0), height=8.0, kind="H")]

    def fake_blocking(station_id: str, begin: str, end: str) -> list[noaa.Extremum]:
        calls["n"] += 1
        if calls["n"] == 1:
            return good
        raise RuntimeError("NOAA down")

    monkeypatch.setattr(noaa_mod, "_fetch_blocking", fake_blocking)
    monkeypatch.setattr(noaa_mod, "CACHE_TTL", 0)  # force a refetch on the 2nd call

    async def run() -> tuple[list[noaa.Extremum], list[noaa.Extremum]]:
        first = await noaa_mod.fetch_extrema("9449211", "20260501", "20260601")
        second = await noaa_mod.fetch_extrema("9449211", "20260501", "20260601")
        return first, second

    first, second = asyncio.run(run())
    assert first == good
    assert second == good  # stale-if-error: returns last-known-good despite failure


def test_bootstrap_shape(client: TestClient, fake_noaa: None) -> None:
    res = client.get("/api/tides/bootstrap")
    assert res.status_code == 200
    body = res.json()
    assert body["datum"] == "MLLW"
    assert len(body["stations"]) == len(stations.STATIONS) == 6
    assert "moon_glyph" in body["sun_moon"]
    stn = body["stations"][0]
    assert {"id", "code", "name", "extrema"} <= stn.keys()
    assert stn["extrema"]
    assert isinstance(stn["extrema"][0]["t"], int)
