from flask import abort
from app.models import Listing

COUNTRY_FLAGS = {
    "us": "🇺🇸",
    "au": "🇦🇺",
    "de": "🇩🇪",
    "gb": "🇬🇧",
}

CURRENCY_BY_COUNTRY = {
    "us": "USD",
    "au": "AUD",
    "de": "EUR",
    "gb": "GBP",
}

ENABLED_MARKETS = ["EBAY_US", "EBAY_GB", "EBAY_DE", "EBAY_AU"]

def get_enabled_markets():
    """Return enabled marketplaces as dict keyed by country code."""
    return {m.split("_")[1].lower(): m for m in ENABLED_MARKETS}

def get_market_context(country):
    country = country.lower()
    markets = get_enabled_markets()

    if country not in markets:
        abort(404)

    marketplaces = [markets[country]]
    currency = CURRENCY_BY_COUNTRY.get(country, "")

    return country, marketplaces, currency

def get_country_context_or_404(country):
    """
    Normalize/validate country using your existing market context helper.
    Returns: (country, marketplaces, currency)
    """
    return get_market_context(country)

def db_query(marketplaces):
    return (Listing.query
            .filter(
                Listing.status == "ACTIVE",
                Listing.marketplace.in_(marketplaces),
            ))
    

