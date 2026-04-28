import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class Config:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASS')}@"
        f"{os.getenv('DB_HOST')}:5432/"
        f"{os.getenv('DB_NAME')}?client_encoding=utf8"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
