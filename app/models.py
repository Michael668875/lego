from app import db
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

    set_num = db.Column(db.String(32), index=True)

    title = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), nullable=False)

    image_urls = db.Column(db.JSON)
    condition = db.Column(db.String)

    marketplace = db.Column(db.String)
    country = db.Column(db.String(2))

    status = db.Column(db.String, default="ACTIVE", server_default="ACTIVE", index=True)

    affiliate_url = db.Column(db.Text)

    last_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    miss_count = db.Column(db.Integer, nullable=True, default=0)
    ended_at = db.Column(db.DateTime, nullable=True)

    last_updated = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index(
            "ix_listings_active_marketplace_setnum",
            "status",
            "marketplace",
            "set_num",
        ),
    )

    price_history = db.relationship(
        "PriceHistory",
        back_populates="listing",
        cascade="all, delete-orphan"
    )

    lego_set = db.relationship(
        "LegoSet",
        primaryjoin="foreign(Listing.set_num) == LegoSet.base_set_num",
        viewonly=True,
        uselist=False
    )

class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    recorded_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    listing = db.relationship("Listing", back_populates="price_history")

    __table_args__ = (
        db.Index(
            "ix_pricehistory_listing_time",
            "listing_id",
            "recorded_at",
            "id",
        ),
    )


class LegoSet(db.Model):
    __tablename__ = "lego_sets"

    id = db.Column(db.Integer, primary_key=True)

    # Rebrickable canonical set number
    suffix_set_num = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Base set number without suffix
    base_set_num = db.Column(db.String(32), index=True)

    name = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, index=True)
    theme_id = db.Column(db.Integer, db.ForeignKey("themes.id"), index=True)
    num_parts = db.Column(db.Integer)
    img_url = db.Column(db.Text)

    theme = db.relationship("Theme")

    def __repr__(self):
        return f"<LegoSet {self.base_set_num} {self.name}>"
    
class Theme(db.Model):
    __tablename__ = "themes"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), nullable=False)

    parent_id = db.Column(
        db.Integer,
        db.ForeignKey("themes.id"),
        nullable=True
    )

    parent = db.relationship(
        "Theme",
        remote_side=[id],
        backref="children"
    )

class SetPriceStats(db.Model):
    __tablename__ = "set_price_stats"

    id = db.Column(db.Integer, primary_key=True)

    set_id = db.Column(db.Integer, db.ForeignKey("lego_sets.id"))
    marketplace = db.Column(db.String(10))

    listing_count = db.Column(db.Integer)

    min_price = db.Column(db.Numeric(10, 2))
    avg_price = db.Column(db.Numeric(10, 2))
    median_price = db.Column(db.Numeric(10, 2))
    max_price = db.Column(db.Numeric(10, 2))

    updated_at = db.Column(db.DateTime(timezone=True))

    lego_set = db.relationship("LegoSet", backref="listings")