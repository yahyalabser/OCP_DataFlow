from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from src.config.config import get_db_config

_engine = None

def get_engine():
   """Crée l'engine au premier appel réel, pas à l'import du module."""
   global _engine
   if _engine is None:
      db = get_db_config() 
      database_url = URL.create(
         drivername="postgresql+psycopg2",
         username=db["user"],
         password=db["password"],
         host=db["host"],
         port=int(db["port"]),
         database=db["dbname"],
      )
      _engine = create_engine(
         database_url,
         connect_args={"options": "-csearch_path=ocp_dataflow"},
      )
   return _engine