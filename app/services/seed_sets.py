import csv

from app import create_app, db
from app.models import LegoSet


CSV_PATH = "sets.csv"


def get_base_set_num(set_num):
    """
    Convert:
        10210-1 -> 10210
        001-2   -> 001
    """
    return set_num.split("-")[0]


def seed_sets():

    app = create_app()

    with app.app_context():

        existing_sets = {
            row[0]
            for row in db.session.query(LegoSet.suffix_set_num).all()
        }

        batch = []
        added = 0

        with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:

            reader = csv.DictReader(csvfile)

            for row in reader:

                set_num = row["set_num"]

                if set_num in existing_sets:
                    continue

                lego_set = LegoSet(
                    suffix_set_num=set_num,
                    base_set_num=get_base_set_num(set_num),
                    name=row["name"],
                    year=int(row["year"]) if row["year"] else None,
                    theme_id=int(row["theme_id"]) if row["theme_id"] else None,
                    num_parts=int(row["num_parts"]) if row["num_parts"] else None,
                    img_url=row["img_url"],
                )

                batch.append(lego_set)
                existing_sets.add(set_num)
                added += 1

                if len(batch) >= 1000:
                    db.session.bulk_save_objects(batch)
                    db.session.commit()
                    batch.clear()

            if batch:
                db.session.bulk_save_objects(batch)
                db.session.commit()

        print(f"Finished seeding lego_sets table. Added {added} new sets.")


if __name__ == "__main__":
    seed_sets()