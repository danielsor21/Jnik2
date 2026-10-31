"""Logika wyszukiwania: pobranie, filtry, odległość, deduplikacja."""
from __future__ import annotations

from typing import Callable, List

import filters
import geo
import scraper
from models import Listing, SearchParams


def run_search(params: SearchParams,
               log: Callable[[str], None] = lambda _m: None) -> List[Listing]:
    origin = None
    if params.my_location.strip():
        origin = geo.geocode(params.my_location)
        if origin is None:
            log(f"Nie znaleziono lokalizacji „{params.my_location}”.")

    raw = scraper.search(params, log)

    # Wstępny filtr (bez odległości), by nie geokodować zbędnych rekordów.
    candidates, seen = [], set()
    for item in raw:
        if item.uid in seen or not filters.matches(item, params):
            continue
        seen.add(item.uid)
        candidates.append(item)

    if origin:
        for item in candidates:
            if item.location:
                item.distance_km = geo.distance_km(origin, item.location)
        candidates = [c for c in candidates if filters.matches(c, params)]
        candidates.sort(key=lambda c: (c.distance_km is None,
                                       c.distance_km or 0, c.price or 0))
    else:
        candidates.sort(key=lambda c: c.price or 0)
    log(f"Pasujących ofert: {len(candidates)}.")
    return candidates
