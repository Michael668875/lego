from flask import Blueprint, render_template, redirect, url_for, g, request, abort, Response
from datetime import datetime, timezone
from app.route_helpers import *
from functools import wraps
from collections import defaultdict
from slugify import slugify

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


@bp.app_context_processor
def inject_site_globals():
    return {
        "country": getattr(g, "country", DEFAULT_COUNTRY),
        "country_flags": COUNTRY_FLAGS,
        "currency": getattr(g, "currency", "USD"),
    }



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
def listings(country):

    query = db_query(g.marketplaces)

    listings = page_nums(query)

    return render_template(
        "listings.html",
        listings=listings,
    )

@bp.route("/<country>/<set_num>")
def set_list(country, set_num):

    listings = db_query(g.marketplaces, set_num)

    return render_template(
        "set_type.html",
        listings=listings,
        set_num=set_num,
    )

@bp.route("/<country>/theme/<int:theme_id>")
def theme_sets(country, theme_id):

    theme = Theme.query.get_or_404(theme_id)

    sets = (
        db.session.query(LegoSet)
        .join(
            Listing,
            Listing.set_num == LegoSet.base_set_num
        )
        .filter(
            LegoSet.theme_id == theme_id,
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(g.marketplaces),
        )
        .distinct()
        .order_by(LegoSet.year.desc())
        .all()
    )
    
    return render_template(
        "theme_sets.html",
        theme=theme,
        sets=sets,
    )

@bp.route("/<country>/overview")
def overview(country):
    
    query = db_overview(g.marketplaces)

    results = page_nums(query)

    return render_template(
        "overview.html",
        results=results,
    )

@bp.route("/<country>/best_deals")
def best_deals(country):        

    listings = bestdeals_listings(g.marketplaces)

    return render_template(
        "best_deals.html",
        listings=listings,
    )

@bp.route("/<country>/drops")
def price_drops(country):    

    rows = drops_query(g.marketplaces)

    return render_template(
        "price_drops.html",
        rows=rows,
    )

"""@bp.route("/<country>/models")
def models(country):

    rows = model_query(g.marketplaces)

    grouped = defaultdict(list)
    theme_names = {}

    for row in rows:
        grouped[row.theme_id].append(row)
        theme_names[row.theme_id] = row.theme_name

    return render_template(
        "models.html",
        grouped_models=grouped,
        theme_names=theme_names,
    )"""


@bp.route("/<country>/models")
def models(country):

    rows = model_query(g.marketplaces)

    grouped = defaultdict(list)
    theme_names = {}

    for row in rows:
        grouped[row.theme_id].append(row)
        theme_names[row.theme_id] = row.theme_name

    themes = [
        {
            "id": theme_id,
            "name": theme_names[theme_id],
            "slug": slugify(theme_names[theme_id]),
            "models": grouped[theme_id],
        }
        for theme_id in grouped.keys()
    ]

    return render_template(
        "models.html",
        themes=themes,
    )

@bp.route("/<country>/set/<base_set>")
def set_page(country, base_set):

    set_data = (
        LegoSet.query
        .filter_by(base_set_num=str(base_set))
        .order_by(LegoSet.year.desc())
        .first_or_404()
    )

    stats = db.session.query(
        func.count(Listing.id).label("active_count"),
        func.min(Listing.price).label("cheapest_price")
    ).filter(
        Listing.set_num == base_set,
        Listing.country == g.country.upper()
    ).first()

    return render_template(
        "set_page.html",
        set_data=set_data,
        stats=stats,
    )

@bp.route("/<country>/about")
def about(country):
    return render_template("about.html")


@bp.route("/<country>/how-it-works")
def methodology(country):
    return render_template("methodology.html")

@bp.route("/<country>/affiliate-disclosure")
def affiliate_disclosure(country):
    return render_template("affiliate_disclosure.html")

@bp.route("/<country>/disclaimer")
def disclaimer(country):
    return render_template("disclaimer.html")

@bp.route("/<country>/privacy")
def privacy(country):
    return render_template("privacy.html")


@bp.route("/<country>/terms")
def terms(country):
    return render_template("terms.html")


@bp.route("/<country>/contact")
def contact(country):
    return render_template("contact.html")


