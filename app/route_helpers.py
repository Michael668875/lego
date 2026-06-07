from flask import abort, request
from sqlalchemy import func
from app.models import Listing, PriceHistory, LegoSet, Theme
from app.extensions import db





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

    return (
        db.session.query(
            base_q.c.set_num,
            base_q.c.count,
            Listing
        )
        .join(Listing, Listing.id == cheapest_listing_subq)
        .order_by(base_q.c.count.desc())
    )


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
    return (
        db.session.query(
            Listing,
            avg_subquery.c.avg_price
        )
        .join(
            avg_subquery,
            Listing.set_num == avg_subquery.c.set_num
        )
        .filter(Listing.marketplace.in_(marketplaces))
        .filter(Listing.status == "ACTIVE")
        .filter(Listing.price <= avg_subquery.c.avg_price * 1) #1 for debugging. set to 0.75 later
        .order_by(
            (
                (avg_subquery.c.avg_price - Listing.price)
                / avg_subquery.c.avg_price
            ).desc()
        )
        .limit(100)
        .all()
    )


# price drops logic
def old_price_query():
    return func.lag(PriceHistory.price).over(
        partition_by=PriceHistory.listing_id,
        order_by=(PriceHistory.recorded_at, PriceHistory.id)
    )

def changes_query(marketplaces):
    old_price = old_price_query()
    return (
            db.session.query(
                PriceHistory.listing_id.label("listing_id"),

                Listing.set_num.label("set_num"),
                Listing.title.label("title"),

                Listing.ebay_item_id.label("ebay_item_id"),
                Listing.affiliate_url.label("affiliate_url"),

                PriceHistory.price.label("new_price"),
                old_price.label("old_price"),

                Listing.currency.label("currency"),
            )
            .join(Listing, Listing.id == PriceHistory.listing_id)
            .filter(
                Listing.status == "ACTIVE",
                Listing.marketplace.in_(marketplaces),
                Listing.set_num.isnot(None),
            )
            .subquery()
        )

def drops_query(marketplaces):

    price_changes_subq = changes_query(marketplaces)

    return (
        db.session.query(
            price_changes_subq.c.set_num,
            price_changes_subq.c.title,

            price_changes_subq.c.ebay_item_id,

            price_changes_subq.c.old_price,
            price_changes_subq.c.new_price,

            (
                price_changes_subq.c.old_price
                - price_changes_subq.c.new_price
            ).label("drop_amount"),

            (
                (
                    price_changes_subq.c.old_price
                    - price_changes_subq.c.new_price
                )
                / price_changes_subq.c.old_price * 100
            ).label("discount_percent"),

            price_changes_subq.c.currency,
            price_changes_subq.c.affiliate_url,
        )
        # remove filter for debuggin. restore later
        #.filter( 
        #    price_changes_subq.c.old_price.isnot(None),
        #    price_changes_subq.c.new_price < price_changes_subq.c.old_price,
        #)
        .all()
    )

# models logic
"""def model_query(marketplaces):
    return (
        db.session.query(
            Listing.set_num,
            func.count(Listing.id).label("count"),
            func.max(Listing.last_seen).label("last_seen"),
        )
        .filter(
            Listing.status == "ACTIVE",
            Listing.marketplace.in_(marketplaces)
        )
        .filter(Listing.set_num.isnot(None))
        .group_by(Listing.set_num)
        .order_by(func.count(Listing.id).desc())
        .all()
    )"""

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

# Pagination
def page_nums(query, pages = 50):
    page = request.args.get("page", 1, type=int)
    per_page = pages  
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination.items