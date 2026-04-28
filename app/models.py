from app.extensions import db
from datetime import timezone, datetime

class TempSummaries(db.Model):
    __tablename__ = "temp_summaries"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.String(20))

    ebay_item_id = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(10), nullable=False)
    condition = db.Column(db.String)
    listing_type = db.Column(db.String(50))
    marketplace = db.Column(db.String)
    item_country = db.Column(db.String(2))
    item_url = db.Column(db.Text)
    affiliate_url = db.Column(db.Text)
    creation_date = db.Column(db.DateTime(timezone=True))
    first_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sold_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_updated = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))