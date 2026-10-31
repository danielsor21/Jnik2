"""Pobieranie ogłoszeń z Otomoto i OLX (requests + BeautifulSoup)."""
from __future__ import annotations

import json
import random
import re
import time
from typing import Callable, Iterable, List, Optional
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from models import Listing, SearchParams

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]
Log = Callable[[str], None]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def _to_int(value) -> Optional[int]:
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value).split(",")[0])
    return int(digits) if digits else None


def _fetch(url: str, log: Log) -> Optional[str]:
    time.sleep(random.uniform(1.0, 2.5))  # dynamiczne opóźnienie
    headers = {"User-Agent": random.choice(USER_AGENTS),
               "Accept-Language": "pl-PL,pl;q=0.9"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            log(f"  HTTP {resp.status_code} dla {url}")
            return None
        return resp.text
    except requests.RequestException as exc:
        log(f"  Błąd sieci: {exc}")
        return None


# ----------------------------------------------------------------- Otomoto
def otomoto_url(p: SearchParams) -> str:
    path = "https://www.otomoto.pl/osobowe"
    if p.brand:
        path += "/" + _slug(p.brand)
        if p.model:
            path += "/" + _slug(p.model)
    if p.year_from:
        path += f"/od-{p.year_from}"
    q = ["search[order]=created_at_first:desc"]
    if p.price_from:
        q.append(f"search[filter_float_price:from]={p.price_from}")
    if p.price_to:
        q.append(f"search[filter_float_price:to]={p.price_to}")
    if p.year_to:
        q.append(f"search[filter_float_year:to]={p.year_to}")
    return path + "?" + "&".join(q)


def _walk(node) -> Iterable[dict]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _param(item: dict, key: str):
    for prm in item.get("parameters") or []:
        if isinstance(prm, dict) and prm.get("key") == key:
            return prm.get("value") or prm.get("displayValue")
    return None


def _otomoto_from_json(item: dict) -> Optional[Listing]:
    url, title = item.get("url"), item.get("title")
    if not (isinstance(url, str) and isinstance(title, str)
            and "otomoto.pl" in url and "price" in item):
        return None
    price = item["price"]
    if isinstance(price, dict):
        amount = price.get("amount")
        price = amount.get("units") if isinstance(amount, dict) else amount
    loc = item.get("location") or {}
    city = (loc.get("city") or {}).get("name", "") if isinstance(loc, dict) else ""
    region = (loc.get("region") or {}).get("name", "") if isinstance(loc, dict) else ""
    return Listing(
        source="Otomoto", title=title, url=url, price=_to_int(price),
        year=_to_int(_param(item, "year")),
        mileage=_to_int(_param(item, "mileage")),
        location=", ".join(x for x in (city, region) if x),
        description=str(item.get("shortDescription") or ""),
    )


def parse_otomoto(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "lxml")
    found, seen = [], set()
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        try:
            for item in _walk(json.loads(script.string)):
                lst = _otomoto_from_json(item)
                if lst and lst.url not in seen:
                    seen.add(lst.url)
                    found.append(lst)
        except ValueError:
            pass
    if found:
        return found
    # Plan B: znaczniki HTML
    for art in soup.select("article[data-id]"):
        a = art.select_one("h2 a, h1 a, a[href*='/oferta/']")
        if not a or not a.get("href"):
            continue
        text = art.get_text(" ", strip=True)
        price_el = art.select_one("[data-testid='ad-price'], h3")
        year = re.search(r"\b(19[89]\d|20[0-4]\d)\b", text)
        km = re.search(r"([\d\s]{3,})\s*km\b", text)
        found.append(Listing(
            source="Otomoto", title=a.get_text(strip=True), url=a["href"],
            price=_to_int(price_el.get_text()) if price_el else None,
            year=int(year.group(1)) if year else None,
            mileage=_to_int(km.group(1)) if km else None,
            description=text,
        ))
    return found


# --------------------------------------------------------------------- OLX
def olx_url(p: SearchParams) -> str:
    query = " ".join(x for x in (p.brand, p.model) if x)
    base = "https://www.olx.pl/motoryzacja/samochody/"
    if query:
        base += f"q-{quote(query.replace(' ', '-'))}/"
    q = ["search[order]=created_at:desc"]
    if p.price_from:
        q.append(f"search[filter_float_price:from]={p.price_from}")
    if p.price_to:
        q.append(f"search[filter_float_price:to]={p.price_to}")
    if p.year_from:
        q.append(f"search[filter_float_year:from]={p.year_from}")
    if p.year_to:
        q.append(f"search[filter_float_year:to]={p.year_to}")
    return base + "?" + "&".join(q)


def parse_olx(html: str) -> List[Listing]:
    soup = BeautifulSoup(html, "lxml")
    found = []
    for card in soup.select("[data-cy='l-card']"):
        a = card.find("a", href=True)
        title_el = card.find(["h4", "h6", "h3"])
        if not a or not title_el:
            continue
        price_el = card.select_one("[data-testid='ad-price']")
        loc_el = card.select_one("[data-testid='location-date']")
        text = card.get_text(" ", strip=True)
        year = re.search(r"\b(19[89]\d|20[0-4]\d)\b", text)
        km = re.search(r"([\d\s]{3,})\s*km\b", text)
        loc = loc_el.get_text(" ", strip=True) if loc_el else ""
        loc = re.split(r"\s+-\s+|Odświeżono|Dzisiaj|\d{1,2} \w+ 20", loc)[0]
        found.append(Listing(
            source="OLX", title=title_el.get_text(strip=True),
            url=urljoin("https://www.olx.pl", a["href"]),
            price=_to_int(price_el.get_text()) if price_el else None,
            year=int(year.group(1)) if year else None,
            mileage=_to_int(km.group(1)) if km else None,
            location=loc.strip(" ,"), description=text,
        ))
    return found


def search(params: SearchParams, log: Log = lambda _m: None) -> List[Listing]:
    """Pobiera ogłoszenia ze wszystkich włączonych źródeł."""
    results: List[Listing] = []
    sources = []
    if params.use_otomoto:
        sources.append(("Otomoto", otomoto_url(params), parse_otomoto))
    if params.use_olx:
        sources.append(("OLX", olx_url(params), parse_olx))
    for name, url, parser in sources:
        log(f"Szukam: {name}…")
        html = _fetch(url, log)
        if html is None:
            log(f"  {name}: brak danych (blokada lub błąd sieci).")
            continue
        items = parser(html)
        log(f"  {name}: {len(items)} ogłoszeń na stronie.")
        results.extend(items)
    return results
