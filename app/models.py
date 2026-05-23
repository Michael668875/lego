from app.extensions import db
from datetime import timezone, datetime
from sqlalchemy import func

class TempSummaries(db.Model):
    __tablename__ = "temp_summaries"

    id = db.Column(db.Integer, primary_key=True)

    ebay_item_id = db.Column(db.String, unique=True, nullable=False)

    title = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), nullable=False)

    condition = db.Column(db.String)
    buying_options = db.Column(db.JSON)

    image_urls = db.Column(db.JSON)  # all images

    item_url = db.Column(db.Text)
    affiliate_url = db.Column(db.Text)

    seller_username = db.Column(db.String(100))
    seller_feedback_score = db.Column(db.Integer)
    seller_feedback_percent = db.Column(db.Float)

    categories = db.Column(db.JSON)

    marketplace = db.Column(db.String)

    item_country = db.Column(db.String(2))
    item_city = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))

    item_created_at = db.Column(db.DateTime(timezone=True))

    first_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    sold_at = db.Column(db.DateTime(timezone=True), nullable=True)

class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)

    ebay_item_id = db.Column(db.String, unique=True, nullable=False)

    set_num = db.Column(db.Integer, nullable=True)

    title = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), nullable=False)

    image_urls = db.Column(db.JSON)
    condition = db.Column(db.String)

    marketplace = db.Column(db.String)
    item_country = db.Column(db.String(2))

    status = db.Column(db.String, default="ACTIVE", server_default="ACTIVE", index=True)

    affiliate_url = db.Column(db.Text)

    last_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    price_history = db.relationship(
        "PriceHistory",
        back_populates="listing",
        cascade="all, delete-orphan"
    )

class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    listing = db.relationship("Listing", back_populates="price_history")