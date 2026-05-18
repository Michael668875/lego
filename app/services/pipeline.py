from app.extensions import db
from sqlalchemy import text
import re
from app.models import TempSummaries, Listing

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
            item_country,
            affiliate_url,
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
    db.session.commit()


def find_set_number(title):
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

    patterns = [
        r"\b(\d{4,6})-\d+\b",  # 75313-1
        r"\((\d{4,6})\)",      # (75313)
        r"\bSet\s+(\d{4,6})\b",# Set 75313
        r"\b(\d{4,6})\b",      # plain 75313
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def get_set_nums():
    """
    Updates Listing.set_num using matching TempSummaries titles.
    """

    listings = Listing.query.all()

    for listing in listings:
        temp = TempSummaries.query.filter_by(
            ebay_item_id=listing.ebay_item_id
        ).first()

        if not temp:
            continue

        set_num = find_set_number(temp.title)

        if set_num:
            listing.set_num = set_num

    db.session.commit()
    
with app.app_context():
    insert_listings()
    get_set_nums()
