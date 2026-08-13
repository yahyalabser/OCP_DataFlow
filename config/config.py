from dotenv import load_dotenv
import os

load_dotenv()

class MissingEnvVar(Exception):
   """Levée uniquement quand une variable manquante est réellement utilisée."""
   pass

class _LazyEnv:
   """Accès aux variables d'env avec validation différée (au premier usage réel)."""
   def __init__(self):
     self._cache = {}

   def get(self, name, default=None, required=True):
      if name in self._cache:
         return self._cache[name]
      value = os.getenv(name, default)
      if required and not value:
         raise MissingEnvVar(
               f"Variable d'environnement manquante : {name}. "
               f"Vérifie ton fichier .env."
         )
      self._cache[name] = value
      return value

_env = _LazyEnv()

def get_api_key_news():
   return _env.get("API_KEY_NEWS")

def get_api_key_alpha():
   return _env.get("API_KEY_alpha")

def get_fao_credentials():
   return _env.get("FAO_USERNAME"), _env.get("FAO_PASSWORD")

def get_cognito_client_id():
   return _env.get("COGNITO_CLIENT_ID")

COGNITO_REGION = os.getenv("COGNITO_REGION", "eu-west-1")

def get_db_config():
   return {
      "user": _env.get("POSTGRES_USER"),
      "password": _env.get("POSTGRES_PASSWORD"),
      "dbname": _env.get("POSTGRES_DB"),
     "host": _env.get("POSTGRES_HOST", "localhost", required=False),
     "port": _env.get("POSTGRES_PORT", "5432", required=False),
   }