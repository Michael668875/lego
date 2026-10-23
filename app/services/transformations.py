from app.extensions import db
from sqlalchemy import text
from app import create_app

app = create_app()


def create_overview():
    db.session.execute(text("TRUNCATE TABLE bd_overview_sets"))

    db.session.execute(text("""
        INSERT INTO bd_overview_sets (
            set_num,
            country,
            count,
            cheapest_listing_id,
            cheapest_price
        )
        WITH active_listings AS (
            SELECT
                id AS listing_id,
                set_num,
                country,
                price
            FROM listings
            WHERE
                set_num IS NOT NULL
                AND status = 'ACTIVE'
        ),
        overview AS (
            SELECT
                set_num,
                country,
                COUNT(*) AS listing_count
            FROM active_listings
            GROUP BY
                set_num,
                country
        ),
        ranked_listings AS (
            SELECT
                listing_id,
                set_num,
                country,
                price,
                ROW_NUMBER() OVER (
                    PARTITION BY set_num, country
                    ORDER BY price ASC NULLS LAST, listing_id ASC
                ) AS price_rank
            FROM active_listings
        )
        SELECT
            o.set_num,
            o.country,
            o.listing_count,
            r.listing_id,
            r.price
        FROM overview o
        JOIN ranked_listings r
            ON r.set_num = o.set_num
            AND r.country = o.country
            AND r.price_rank = 1
    """))

    db.session.commit()
    print("OvervieSets created.")

def create_top_theme():
    db.session.execute(text("TRUNCATE TABLE bd_top_theme"))

    db.session.execute(text("""
        INSERT INTO bd_top_theme (
            theme_id,
            theme_name,
            country,
            listing_count
        )
        WITH ranked_themes AS (
            SELECT
                t.id AS theme_id,
                t.name AS theme_name,
                l.country,
                COUNT(l.id) AS listing_count,
                ROW_NUMBER() OVER (
                    PARTITION BY l.country
                    ORDER BY COUNT(l.id) DESC, t.name ASC
                ) AS rank
            FROM themes t
            JOIN lego_sets ls
                ON ls.theme_id = t.id
            JOIN listings l
                ON l.set_num = ls.base_set_num
            WHERE l.status = 'ACTIVE'
            GROUP BY
                t.id,
                t.name,
                l.country
        )
        SELECT
            theme_id,
            theme_name,
            country,
            listing_count
        FROM ranked_themes
        WHERE rank = 1
    """))

    db.session.commit()
    print("Top Theme created.")


if __name__ == "__main__":
    with app.app_context():
     #   create_overview()
        create_top_theme()
