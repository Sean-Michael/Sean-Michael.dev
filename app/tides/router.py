"""Bellingham Tidal Observatory API, mounted under /api/tides.

``/bootstrap`` returns station metadata plus real NOAA hi/lo predictions
(extrema) spanning a wide window, plus sun/moon facts — the full-dashboard
payload. ``/widget`` returns a compact snapshot for the homepage carousel
widget. The frontend interpolates the smooth tide curve from the extrema.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from app.tides import astro, noaa, stations, tides

router = APIRouter(prefix="/api/tides", tags=["tides"])

_TZ = ZoneInfo("America/Los_Angeles")

# How far around "now" to fetch hi/lo predictions — wide enough to cover the
# dashboard's longest range (30D) panned either direction.
_PAST_DAYS = 20
_FUTURE_DAYS = 20


def _epoch_ms(dt: datetime) -> int:
    # NOAA lst_ldt times are Pacific wall-clock but tz-naive; localize them.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ)
    return int(dt.timestamp() * 1000)


def _serialize_extrema(extrema: list[noaa.Extremum]) -> list[dict[str, Any]]:
    return [{"t": _epoch_ms(e.t), "height": round(e.height, 3), "kind": e.kind} for e in extrema]


def _date_range(now: datetime) -> tuple[str, str]:
    begin = (now - timedelta(days=_PAST_DAYS)).strftime("%Y%m%d")
    end = (now + timedelta(days=_FUTURE_DAYS)).strftime("%Y%m%d")
    return begin, end


async def _station_payload(s: stations.Station, begin: str, end: str) -> dict[str, Any]:
    extrema = await noaa.fetch_extrema(s.id, begin, end)
    return {
        "id": s.id,
        "code": s.code,
        "name": s.name,
        "area": s.area,
        "lat": s.lat,
        "lon": s.lon,
        "predictions": s.predictions,
        "group": s.group,
        "extrema": _serialize_extrema(extrema),
    }


@router.get("/bootstrap")
async def bootstrap() -> dict[str, Any]:
    """Everything the dashboard loads on startup, in one round trip."""
    now = datetime.now(_TZ)
    begin, end = _date_range(now)
    # Don't let one flaky station sink the whole dashboard — gather, then drop
    # any that failed (each station already falls back to last-known-good data).
    results = await asyncio.gather(
        *(_station_payload(s, begin, end) for s in stations.STATIONS),
        return_exceptions=True,
    )
    good = [r for r in results if not isinstance(r, BaseException)]
    if not good:
        first = next((r for r in results if isinstance(r, BaseException)), None)
        raise HTTPException(status_code=502, detail=f"NOAA upstream error: {first}")

    sm = astro.sun_moon(now.date())
    return {
        "now": _epoch_ms(now),
        "tz": "America/Los_Angeles",
        "datum": "MLLW",
        "units": "english",
        "date": {
            "iso": now.strftime("%Y-%m-%d"),
            "pretty": now.strftime("%a · %b %-d, %Y"),
        },
        "sun_moon": {
            "sunrise": sm.sunrise,
            "sunset": sm.sunset,
            "noon": sm.noon,
            "moon_phase": sm.moon_phase,
            "moon_illum": sm.moon_illum,
            "moon_glyph": sm.moon_glyph,
        },
        "stations": good,
    }


@router.get("/widget")
async def widget() -> dict[str, Any]:
    """Compact Bellingham snapshot for the homepage carousel widget."""
    try:
        now = datetime.now(_TZ)
        begin, end = _date_range(now)
        s = stations.get_station(stations.WIDGET_STATION_ID)
        assert s is not None
        extrema = await noaa.fetch_extrema(s.id, begin, end)
        now_naive = now.replace(tzinfo=None)
        snap = tides.snapshot(extrema, now_naive)

        # Sparkline samples across the calendar day containing "now".
        day_start = now_naive.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        pts = tides.sample(extrema, day_start, day_end, 48)

        return {
            "station": s.name,
            "code": s.code,
            "now": _epoch_ms(now),
            "time_label": now.strftime("%H:%M"),
            "height": round(snap.height, 1),
            "rate": round(snap.rate, 2),
            "trend": snap.trend,
            "next_high": (
                {"height": round(snap.next_high.height, 1), "t": _epoch_ms(snap.next_high.t)}
                if snap.next_high
                else None
            ),
            "next_low": (
                {"height": round(snap.next_low.height, 1), "t": _epoch_ms(snap.next_low.t)}
                if snap.next_low
                else None
            ),
            "day_start": _epoch_ms(day_start),
            "day_end": _epoch_ms(day_end),
            "samples": [{"t": _epoch_ms(p.t), "v": round(p.v, 3)} for p in pts],
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"NOAA upstream error: {exc}") from exc
