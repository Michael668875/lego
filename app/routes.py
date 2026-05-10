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
from app.models import Listing
from app.route_helpers import *

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    return "hello this works"

@bp.route("/<country>/")
def listings(country):
    country, marketplaces, currency = get_country_context_or_404(country)

    query = (
        Listing.query
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces),
        )
    )

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 50
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    listings = pagination.items

    return render_template(
        "listings.html",
        listings=listings,
        pagination=pagination,
        country=country,
        currency=currency,
        country_flags=COUNTRY_FLAGS,  
    )

@bp.route("/<country>/overview")
def overview():
    pass

@bp.route("/<country>/best_deals")
def best_deals():
    pass

@bp.route("/<country>/drops")
def price_drops():
    pass

@bp.route("/<country>/models")
def models():
    pass
