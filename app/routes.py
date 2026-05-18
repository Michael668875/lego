from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    abort,
    request,
    make_response,
    Response
)
from app.route_helpers import *

from sqlalchemy import func
from app.models import Listing
from app.extensions import db
from datetime import datetime, timedelta

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return render_template("listings.html")

@bp.route("/<country>/")
def listings(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    query = db_query(marketplaces)
    
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 50
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    listings = pagination.items

    return render_template(
        "test_listings.html",
        listings=listings,
        pagination=pagination,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,  
    )

@bp.route("/<country>/overview")
def overview(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    results = (
        db.session.query(
            Listing.set_num,
            func.count(Listing.id).label("count")
        )
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.set_num.isnot(None))
        .group_by(Listing.set_num)
        .order_by(func.count(Listing.id).desc())
        .all()
    )

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

    listings = (
        Listing.query
        .filter(Listing.marketplace.in_(marketplaces))
        .order_by(Listing.price.asc())
        .limit(100)
        .all()
    )

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

    cutoff = datetime.now(datetime.timetzone.utc) - timedelta(days=3) 

    listings = (
        Listing.query
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.status == "ACTIVE")
        .all()
    )

    return render_template(
        "price_drops.html",
        listings=listings,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,
    )

@bp.route("/<country>/models")
def models(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    models = (
        db.session.query(
            Listing.set_num,
            func.min(Listing.price).label("min_price"),
            func.count(Listing.id).label("count"),
        )
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.set_num.isnot(None))
        .group_by(Listing.set_num)
        .order_by(func.count(Listing.id).desc())
        .all()
    )

    return render_template(
        "models.html",
        models=models,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,
    )
