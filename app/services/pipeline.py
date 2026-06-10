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

# create data for price_history table
def insert_price_history():
    """
    Append a price_history row only when the current listing price differs
    from the most recent recorded price (or if no history exists yet),
    limited to listings present in the current scrape.
    """
    db.session.execute(text(r"""
        INSERT INTO price_history (listing_id, price, currency)
        SELECT
            l.id,
            l.price,
            l.currency
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
           OR last_ph.price <> l.price
           OR last_ph.currency <> l.currency;
    """))

def find_set_number(title, valid_set_nums):
    """
    Extracts LEGO set numbers like:
    75313
    75313-1
    (75313)
    Set 75313

    Returns the numeric part as int, or None.
    """

    if not title:
        return None
    
    for num in sorted(valid_set_nums, key=len, reverse=True):
        if num in title:
            # extra safety check: ensure it's not part of a larger digit sequence
            if re.search(rf"(?<!\d){re.escape(num)}(?!\d)", title):
                return num

    patterns = [
        r"\b(\d{5,6})-\d+\b",        # 75313-1 (most reliable)
        r"\bSet\s*#?\s*(\d{5,6})\b", # Set 75313 / Set #75313
        r"\((\d{5,6})\)",            # (75313)
        r"\b(\d{5,6})\b",            # fallback ONLY
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def get_set_nums():
    """
    Updates Listing.set_num using matching TempSummaries titles.
    """

    all_set_nums = {
        str(s.base_set_num).strip()
        for s in LegoSet.query.with_entities(LegoSet.base_set_num).all()
        if s.base_set_num
        and str(s.base_set_num).isdigit()
        and len(str(s.base_set_num)) >= 4
    }

    listings = Listing.query.all()

    for listing in listings:
        temp = TempSummaries.query.filter_by(
            ebay_item_id=listing.ebay_item_id
        ).first()

        if not temp:
            continue

        set_num = find_set_number(temp.title, all_set_nums)

        if set_num:
            listing.set_num = str(set_num)

    

def run_pipeline():
    insert_listings()
    get_set_nums()
    insert_price_history()

    db.session.commit()

with app.app_context():
    run_pipeline()