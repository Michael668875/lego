from flask import Blueprint, render_template, redirect, url_for, g, request, send_from_directory, current_app, make_response
from datetime import datetime, timezone
from app.route_helpers import *


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

    query = sort_listings(
        query,
        request.args.get("sort", "price"),
        request.args.get("direction", "desc")
    )

    listings = paginate(query)

    stats = homepage_stats(g.marketplaces)

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

    listings = db_query(g.marketplaces, set_num)

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

    sets = get_sets(theme_id, g.marketplaces)
    
    response = make_response(render_template(
        "theme_sets.html",
        theme=theme,
        sets=sets,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/overview")
def overview(country):
    
    query, base_q = db_overview(g.marketplaces)

    query = sort_overview(
        query,
        request.args.get("sort", "count"),
        request.args.get("direction", "desc"),
        base_q.c.count
    )

    listings = paginate(query)

    response = make_response(render_template(
        "overview.html",
        listings=listings,
        sets = listings.items,
    ))

    response.headers["Cache-Control"] = "public, max-age=60"
    return response

@bp.route("/<country>/best_deals")
def best_deals(country):        

    query, discount_expr = bestdeals_listings(g.marketplaces)
    
    query = sort_deals(
        query,
        request.args.get("sort", "discount"),
        request.args.get("direction", "desc"),
        discount_expr
    )

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

    query, ranked = drops_query(g.marketplaces)

    query = sort_drops(
        query,
        request.args.get("sort", "discount_percent"),
        request.args.get("direction", "desc"),
        ranked.c.set_num,
        ranked.c.old_price,
        ranked.c.new_price,
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

    rows = model_query(g.marketplaces)

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