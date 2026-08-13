import pandas as pd
from sqlalchemy import Table, MetaData
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from logger_config import get_logger

logger = get_logger("db_writer")

_metadata = MetaData()
_table_cache: dict[str, Table] = {}


def _get_table(engine: Engine, table_name: str) -> Table:
   """Récupère la Table réfléchie depuis le cache, ou la charge et la met en cache."""
   if table_name not in _table_cache:
      _table_cache[table_name] = Table(table_name, _metadata, autoload_with=engine)
   return _table_cache[table_name]


def upsert(engine: Engine, df: pd.DataFrame, table_name: str, unique_cols: list[str], protected_cols: list[str] | None = None) -> None:
   if df.empty:
      logger.warning(f"Aucune donnée à charger pour {table_name}")
      return

   protected_cols = set(protected_cols or [])
   table = _get_table(engine, table_name)
   records = df.to_dict(orient="records")

   with engine.begin() as conn:
      stmt = insert(table).values(records)
      pk_cols = {c.name for c in table.primary_key.columns}
      update_cols = {
         c.name: c for c in stmt.excluded
         if c.name not in unique_cols
         and c.name not in pk_cols
         and c.name not in protected_cols
      }
      if update_cols:
         stmt = stmt.on_conflict_do_update(index_elements=unique_cols, set_=update_cols)
      else:
         stmt = stmt.on_conflict_do_nothing(index_elements=unique_cols)
      conn.execute(stmt)

   logger.info(f"{len(records)} ligne(s) upsertée(s) dans {table_name}")