# RUN ONCE INITIALLY. THEN RUN ONLY IF URL STRUCTURE CHANGES OR LEGOSETS TABLE IS UPDATED

from pathlib import Path
from datetime import datetime, timezone

from app import create_app, db
from app.models import LegoSet, Theme
from flask import url_for

# =========================
# CONFIG
# =========================

COUNTRIES = ["us", "au", "de", "gb"]

SITEMAP_DIR = Path("app/static/sitemaps")
SITEMAP_DIR.mkdir(parents=True, exist_ok=True)

SETS_PER_SITEMAP = 10000

# Change this in production
BASE_URL = "http://127.0.0.1:5000"


# =========================
# HELPERS
# =========================

def write_urlset(filename, urls):

    with open(SITEMAP_DIR / filename, "w", encoding="utf-8") as f:

        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for url in urls:
            f.write("  <url>\n")
            f.write(f"    <loc>{url['loc']}</loc>\n")
            f.write(f"    <lastmod>{url['lastmod']}</lastmod>\n")
            f.write(f"    <changefreq>{url['changefreq']}</changefreq>\n")
            f.write(f"    <priority>{url['priority']}</priority>\n")
            f.write("  </url>\n")

        f.write("</urlset>\n")


# =========================
# STATIC PAGES
# =========================

def generate_static():

    today = datetime.now(timezone.utc).date().isoformat()

    urls = []

    for country in COUNTRIES:

        urls.extend([
            {
                "loc": f"{BASE_URL}/{country}/",
                "lastmod": today,
                "changefreq": "daily",
                "priority": "1.0",
            },
            {
                "loc": f"{BASE_URL}/{country}/overview",
                "lastmod": today,
                "changefreq": "weekly",
                "priority": "0.8",
            },
            {
                "loc": f"{BASE_URL}/{country}/best-deals",
                "lastmod": today,
                "changefreq": "daily",
                "priority": "0.9",
            },
        ])

    write_urlset("sitemap-static.xml", urls)


# =========================
# THEMES
# =========================

def generate_themes():

    today = datetime.now(timezone.utc).date().isoformat()

    themes = Theme.query.all()

    urls = []

    for country in COUNTRIES:
        for theme in themes:

            urls.append({
                "loc": f"{BASE_URL}/{country}/theme/{theme.id}",
                "lastmod": today,
                "changefreq": "weekly",
                "priority": "0.7",
            })

    write_urlset("sitemap-themes.xml", urls)


# =========================
# SETS (chunked)
# =========================

def generate_sets():

    today = datetime.now(timezone.utc).date().isoformat()

    sets = (
        db.session.query(LegoSet.base_set_num)
        .filter(LegoSet.base_set_num.isnot(None))
        .distinct()
        .all()
    )

    urls = []
    sitemap_num = 1

    for (base_set_num,) in sets:

        for country in COUNTRIES:

            urls.append({
                "loc": f"{BASE_URL}/{country}/set/{base_set_num}",
                "lastmod": today,
                "changefreq": "weekly",
                "priority": "0.6",
            })

        # chunk flush
        if len(urls) >= SETS_PER_SITEMAP * len(COUNTRIES):

            write_urlset(
                f"sitemap-sets-{sitemap_num}.xml",
                urls
            )

            sitemap_num += 1
            urls = []

    # final flush
    if urls:

        write_urlset(
            f"sitemap-sets-{sitemap_num}.xml",
            urls
        )

    return sitemap_num


# =========================
# SITEMAP INDEX
# =========================

def generate_index(num_set_maps):

    files = [
        "sitemap-static.xml",
        "sitemap-themes.xml",
    ]

    for i in range(1, num_set_maps + 1):
        files.append(f"sitemap-sets-{i}.xml")

    with open(SITEMAP_DIR / "sitemap.xml", "w", encoding="utf-8") as f:

        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for filename in files:

            f.write("  <sitemap>\n")
            f.write(f"    <loc>{BASE_URL}/static/sitemaps/{filename}</loc>\n")
            f.write("  </sitemap>\n")

        f.write("</sitemapindex>\n")


# =========================
# MAIN
# =========================

app = create_app()

with app.app_context():

    generate_static()
    generate_themes()

    num_set_maps = generate_sets()

    generate_index(num_set_maps)

    print("Sitemaps generated successfully.")