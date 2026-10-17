from flask import Blueprint, render_template, redirect, url_for, g, request, send_from_directory, current_app, make_response
from datetime import datetime, timezone
from app.route_helpers import *
from app.models import PriceDrop, OverviewSets, BestDeals, AvailableSets

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
    

# DEFAULT_COUNTRY = "us"    

# @bp.before_app_request
# def load_country_context():

#     country = None

#     # 1. route-based country (if exists)
#     if request.view_args:
#         country = request.view_args.get("country")

#     # 2. cookie fallback
#     if not country:
#         country = request.cookies.get("country")

#     # 3. default fallback
#     country = (country or DEFAULT_COUNTRY).lower()

#     markets = get_enabled_markets()

#     # 4. safety fallback (DO NOT abort globally)
#     if country not in CURRENCY_BY_COUNTRY:
#         country = DEFAULT_COUNTRY

#     g.country = country.upper()
#     g.currency = CURRENCY_BY_COUNTRY.get(g.country, "USD")  

DEFAULT_COUNTRY = "us"

@bp.before_app_request
def load_country_context():
    country = None

    # 1. Country from the route
    if request.view_args:
        country = request.view_args.get("country")

    # 2. Cookie fallback
    if not country:
        country = request.cookies.get("country")

    # 3. Default fallback
    country = (country or DEFAULT_COUNTRY).lower()

    # 4. Validate country
    if country not in CURRENCY_BY_COUNTRY:
        country = DEFAULT_COUNTRY

    g.country = country.upper()
    g.currency = CURRENCY_BY_COUNTRY.get(country, "USD")


@bp.app_context_processor
def inject_site_globals():
    return {
        "country": getattr(g, "country", DEFAULT_COUNTRY),
        "country_flags": COUNTRY_FLAGS,
        "currency": getattr(g, "currency", "USD"),
    }



# @bp.route("/")
# def index():
#     preferred = request.cookies.get("country")
#     valid_countries = set(get_enabled_markets().keys())

#     if preferred:
#         preferred = preferred.lower()
#         if preferred in valid_countries:
#            return redirect(url_for("main.listings", country=preferred))

#     return redirect(url_for("main.listings", country="us"))

@bp.route("/")
def index():
    preferred = (request.cookies.get("country") or "").lower()

    if preferred in CURRENCY_BY_COUNTRY:
        return redirect(url_for("main.listings", country=preferred))

    return redirect(url_for("main.listings", country=DEFAULT_COUNTRY))

@bp.route("/<country>/")
def listings(country):    

    query = db_query(g.country)

    query = sort_listings(
        query,
        request.args.get("sort", "price"),
        request.args.get("direction", "desc")
    )

    listings = paginate(query)

    stats = homepage_stats(g.country)

    response = make_response(render_template(
        "listings.html",
        listings=listings,
        sets=listings.items,
        active_listings=stats["active_listings"],
        top_theme=stats["top_theme"],
        top_theme_id=stats["top_theme_id"],
        best_deals_count=stats["best_deals_count"]
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/<set_num>")
def set_list(country, set_num):

    listings = db_query(g.country, set_num)

    listings = sort_listings(
            listings,
            request.args.get("sort", "price"),
            request.args.get("direction", "desc")
        )

    response = make_response(render_template(
        "set_list.html",
        listings=listings,
        set_num=set_num,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/theme/<int:theme_id>")
def theme_sets(country, theme_id):

    theme = Theme.query.get_or_404(theme_id)

    sets = get_sets(theme_id, g.country)
    
    response = make_response(render_template(
        "theme_sets.html",
        theme=theme,
        sets=sets,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/overview")
def overview(country):

    country = country.upper()

    query = (
        db.session.query(
            Listing,
            OverviewSets.count.label("count"),
            OverviewSets.set_num.label("set_num"),
        )
        .join(
            OverviewSets,
            Listing.id == OverviewSets.cheapest_listing_id
        )
        .filter(OverviewSets.country == country)
    )

    sort = request.args.get("sort", "count")
    direction = request.args.get("direction", "desc")

    sort_columns = {
        "count": OverviewSets.count,
        "set_num": OverviewSets.set_num,
        "price": Listing.price,
    }

    sort_column = sort_columns.get(sort, OverviewSets.count)

    if direction == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    listings = paginate(query)

    response = make_response(
        render_template(
            "overview.html",
            listings=listings,
            sets=listings.items,
        )
    )

    response.headers["Cache-Control"] = "public, max-age=60"

    return response

@bp.route("/<country>/best_deals")
def best_deals(country):
    country = country.upper()

    query = (
        db.session.query(
            Listing,
            BestDeals.avg_price.label("avg_price"),
            BestDeals.discount.label("discount"),
        )
        .join(
            BestDeals,
            Listing.id == BestDeals.listing_id
        )
        .filter(BestDeals.country == country)
    )

    sort_columns = {
        "discount": BestDeals.discount,
        "price": Listing.price,
        "set_num": BestDeals.set_num,
    }

    sort = request.args.get("sort", "discount")
    direction = request.args.get("direction", "desc")
    sort_column = sort_columns.get(sort, BestDeals.discount)

    if direction == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    listings = paginate(query)

    response = make_response(render_template(
        "best_deals.html",
        listings=listings,
        sets=listings.items,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/drops")
def price_drops(country):

    query = PriceDrop.query.filter_by(
        country=country.upper(),
        status="ACTIVE",
    )

    query = sort_drops(
        query,
        request.args.get("sort", "discount_percent"),
        request.args.get("direction", "desc"),
        PriceDrop.ebay_item_id,
        PriceDrop.old_price,
        PriceDrop.price,
    )

    listings = paginate(query)

    response = make_response(render_template(
        "price_drops.html",
        listings=listings,
        sets=listings.items,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/models")
def models(country):

    rows = AvailableSets.query.filter_by(
        country=country.upper(),
    ).order_by(
        AvailableSets.count.desc()
    ).all()

    themes = theme_query(rows)

    response = make_response(render_template(
        "models.html",
        themes=themes,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/set/<base_set>")
def set_page(country, base_set):

    set_data, stats = get_set_data(base_set, g.country)

    response = make_response(render_template(
        "set_page.html",
        set_data=set_data,
        stats=stats,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/search")
def search(country):

    q, results = search_query()

    response = make_response(render_template(
        "search_results.html",
        results=results,
        query=q
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

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


@bp.route("/sitemap.xml")
def sitemap():
    return redirect(
        url_for(
            "static",
            filename="sitemaps/sitemap.xml"
        )
    )

@bp.route("/robots.txt")
def robots():
    return send_from_directory(
        current_app.static_folder,
        "robots.txt"
    )