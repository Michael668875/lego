import csv

from app import create_app, db
from app.models import Theme


CSV_PATH = "themes.csv"


def seed_themes():

    app = create_app()

    with app.app_context():

        existing_ids = {
            row[0]
            for row in db.session.query(Theme.id).all()
        }

        added = 0

        with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:

            reader = csv.DictReader(csvfile)

            for row in reader:

                theme_id = int(row["id"])

                if theme_id in existing_ids:
                    continue

                theme = Theme(
                    id=theme_id,
                    name=row["name"],
                    parent_id=int(row["parent_id"]) if row["parent_id"] else None,
                )

                db.session.add(theme)
                existing_ids.add(theme_id)
                added += 1

            db.session.commit()

        print(f"Finished seeding themes table. Added {added} new themes.")


if __name__ == "__main__":
    seed_themes()