from decimal import Decimal
from datetime import datetime
from app import db
from app.models import TempSummaries
import re

def clean_text(text: str) -> str: 
    # remove emojis and weird symbols
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    return text.strip()


def save_temp_summaries(items):
    
    # Load all rows once
    ids = [item["itemId"] for item in items if "itemId" in item]

    existing = {
        row.ebay_item_id: row
        for row in TempSummaries.query.filter(
            TempSummaries.ebay_item_id.in_(ids)
        )
    }

    inserted = 0

    for item in items:
        item_id = item.get("itemId")
        if not item_id:
            continue

        price_info = item.get("price", {})
        price_value = price_info.get("value")
        category_id = item.get("leafCategoryIds", [None])[0]
        creation_date = None
        location = item.get("itemLocation", {})
        if item.get("itemCreationDate"):
            creation_date = datetime.fromisoformat(
                item["itemCreationDate"].replace("Z", "+00:00")
            )

        listing = existing.get(item_id)

        if listing:
            continue  # skip creating a new listing

        # Create temporary listing with category
        listing = TempSummaries(
            category_id=category_id,
            ebay_item_id=item_id,
            title = clean_text(item.get("title", "")),
            price=Decimal(str(price_value)) if price_value else None,
            currency= price_info.get("currency"),
            condition=item.get("condition"),
            listing_type=",".join(item.get("buyingOptions", [])),
            marketplace=item.get("marketplace_id"),            
            item_country = location.get("country"),
            item_url=item.get("itemWebUrl"),
            affiliate_url=item.get("itemAffiliateWebUrl"),
            creation_date = creation_date            
        )
        db.session.add(listing)
        db.session.flush()       

        inserted += 1

    db.session.commit()
    print(f"Inserted {inserted} into temp db.")