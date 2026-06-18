from flask import abort, request, render_template, url_for
from sqlalchemy import func, exists, case, desc
from app.models import Listing, PriceHistory, LegoSet, Theme
from app.extensions import db
from collections import defaultdict
from functools import wraps
from slugify import slugify
from sqlalchemy import or_, and_
from sqlalchemy.orm import aliased


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


def db_query(marketplaces, set_num=None):
    query = (
        Listing.query
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces),
        )
    )

    if set_num:
        query = query.filter(Listing.set_num == set_num)

    return query

# stats for homepage
def homepage_stats(marketplaces):

    # Active listings
    active_listings = (
        Listing.query
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces)
        )
        .count()
    )

    # Top theme
    top_theme = (
        db.session.query(
            Theme.id,
            Theme.name,
            func.count(Listing.id).label("listing_count")
        )
        .join(LegoSet, LegoSet.theme_id == Theme.id)
        .join(
            Listing,
            Listing.set_num == LegoSet.base_set_num
        )
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces)
        )
        .group_by(Theme.id, Theme.name)
        .order_by(func.count(Listing.id).desc())
        .first()
    )

    # Best deals available
    avg_subquery = (
        db.session.query(
            Listing.set_num.label("set_num"),
            func.avg(Listing.price).label("avg_price")
        )
        .filter(
            Listing.marketplace.in_(marketplaces),
            Listing.status == "ACTIVE",
            Listing.set_num.isnot(None)
        )
        .group_by(Listing.set_num)
        .subquery()
    )

    best_deals_count = (
        db.session.query(Listing.id)
        .join(
            avg_subquery,
            Listing.set_num == avg_subquery.c.set_num
        )
        .filter(
            Listing.marketplace.in_(marketplaces),
            Listing.status == "ACTIVE",
            Listing.price <= avg_subquery.c.avg_price * 0.75
        )
        .count()
    )

    return {
        "active_listings": active_listings,
        "top_theme": top_theme.name if top_theme else "N/A",
        "top_theme_id": top_theme.id if top_theme else None,
        "best_deals_count": best_deals_count
    }
   
#overview logic
def db_overview(marketplaces):

    base_q = (
        db.session.query(
            Listing.set_num.label("set_num"),
            func.count(Listing.id).label("count")
        )
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.set_num.isnot(None))
        .group_by(Listing.set_num)
        .subquery()
    )

    cheapest_listing_subq = (
        db.session.query(Listing.id)
        .filter(Listing.set_num == base_q.c.set_num)
        .filter(Listing.marketplace.in_(marketplaces))
        .order_by(Listing.price.asc())
        .limit(1)
        .correlate(base_q)
        .scalar_subquery()
    )

    query = (
        db.session.query(
            base_q.c.set_num,
            base_q.c.count,
            Listing
        )
        .join(Listing, Listing.id == cheapest_listing_subq)
    )

    return query, base_q


# best deals logic
def db_bestdeals(marketplaces):
    return (
        db.session.query(
            Listing.set_num.label("set_num"),
            func.avg(Listing.price).label("avg_price")
        )
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.set_num.isnot(None))
        .filter(Listing.price.isnot(None))
        .filter(Listing.status == "ACTIVE")
        .group_by(Listing.set_num)
        .subquery()
    )

# Listings 25%+ below average
def bestdeals_listings(marketplaces):
    avg_subquery = db_bestdeals(marketplaces)

    discount_expr = (
        (avg_subquery.c.avg_price - Listing.price)
        / avg_subquery.c.avg_price
    ).label("discount")

    query = (
        db.session.query(
            Listing,
            avg_subquery.c.avg_price.label("avg_price"),
            discount_expr
        )
        .join(
            avg_subquery,
            Listing.set_num == avg_subquery.c.set_num
        )
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.status == "ACTIVE")
        .filter(Listing.price <= avg_subquery.c.avg_price * 0.75)
    )

    return query, discount_expr


# price drops logic

def drops_query(marketplaces):

    ranked = (
        db.session.query(
            PriceHistory.listing_id.label("listing_id"),
            PriceHistory.price.label("new_price"),
            PriceHistory.recorded_at.label("recorded_at"),

            Listing.set_num.label("set_num"),
            Listing.title.label("title"),
            Listing.ebay_item_id.label("ebay_item_id"),
            Listing.affiliate_url.label("affiliate_url"),
            Listing.currency.label("currency"),

            func.lag(PriceHistory.price).over(
                partition_by=PriceHistory.listing_id,
                order_by=(
                    PriceHistory.recorded_at.asc(),
                    PriceHistory.id.asc()
                )
            ).label("old_price"),
        )
        .join(Listing, Listing.id == PriceHistory.listing_id)
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces),
            Listing.set_num.isnot(None),
        )
        .subquery()
    )

    query = (
        db.session.query(
            ranked.c.set_num,
            ranked.c.title,
            ranked.c.ebay_item_id,
            ranked.c.affiliate_url,
            ranked.c.currency,
            ranked.c.new_price,
            ranked.c.old_price,
            (
                (ranked.c.old_price - ranked.c.new_price)
                / ranked.c.old_price * 100
            ).label("discount_percent"),
            LegoSet.name.label("canon_name"),
            LegoSet.img_url.label("image_url"),
        )
        .outerjoin(
            LegoSet,
            LegoSet.base_set_num == ranked.c.set_num
        )
        .filter(
            ranked.c.old_price.isnot(None),
            ranked.c.new_price < ranked.c.old_price
        )
    )

    return query, ranked

# models logic
def model_query(marketplaces):
    return (
        db.session.query(
            Listing.set_num,
            LegoSet.name.label("name"),
            LegoSet.theme_id.label("theme_id"),
            Theme.name.label("theme_name"),
            func.count(Listing.id).label("count"),
            func.max(Listing.last_seen).label("last_seen"),
        )
        .join(LegoSet, Listing.set_num == LegoSet.base_set_num)
        .join(Theme, LegoSet.theme_id == Theme.id)
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces)
        )
        .group_by(
            Listing.set_num,
            LegoSet.name,
            LegoSet.theme_id,
            Theme.name,           
        )
        .order_by(func.count(Listing.id).desc())
        .all()
    )

def theme_query(rows):

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
    return themes


# Pagination
def paginate(query, per_page=50):
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return PaginationWrapper(pagination)

def build_pagination_args(**new_args):
    args = request.args.to_dict(flat=True)
    args.update(new_args)
    return args

def page_url(page):
    args = build_pagination_args(page=page)
    return url_for(request.endpoint, **request.view_args, **args)

class PaginationWrapper:
    def __init__(self, pagination):
        self.pagination = pagination

    @property
    def items(self):
        return self.pagination.items

    @property
    def page(self):
        return self.pagination.page

    @property
    def pages(self):
        return self.pagination.pages

    @property
    def has_next(self):
        return self.pagination.has_next

    @property
    def has_prev(self):
        return self.pagination.has_prev

    @property
    def next_num(self):
        return self.pagination.next_num

    @property
    def prev_num(self):
        return self.pagination.prev_num

    def url_for_page(self, page):
        args = build_pagination_args(page=page)
        return url_for(request.endpoint, **request.view_args, **args)
    
    def iter_pages(
        self,
        left_edge=1,
        left_current=2,
        right_current=2,
        right_edge=1
    ):
        return self.pagination.iter_pages(
            left_edge=left_edge,
            left_current=left_current,
            right_current=right_current,
            right_edge=right_edge
        )



def get_sets(theme_id, marketplaces):
    return (
        db.session.query(LegoSet)
        .join(
            Listing,
            Listing.set_num == LegoSet.base_set_num
        )
        .filter(
            LegoSet.theme_id == theme_id,
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces),
        )
        .distinct()
        .order_by(LegoSet.year.desc())
        .all()
    )


def get_set_data(base_set, country):

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
        Listing.country == country.upper(),
        Listing.status == "ACTIVE"
    ).first()

    return set_data, stats

def search_query():
    q = request.args.get("q", "").strip()

    if not q:
        return render_template(
            "search_results.html",
            results=[],
            query=q
        )

    raw_results = (
        LegoSet.query
        .filter(
            db.exists().where(
                (Listing.set_num == LegoSet.base_set_num) &
                (Listing.status == "ACTIVE")
            )
        )
        .filter(
            db.or_(
                LegoSet.base_set_num.ilike(f"%{q}%"),
                LegoSet.name.ilike(f"%{q}%"),
                Theme.name.ilike(f"%{q}%")
            )
        )
        .join(Theme)
        .distinct()
        .add_columns(
            case(
                (LegoSet.base_set_num.ilike(q), 100),
                (LegoSet.base_set_num.ilike(f"%{q}%"), 80),
                (LegoSet.name.ilike(f"%{q}%"), 50),
                (Theme.name.ilike(f"%{q}%"), 30),
                else_=0
            ).label("score")
        )
        .order_by(LegoSet.year.desc())
        .all()
    )

    results = [legoset for legoset, score in raw_results]
    print(raw_results)
    return q, results

def sort_listings(query, sort, direction):

    sort_columns = {
        "price": Listing.price,
        "set_num": Listing.set_num,
    }

    column = sort_columns.get(sort, Listing.price)

    if direction == "asc":
        return query.order_by(column.asc())

    return query.order_by(column.desc())

def sort_deals(query, sort, direction, discount_expr=None):

    sort_columns = {
        "price": Listing.price,
        "set_num": Listing.set_num,
        "discount": discount_expr,
    }

    column = sort_columns.get(sort, discount_expr)

    if direction == "asc":
        return query.order_by(column.asc())

    return query.order_by(column.desc())

def sort_overview(query, sort, direction, l_count):

    sort_columns = {
        "price": Listing.price,
        "set_num": Listing.set_num,
        "count": l_count,
    }

    column = sort_columns.get(sort, l_count)

    if direction == "asc":
        return query.order_by(column.asc())
    return query.order_by(column.desc())

def sort_drops(query, sort, direction, set_num, old_price, new_price):
    
    discount_percent = ((old_price - new_price) / old_price * 100)

    sort_columns = {
        "set_num": set_num,
        "old_price": old_price,
        "new_price": new_price,
        "discount_percent": discount_percent
    }

    column = sort_columns.get(sort, discount_percent)

    if direction == "asc":
        return query.order_by(column.asc())

    return query.order_by(column.desc())