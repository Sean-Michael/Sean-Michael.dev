"""The fixed set of NOAA CO-OPS stations around Bellingham Bay.

IDs, coordinates, and prediction type come from NOAA's station catalog.
``group`` mirrors the dashboard's region grouping (central / south / islands /
north); ``code`` is the short mono label shown in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Station:
    id: str
    code: str
    name: str
    area: str
    lat: float
    lon: float
    predictions: str  # "Harmonic" | "Subordinate"
    group: str  # "central" | "south" | "islands" | "north"


STATIONS: list[Station] = [
    Station(
        "9449211",
        "BHM·INT",
        "Bellingham",
        "central waterfront",
        48.7450,
        -122.4950,
        "Subordinate",
        "central",
    ),
    Station(
        "9449161",
        "VLG·LMI",
        "Village Point",
        "lummi island",
        48.7167,
        -122.7080,
        "Harmonic",
        "islands",
    ),
    Station(
        "9449292",
        "SDY·LMI",
        "Sandy Point",
        "lummi bay",
        48.7900,
        -122.7080,
        "Subordinate",
        "north",
    ),
    Station(
        "9449771",
        "ROS·ORC",
        "Rosario",
        "east sound, orcas island",
        48.6467,
        -122.8700,
        "Harmonic",
        "islands",
    ),
    Station(
        "9449911",
        "UPR·LOP",
        "Upright Head",
        "lopez island",
        48.5717,
        -122.8850,
        "Harmonic",
        "islands",
    ),
    Station(
        "9449798",
        "ORC·ORC",
        "Orcas",
        "orcas island",
        48.6000,
        -122.9500,
        "Subordinate",
        "islands",
    ),
]

STATIONS_BY_ID: dict[str, Station] = {s.id: s for s in STATIONS}

# Station that powers the homepage widget.
WIDGET_STATION_ID = "9449211"


def get_station(station_id: str) -> Station | None:
    return STATIONS_BY_ID.get(station_id)
