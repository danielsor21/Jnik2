"""Geokodowanie (OpenStreetMap Nominatim) i liczenie odległości."""
from __future__ import annotations

import math
import time
from typing import Dict, Optional, Tuple

import requests

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "RadarOkazji/1.0 (desktop vehicle search)"}

_cache: Dict[str, Optional[Tuple[float, float]]] = {}
_last_call = 0.0


def geocode(place: str) -> Optional[Tuple[float, float]]:
    """Zwraca (lat, lon) dla nazwy miejscowości w Polsce lub None."""
    global _last_call
    key = place.strip().lower()
    if not key:
        return None
    if key in _cache:
        return _cache[key]
    wait = 1.1 - (time.time() - _last_call)  # limit Nominatim: 1 zapytanie/s
    if wait > 0:
        time.sleep(wait)
    result = None
    try:
        resp = requests.get(
            NOMINATIM,
            params={"q": place, "format": "json", "limit": 1,
                    "countrycodes": "pl"},
            headers=HEADERS, timeout=15,
        )
        _last_call = time.time()
        data = resp.json()
        if data:
            result = (float(data[0]["lat"]), float(data[0]["lon"]))
    except (requests.RequestException, ValueError, KeyError):
        result = None
    _cache[key] = result
    return result


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Odległość w linii prostej w km."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def distance_km(origin: Tuple[float, float], place: str) -> Optional[float]:
    """Odległość od punktu origin do miejscowości `place`."""
    # Lokalizacje ogłoszeń bywają w formacie "Katowice, Śląskie".
    target = geocode(place)
    if target is None:
        return None
    return round(haversine_km(origin, target), 0)
