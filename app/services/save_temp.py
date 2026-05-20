from decimal import Decimal
from datetime import datetime
from app import db
from app.models import TempSummaries
import re

def clean_text(text: str) -> str: 
    # remove emojis and weird symbols
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    return text.strip()

def extract_images(item):
    urls = []

    image = item.get("image") or {}

    for k in ["imageUrl", "originalImageUrl", "thumbnailImageUrl"]:
        if image.get(k):
            urls.append(image[k])

    for arr in ["additionalImages", "thumbnailImages"]:
        for img in item.get(arr, []) or []:
            if isinstance(img, dict) and img.get("imageUrl"):
                urls.append(img["imageUrl"])

    for k in ["galleryPlusPictureURL", "pictureURLLarge", "pictureURLSuperSize"]:
        if item.get(k):
            urls.append(item[k])

    return list(dict.fromkeys(urls))  # remove duplicates

def save_temp_summaries(items):
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

        if item_id in existing:
            continue

        price_info = item.get("price", {})
        price_value = price_info.get("value")

        # datetime
        item_created_at = None
        if item.get("itemCreationDate"):
            item_created_at = datetime.fromisoformat(
                item["itemCreationDate"].replace("Z", "+00:00")
            )

        # images
        image_urls = extract_images(item)

        # seller
        seller = item.get("seller", {})

        # location
        location = item.get("itemLocation", {})

        # feedback
        percent = seller.get("feedbackPercentage")

        listing = TempSummaries(
            ebay_item_id=item_id,
            title=clean_text(item.get("title", "")),

            price=Decimal(str(price_value)) if price_value else None,
            currency=price_info.get("currency"),

            condition=item.get("condition"),
            buying_options=item.get("buyingOptions", []),

            image_urls=image_urls,

            item_url=item.get("itemWebUrl"),
            affiliate_url=item.get("itemAffiliateWebUrl"),

            seller_username=seller.get("username"),
            seller_feedback_score=seller.get("feedbackScore"),
            
            seller_feedback_percent = (float(percent.replace("%", "")) if percent else None),

            categories=item.get("categories", []),

            marketplace=item.get("marketplace_id"),

            item_country=location.get("country"),
            item_city=location.get("city"),
            postal_code=location.get("postalCode"),

            item_created_at=item_created_at,
        )

        db.session.add(listing)
        inserted += 1

    db.session.commit()
    print(f"Inserted {inserted} into temp db.")