"""Modele danych i parametry wyszukiwania."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

DEFAULT_EXCLUDED = (
    "szkoda całkowita, spalony, anglik, brak prawa rejestracji, "
    "po powodzi, zalany"
)


@dataclass
class SearchParams:
    """Kryteria wyszukiwania (cel: pojazd)."""

    brand: str = ""
    model: str = ""
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    price_from: Optional[int] = None
    price_to: Optional[int] = None
    my_location: str = ""
    max_distance_km: Optional[int] = None
    description_keywords: str = ""   # opcjonalne: min. jedno słowo musi wystąpić
    excluded_phrases: str = ""   # opcjonalne
    use_otomoto: bool = True
    use_olx: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Listing:
    """Pojedyncze ogłoszenie."""

    source: str
    title: str
    url: str
    price: Optional[int] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    location: str = ""
    description: str = ""
    distance_km: Optional[float] = None

    @property
    def uid(self) -> str:
        return self.url.split("?")[0].rstrip("/")
