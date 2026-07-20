import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_NEWS = os.getenv("API_KEY_NEWS")
API_KEY_alpha = os.getenv("API_KEY_alpha")
TOKEN_FAO = os.getenv("TOKEN_FAO")