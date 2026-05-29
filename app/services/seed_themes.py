import csv

from app import create_app, db
from app.models import Theme


CSV_PATH = "themes.csv"


def seed_themes():

    app = create_app()

    with app.app_context():

        with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:

            reader = csv.DictReader(csvfile)

            for row in reader:

                theme = Theme(
                    id=int(row["id"]),
                    name=row["name"],
                    parent_id=int(row["parent_id"]) if row["parent_id"] else None,
                )

                db.session.add(theme)

            db.session.commit()

        print("Finished seeding themes table.")


if __name__ == "__main__":
    seed_themes()