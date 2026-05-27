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


# Keyed by station id (the begin/end window is always ~now±20d, so the last
# successful fetch stays usable). Holds the last-known-good extrema indefinitely
# so we can serve stale data when NOAA is flaky (predictions change very slowly).
_CACHE: dict[str, tuple[float, list[Extremum]]] = {}

_RETRIES = 2  # extra attempts on transient NOAA failures


def _fetch_blocking(station_id: str, begin: str, end: str) -> list[Extremum]:
    last_err: Exception | None = None
    for attempt in range(_RETRIES + 1):
        try:
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
                out.append(
                    Extremum(t=ts.to_pydatetime(), height=float(row["v"]), kind=str(row["type"]))
                )
            return out
        except Exception as err:  # noqa: BLE001 — retry any upstream hiccup
            last_err = err
            if attempt < _RETRIES:
                time.sleep(0.6 * (attempt + 1))
    assert last_err is not None
    raise last_err


async def fetch_extrema(station_id: str, begin: str, end: str) -> list[Extremum]:
    """Return real NOAA hi/lo predictions for ``[begin, end]`` (YYYYMMDD).

    Serves fresh data within the TTL, refetches after, and falls back to the
    last-known-good extrema if NOAA is unavailable (stale-if-error).
    """
    now = time.monotonic()
    cached = _CACHE.get(station_id)
    if cached is not None and now - cached[0] < CACHE_TTL:
        return cached[1]

    try:
        extrema = await asyncio.to_thread(_fetch_blocking, station_id, begin, end)
        _CACHE[station_id] = (now, extrema)
        return extrema
    except Exception:
        if cached is not None:
            return cached[1]  # stale-if-error
        raise


def clear_cache() -> None:
    _CACHE.clear()
