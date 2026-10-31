"""Filtrowanie ogłoszeń po stronie klienta."""
from __future__ import annotations

from typing import List

from models import Listing, SearchParams


def split_terms(text: str) -> List[str]:
    """Rozdziela listę fraz po przecinku / średniku / nowej linii."""
    raw = text.replace(";", ",").replace("\n", ",").split(",")
    return [t.strip().lower() for t in raw if t.strip()]


def matches(listing: Listing, params: SearchParams) -> bool:
    """Zwraca True, jeśli ogłoszenie spełnia wszystkie kryteria."""
    text = f"{listing.title} {listing.description}".lower()

    for phrase in split_terms(params.excluded_phrases):
        if phrase in text:
            return False

    title = listing.title.lower()
    for word in (params.brand, params.model):
        # Marka/model musi występować w tytule (pomijamy myślniki/spacje).
        w = word.strip().lower()
        if w and w.replace("-", " ") not in title.replace("-", " "):
            return False

    keywords = split_terms(params.description_keywords)
    if keywords and not any(k in text for k in keywords):
        return False

    if listing.year is not None:
        if params.year_from and listing.year < params.year_from:
            return False
        if params.year_to and listing.year > params.year_to:
            return False
    if listing.price is not None:
        if params.price_from and listing.price < params.price_from:
            return False
        if params.price_to and listing.price > params.price_to:
            return False

    if params.max_distance_km and listing.distance_km is not None:
        if listing.distance_km > params.max_distance_km:
            return False
    return True
