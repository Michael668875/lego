from flask import Blueprint, render_template 

from app.route_helpers import *


bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("listings.html")

@bp.route("/<country>/")
def listings(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    query = db_query(marketplaces)

    listings = page_nums(query)

    return render_template(
        "test_listings.html",
        listings=listings,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,  
    )

@bp.route("/<country>/overview")
def overview(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    query = db_overview(marketplaces)

    results = page_nums(query)

    return render_template(
        "overview.html",
        country=country,
        results=results,
        currency=currency,
        country_flags=COUNTRY_FLAGS,
    )

@bp.route("/<country>/best_deals")
def best_deals(country):
    country, marketplaces, currency = get_country_context_or_404(country)    

    listings = bestdeals_listings(marketplaces)

    return render_template(
        "best_deals.html",
        listings=listings,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,
    )

@bp.route("/<country>/drops")
def price_drops(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    rows = drops_query(marketplaces)

    return render_template(
        "price_drops.html",
        rows=rows,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,
    )

@bp.route("/<country>/models")
def models(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    models = model_query(marketplaces)

    return render_template(
        "models.html",
        models=models,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,
    )
