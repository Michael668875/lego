from app.extensions import db
from sqlalchemy import text
import re
from app.models import TempSummaries, Listing, LegoSet

from app import create_app

app = create_app()

def insert_listings():

    db.session.execute(text(r"""
        INSERT INTO listings (
            ebay_item_id,
            title,
            price,
            currency,
            image_urls,
            condition,
            marketplace,
            country,
            affiliate_url,
            last_seen,
            status
        )
        SELECT
            ts.ebay_item_id,
            ts.title,
            ts.price,
            ts.currency,
            ts.image_urls,
            ts.condition,
            ts.marketplace,
            ts.item_country,
            ts.affiliate_url,
            ts.last_seen,
            'ACTIVE'
        FROM temp_summaries ts
        WHERE EXISTS (
            SELECT 1
            FROM json_array_elements(ts.categories) AS cat
            WHERE cat->>'categoryId' IN (
                '19006',                
                '183446',
                '183447'
            )
        )
        ON CONFLICT (ebay_item_id) DO NOTHING;                            
                            """))


# update the price if it has changed
def update_listing_prices():
    db.session.execute(text(r"""
        UPDATE listings l
        SET
            price = ts.price,
            last_updated = NOW()
        FROM temp_summaries ts
        WHERE l.ebay_item_id = ts.ebay_item_id
        AND l.status = 'ACTIVE'
        AND l.price <> ts.price;
    """))

def mark_sold_listings():
    """
    Mark listings as ENDED if temp_summaries.sold_at is not NULL.
    """
    result = db.session.execute(text(r"""
        UPDATE listings l
        SET
            status = 'ENDED',
            ended_at = ts.sold_at,
            last_updated = NOW()
        FROM temp_summaries ts
        WHERE l.ebay_item_id = ts.ebay_item_id
        AND ts.sold_at IS NOT NULL
        AND l.status != 'ENDED';
    """))
    print(f"Marked {result.rowcount} listings as sold.")

# update last_seen, miss_count, last_updated 
# each time a listing appears from api
def update_seen_listings():
    db.session.execute(text(r"""
        UPDATE listings l
        SET
            status = 'ACTIVE',
            miss_count = 0,
            last_seen = NOW(),
            last_updated = NOW(),
            ended_at = NULL
        FROM temp_summaries ts
        WHERE l.ebay_item_id = ts.ebay_item_id;
    """))

# increment the miss_count so listings can be marked as ended.
def increment_miss_count():
    db.session.execute(text(r"""
        UPDATE listings l
        SET
            miss_count = miss_count + 1,
            last_updated = NOW()
        WHERE status = 'ACTIVE'
        AND NOT EXISTS (
            SELECT 1
            FROM temp_summaries ts
            WHERE ts.ebay_item_id = l.ebay_item_id
        );
    """))

# change status to ended for listings
# changed miss_count >= 12; - will mark ended if not seen for 48 hours
def mark_ended_listings():
    result = db.session.execute(text(r"""
        UPDATE listings
        SET
            status = 'ENDED',
            ended_at = NOW(),
            last_updated = NOW()
        WHERE status = 'ACTIVE'
        AND miss_count >= 12; 
    """))
    print(f"Marked {result.rowcount} listings as ended.")



# create data for price_history table
def insert_price_history():
    result = db.session.execute(text(r"""
        INSERT INTO price_history (listing_id, price, currency)
        SELECT
            l.id,
            ts.price,
            ts.currency
        FROM listings l
        JOIN temp_summaries ts
            ON ts.ebay_item_id = l.ebay_item_id
        LEFT JOIN LATERAL (
            SELECT ph.price, ph.currency
            FROM price_history ph
            WHERE ph.listing_id = l.id
            ORDER BY ph.recorded_at DESC, ph.id DESC
            LIMIT 1
        ) last_ph ON TRUE
        WHERE last_ph.price IS NULL
           OR last_ph.price <> ts.price
           OR last_ph.currency <> ts.currency
    """))

    print("History rows inserted:", result.rowcount)
    
def find_set_number(title, valid_set_nums):
    if not title:
        return None

    patterns = [
        r"\b(\d{5,6})-\d+\b",
        r"\bSet\s*#?\s*(\d{5,6})\b",
        r"\((\d{5,6})\)",
        r"\b(\d{5,6})\b",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, title, re.IGNORECASE):
            num = match.group(1)
            if num in valid_set_nums:
                return num

    return None

def get_set_nums():
    all_set_nums = {
        str(s).strip()
        for (s,) in LegoSet.query.with_entities(
            LegoSet.base_set_num
        ).all()
        if s and str(s).isdigit() and len(str(s)) >= 4
    }

    # Load all temporary summaries into a dictionary once
    temp_titles = dict(
        db.session.query(
            TempSummaries.ebay_item_id,
            TempSummaries.title
        ).all()
    )

    listings = Listing.query.with_entities(
        Listing.id,
        Listing.ebay_item_id
    ).all()

    updated = 0

    for listing_id, ebay_item_id in listings:
        title = temp_titles.get(ebay_item_id)
        if not title:
            continue

        set_num = find_set_number(title, all_set_nums)

        if set_num:
            db.session.query(Listing).filter_by(
                id=listing_id
            ).update(
                {Listing.set_num: str(set_num)},
                synchronize_session=False
            )
            updated += 1

    db.session.commit()
    print(f"Updated set numbers for {updated} listings.", flush=True)

# delete temp data
def truncate_temp_tables():
    """
    Clear temp tables for next scrape.
    """
    db.session.execute(text(r"""
        TRUNCATE temp_summaries;
    """))

def run_pipeline():
    import time

    steps = [
        ("Insert listings", insert_listings),
        ("Match set numbers", get_set_nums),
        ("Update listing prices", update_listing_prices),
        ("Insert price history", insert_price_history),
        ("Update seen listings", update_seen_listings),
        ("Mark sold listings", mark_sold_listings),
        ("Increment miss counts", increment_miss_count),
        ("Mark ended listings", mark_ended_listings),
    ]

    try:
        for name, func in steps:
            start = time.perf_counter()
            print(f"Starting: {name}", flush=True)

            func()

            print(
                f"Finished: {name} ({time.perf_counter() - start:.1f}s)",
                flush=True
            )

        start = time.perf_counter()
        db.session.commit()
        print(
            f"Database commit finished "
            f"({time.perf_counter() - start:.1f}s)",
            flush=True
        )

    except Exception:
        db.session.rollback()
        raise
    

#def run_pipeline():
#    insert_listings()
#    get_set_nums()
#    update_listing_prices()
#    insert_price_history()
#    update_seen_listings()
#    mark_sold_listings()
#    increment_miss_count()
#    mark_ended_listings()
#
#    db.session.commit()

#with app.app_context():
#    run_pipeline()
