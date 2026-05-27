"""Sun and moon facts for Bellingham, computed with ``astral``.

NOAA's tide feed has no sun/moon data, but the dashboard's overlays and KPI
strip need it. These are real astronomical computations for the bay's location.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from astral import LocationInfo, moon
from astral.sun import sun

_TZ = ZoneInfo("America/Los_Angeles")
_BELLINGHAM = LocationInfo("Bellingham", "USA", "America/Los_Angeles", 48.7519, -122.4787)

_PHASE_NAMES = [
    (1.84, "New Moon", "🌑"),
    (5.53, "Waxing Crescent", "🌒"),
    (9.22, "First Quarter", "🌓"),
    (12.91, "Waxing Gibbous", "🌔"),
    (16.61, "Full Moon", "🌕"),
    (20.30, "Waning Gibbous", "🌖"),
    (23.99, "Last Quarter", "🌗"),
    (27.68, "Waning Crescent", "🌘"),
]


@dataclass(frozen=True)
class SunMoon:
    sunrise: str
    sunset: str
    noon: str
    moon_phase: str
    moon_illum: float
    moon_glyph: str


def _hhmm(dt) -> str:
    return dt.astimezone(_TZ).strftime("%H:%M")


def sun_moon(day: date) -> SunMoon:
    s = sun(_BELLINGHAM.observer, date=day, tzinfo=_TZ)
    phase = moon.phase(day)  # 0..27.99
    name, glyph = next(
        ((n, g) for limit, n, g in _PHASE_NAMES if phase < limit),
        ("New Moon", "🌑"),
    )
    illum = (1 - math.cos(2 * math.pi * phase / 29.53)) / 2
    return SunMoon(
        sunrise=_hhmm(s["sunrise"]),
        sunset=_hhmm(s["sunset"]),
        noon=_hhmm(s["noon"]),
        moon_phase=name,
        moon_illum=round(illum, 2),
        moon_glyph=glyph,
    )
