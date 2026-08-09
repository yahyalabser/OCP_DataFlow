from dotenv import load_dotenv
import os

load_dotenv()

API_KEY_NEWS = os.getenv("API_KEY_NEWS")
API_KEY_alpha = os.getenv("API_KEY_alpha")
FAO_USERNAME = os.getenv("FAO_USERNAME")
FAO_PASSWORD = os.getenv("FAO_PASSWORD")

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
