#!/usr/bin/env python3
import os
import sys
from app import create_app
from app.services.save_temp import save_temp_summaries
#from app.services.pipeline import run_pipeline, truncate_temp_tables
from app.services.fetch import get_paginated_summaries
#from app.services.parse import blacklist
from datetime import datetime
import traceback
import tempfile

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "main_fetch.log")
LOCK_FILE = os.path.join(tempfile.gettempdir(), "main_fetch.lock")


# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)


# -----------------------------
# Prevent overlapping runs
# -----------------------------
if os.path.exists(LOCK_FILE):
    print("Another main_fetch.py job is already running. Exiting.")
    sys.exit(0)

# Create lock file
with open(LOCK_FILE, "w") as f:
    f.write("")

# -----------------------------
# Main job
# -----------------------------
def main():
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Starting main_fetch.py job")
    app = create_app()
    try:
        with app.app_context():
            
            # Fetch summaries
            items = get_paginated_summaries()
            save_temp_summaries(items)
            print(f"Fetched and saved {len(items)} summaries")           

    except Exception:
        print("Error occurred in main_fetch.py:")
        traceback.print_exc()
    finally:
        # Remove lock file
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        print("Finished main_fetch.py job")

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    main()