from flask import Blueprint, render_template, redirect, url_for, g, request, abort
from datetime import datetime, timezone
from app.route_helpers import *
from app.models import LegoSet


bp = Blueprint("main", __name__)

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500

@bp.app_template_filter("timeago")
def timeago(dt):
    if not dt:
        return ""

    # If datetime is naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc).astimezone(dt.tzinfo)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} min ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hr ago"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime("%d %b %Y")
    

"""
DEFAULT_COUNTRY = "us"    

@bp.before_app_request
def load_country_context():

    country = None

    # 1. route-based country (if exists)
    if request.view_args:
        country = request.view_args.get("country")

    # 2. cookie fallback
    if not country:
        country = request.cookies.get("country")

    # 3. default fallback
    country = (country or DEFAULT_COUNTRY).lower()

    markets = get_enabled_markets()

    # 4. safety fallback (DO NOT abort globally)
    if country not in markets:
        country = DEFAULT_COUNTRY

    g.country = country
    g.marketplaces = [markets[country]]
    g.currency = CURRENCY_BY_COUNTRY.get(country, "USD")    
"""
from functools import wraps
from flask import g, request

DEFAULT_COUNTRY = "us"

def with_market_context(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        country = kwargs.get("country")

        if not country:
            country = request.cookies.get("country", DEFAULT_COUNTRY)

        country = country.lower()

        markets = get_enabled_markets()

        if country not in markets:
            country = DEFAULT_COUNTRY

        g.country = country
        g.marketplaces = [markets[country]]
        g.currency = CURRENCY_BY_COUNTRY.get(country, "USD")

        return f(*args, **kwargs)

    return wrapper


@bp.app_context_processor
def inject_site_globals():
    return {
        "country": getattr(g, "country", DEFAULT_COUNTRY),
        "country_flags": COUNTRY_FLAGS,
        "currency": getattr(g, "currency", "USD"),
    }


"""@bp.after_app_request
def persist_country_cookie(response):
    if request.view_args and "country" in request.view_args:
        country = request.view_args["country"].lower()
        response.set_cookie("country", country, max_age=60 * 60 * 24 * 365)
    return response"""


@bp.route("/")
def index():
    preferred = request.cookies.get("country")
    valid_countries = set(get_enabled_markets().keys())

    if preferred:
        preferred = preferred.lower()
        if preferred in valid_countries:
            return redirect(url_for("main.listings", country=preferred))

    return redirect(url_for("main.listings", country="us"))

@bp.route("/<country>/")
@with_market_context
def listings(country):

    query = db_query(g.marketplaces)

    listings = page_nums(query)

    return render_template(
        "listings.html",
        listings=listings,
    )

@bp.route("/<country>/overview")
@with_market_context
def overview(country):
    
    query = db_overview(g.marketplaces)

    results = page_nums(query)

    return render_template(
        "overview.html",
        results=results,
    )

@bp.route("/<country>/best_deals")
@with_market_context
def best_deals(country):        

    listings = bestdeals_listings(g.marketplaces)

    return render_template(
        "best_deals.html",
        listings=listings,
    )

@bp.route("/<country>/drops")
@with_market_context
def price_drops(country):    

    rows = drops_query(g.marketplaces)

    return render_template(
        "price_drops.html",
        rows=rows,
    )

@bp.route("/<country>/models")
@with_market_context
def models(country):    

    models = model_query(g.marketplaces)

    return render_template(
        "models.html",
        models=models,
    )

@bp.route("/<base_set>")
def set_page(base_set):

    set_data = (
        LegoSet.query
        .filter_by(base_set_num=base_set)
        .order_by(LegoSet.year.desc())
        .first_or_404()
    )

    stats = db.session.query(
        func.count(Listing.id).label("active_count"),
        func.min(Listing.price).label("cheapest_price")
    ).filter(
        Listing.set_num == base_set
    ).first()

    return render_template(
        "set_page.html",
        set_data=set_data,
        stats=stats,
    )

@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/how-it-works")
def methodology():
    return render_template("methodology.html")

@bp.route("/affiliate-disclosure")
def affiliate_disclosure():
    return render_template("affiliate_disclosure.html")

@bp.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")

@bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@bp.route("/terms")
def terms():
    return render_template("terms.html")


@bp.route("/contact")
def contact():
    return render_template("contact.html")


