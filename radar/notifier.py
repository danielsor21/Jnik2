"""Powiadomienia Discord przez webhook."""
from __future__ import annotations

from typing import Optional

import requests

from models import Listing, SearchParams


def _range(a, b, unit: str = "") -> str:
    if a is None and b is None:
        return "dowolny"
    return f"{a if a is not None else '…'} – {b if b is not None else '…'}{unit}"


def format_message(params: SearchParams, listing: Optional[Listing]) -> str:
    """Wzór wiadomości: te same pola co w formularzu + ogłoszenie."""
    lines = [
        "@everyone 🚗 **Nowa oferta**",
        "**Cel wyszukiwania:** pojazd",
        f"**Marka:** {params.brand or 'dowolna'}",
        f"**Model:** {params.model or 'dowolny'}",
        f"**Rok:** {_range(params.year_from, params.year_to)}",
        f"**Cena:** {_range(params.price_from, params.price_to, ' zł')}",
        f"**Lokalizacja:** {params.my_location or 'nie ustawiono'}",
    ]
    if params.description_keywords.strip():
        lines.append(f"**Opis ogłoszenia:** {params.description_keywords}")
    if listing:
        dist = (f" (~{listing.distance_km:.0f} km od Ciebie)"
                if listing.distance_km is not None else "")
        price = f"{listing.price:,} zł".replace(",", " ") if listing.price else "brak"
        lines += [
            "",
            f"**{listing.title}** [{listing.source}]",
            f"Cena: {price} | Rok: {listing.year or '—'} | "
            f"Przebieg: {listing.mileage or '—'} km",
            f"Lokalizacja: {listing.location or '—'}{dist}",
            listing.url,
        ]
    return "\n".join(lines)[:1990]


def send_discord(webhook_url: str, content: str) -> None:
    """Wysyła wiadomość z pingiem @everyone. Rzuca wyjątek przy błędzie."""
    resp = requests.post(
        webhook_url.strip(),
        json={"content": content,
              "allowed_mentions": {"parse": ["everyone"]}},
        timeout=15,
    )
    resp.raise_for_status()
