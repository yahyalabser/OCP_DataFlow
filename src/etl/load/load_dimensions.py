from src.config.db_config import get_engine
from logger_config import get_logger
from src.etl.load.db_writer import upsert
from src.etl.load.generate_dim_date import generate_dim_date

logger = get_logger("load_dimensions")

DIMENSION_KEYS = {
   "DimCommodity": ["commodity_name"],
   "DimKeyword" : ["keyword"],
   "DimNewsSource" : ["source_name"],
   "DimElement" : ["element_code"],
   "DimCrop" : ["crop_code"],
   "DimCountry" : ["country_code"],
   "DimCompany" : ["symbol"],
   "DimDate" : ["full_date"]
}

DIMENSION_PROTECTED_COLS = {
   "DimCompany": ["company_name", "sector"],
   "DimCommodity": ["commodity_code"],
}

def load_dimensions(transformed_data: dict) -> dict:
   results = {"success": [], "failed": []}

   transformed_data["DimDate"] = generate_dim_date()
   for table_name, unique_cols in DIMENSION_KEYS.items():
      df = transformed_data.get(table_name)
      if df is None:
         logger.warning(f"Pas de données pour la dimension {table_name}")
         continue

      try:
         upsert(get_engine(), df, table_name, unique_cols, protected_cols=DIMENSION_PROTECTED_COLS.get(table_name))
         results["success"].append(table_name)
      except Exception as e:
         logger.error(f"Échec chargement dimension {table_name} : {e}", exc_info=True)
         results["failed"].append(table_name)

   return results
