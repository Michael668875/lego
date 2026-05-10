from app.extensions import db
from sqlalchemy import text


from app import create_app

app = create_app()

def insert_listings():

    db.session.execute(text(r"""
        INSERT INTO listings (
            ebay_item_id,
            title,
            price,
            currency,
            marketplace,
            affiliate_url,
            status
        )
        SELECT
            ts.ebay_item_id,
            ts.title,
            ts.price,
            ts.currency,
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
    
with app.app_context():
    insert_listings()
