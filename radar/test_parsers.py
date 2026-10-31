import json
import filters
import notifier
import scraper
from models import DEFAULT_EXCLUDED, Listing, SearchParams


def test_otomoto_json():
    data = {"props": {"x": [{"title": "Mercedes CLA 250", "url":
            "https://www.otomoto.pl/osobowe/oferta/a-1.html",
            "price": {"amount": {"units": 29900}}, "shortDescription": "ok",
            "parameters": [{"key": "year", "value": "2015"},
                           {"key": "mileage", "value": "120000"}],
            "location": {"city": {"name": "Katowice"}}}]}}
    html = f'<script id="__NEXT_DATA__">{json.dumps(data)}</script>'
    [l] = scraper.parse_otomoto(html)
    assert (l.price, l.year, l.mileage, l.location) == (
        29900, 2015, 120000, "Katowice")


def test_olx_cards():
    html = ('<div data-cy="l-card"><a href="/d/oferta/x.html"></a>'
            '<h4>Audi A4 2012</h4><p data-testid="ad-price">20 000 zł</p>'
            '<p data-testid="location-date">Kraków - Dzisiaj</p>'
            '<span>2012 - 150 000 km</span></div>')
    [l] = scraper.parse_olx(html)
    assert l.price == 20000 and l.year == 2012 and l.location == "Kraków"
    assert l.mileage == 150000 and l.url.startswith("https://www.olx.pl/")


def test_filters_and_message():
    p = SearchParams(brand="Mercedes", model="CLA", year_from=2014,
                     price_to=30000, excluded_phrases=DEFAULT_EXCLUDED)
    ok = Listing("OLX", "Mercedes CLA 250", "u", 25000, 2015)
    bad = Listing("OLX", "Mercedes CLA po powodzi", "u2", 25000, 2015)
    assert filters.matches(ok, p) and not filters.matches(bad, p)
    assert not filters.matches(Listing("OLX", "Mercedes CLA", "u", 40000, 2015), p)
    assert notifier.format_message(p, ok).startswith("@everyone")


def test_urls():
    p = SearchParams(brand="Mercedes-Benz", model="CLA", year_from=2014,
                     price_to=30000)
    assert "/mercedes-benz/cla/od-2014" in scraper.otomoto_url(p)
    assert "q-Mercedes-Benz-CLA" in scraper.olx_url(p)
