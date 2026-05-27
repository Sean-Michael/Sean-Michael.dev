"""Thin async layer over the (synchronous) ``noaa_coops`` package.

``noaa_coops`` does blocking HTTP + pandas work, so every call is dispatched to
a worker thread via :func:`asyncio.to_thread`. Results are memoized in-process
with a TTL so the dashboard's polling doesn't hammer the NOAA API.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime

from noaa_coops import Station as CoopsStation

# Seconds to cache NOAA prediction responses in-memory.
CACHE_TTL = int(os.environ.get("TIDES_CACHE_TTL", "900"))


@dataclass(frozen=True)
class Extremum:
    """A predicted high or low water event (real NOAA hi/lo prediction)."""

    t: datetime  # naive local time (station-local, lst_ldt)
    height: float  # feet above MLLW
    kind: str  # "H" | "L"


_CACHE: dict[tuple[str, str, str], tuple[float, list[Extremum]]] = {}


def _fetch_blocking(station_id: str, begin: str, end: str) -> list[Extremum]:
    station = CoopsStation(id=station_id)
    df = station.get_data(
        begin_date=begin,
        end_date=end,
        product="predictions",
        datum="MLLW",
        units="english",
        time_zone="lst_ldt",
        interval="hilo",
    )
    out: list[Extremum] = []
    for ts, row in df.iterrows():
        out.append(Extremum(t=ts.to_pydatetime(), height=float(row["v"]), kind=str(row["type"])))
    return out


async def fetch_extrema(station_id: str, begin: str, end: str) -> list[Extremum]:
    """Return real NOAA hi/lo predictions for ``[begin, end]`` (YYYYMMDD)."""
    key = (station_id, begin, end)
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached is not None and now - cached[0] < CACHE_TTL:
        return cached[1]

    extrema = await asyncio.to_thread(_fetch_blocking, station_id, begin, end)
    _CACHE[key] = (now, extrema)
    return extrema


def clear_cache() -> None:
    _CACHE.clear()
