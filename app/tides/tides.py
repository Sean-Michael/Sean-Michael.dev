"""Tide curve math built on real NOAA hi/lo predictions.

NOAA gives us discrete high/low events. Between two consecutive extrema the
water follows very nearly a half-cosine (the standard smooth tidal curve). We
interpolate that curve to get height and rate at any instant, then derive the
per-station snapshot the dashboard shows.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime

from app.tides.noaa import Extremum


@dataclass(frozen=True)
class Sample:
    t: datetime
    v: float


@dataclass(frozen=True)
class Snapshot:
    height: float
    rate: float  # ft/hr, signed
    trend: str  # "rising" | "falling" | "slack"
    day_min: float
    day_max: float
    next_high: Extremum | None
    next_low: Extremum | None


def _ts(dt: datetime) -> float:
    return dt.timestamp()


def height_at(extrema: list[Extremum], when: datetime) -> float:
    """Half-cosine interpolation of height (ft) at ``when``."""
    if not extrema:
        return math.nan
    times = [_ts(e.t) for e in extrema]
    x = _ts(when)
    i = bisect_right(times, x)
    if i == 0:
        return extrema[0].height
    if i >= len(extrema):
        return extrema[-1].height
    a, b = extrema[i - 1], extrema[i]
    ta, tb = times[i - 1], times[i]
    frac = (x - ta) / (tb - ta) if tb != ta else 0.0
    return (a.height + b.height) / 2 + (a.height - b.height) / 2 * math.cos(math.pi * frac)


def rate_at(extrema: list[Extremum], when: datetime) -> float:
    """Signed rate of change in ft/hr via centered finite difference."""
    dt = 300.0  # 5 minutes, in seconds
    before = height_at(extrema, datetime.fromtimestamp(_ts(when) - dt))
    after = height_at(extrema, datetime.fromtimestamp(_ts(when) + dt))
    return (after - before) / (2 * dt) * 3600.0


def sample(extrema: list[Extremum], start: datetime, end: datetime, n: int = 120) -> list[Sample]:
    if n < 1 or not extrema:
        return []
    s, e = _ts(start), _ts(end)
    out: list[Sample] = []
    for i in range(n + 1):
        x = s + (e - s) * (i / n)
        dt = datetime.fromtimestamp(x)
        out.append(Sample(t=dt, v=height_at(extrema, dt)))
    return out


def snapshot(extrema: list[Extremum], now: datetime) -> Snapshot:
    h = height_at(extrema, now)
    r = rate_at(extrema, now)
    trend = "slack" if abs(r) < 0.15 else "rising" if r > 0 else "falling"

    # Day range: min/max over the calendar day containing ``now``.
    day = now.date()
    day_pts = [e.height for e in extrema if e.t.date() == day]
    day_min = min(day_pts) if day_pts else h
    day_max = max(day_pts) if day_pts else h

    upcoming = [e for e in extrema if e.t >= now]
    next_high = next((e for e in upcoming if e.kind == "H"), None)
    next_low = next((e for e in upcoming if e.kind == "L"), None)

    return Snapshot(
        height=h,
        rate=r,
        trend=trend,
        day_min=day_min,
        day_max=day_max,
        next_high=next_high,
        next_low=next_low,
    )
