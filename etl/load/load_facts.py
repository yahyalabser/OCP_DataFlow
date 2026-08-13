from logger_config import get_logger
from config.db_config import get_engine
from etl.load.db_writer import upsert

logger = get_logger("load_facts")

FACT_KEYS = {
   "FactStockPrices": ["symbol", "full_date"],
   "FactCropProduction": ["full_date", "country_code", "crop_code", "element_code"],
   "FactFoodPriceIndex": ["full_date"],
   "FactOCPFinancials": ["quarter_label"],
   "FactNews": ["url"],
   "BridgeArticleKeyword": ["url", "keyword"],
   "FactCommodityPrices": ["full_date", "commodity_name"],
}

def load_facts(transformed_data: dict) -> dict:
   results = {"success": [], "failed": []}

   for table_name, unique_cols in FACT_KEYS.items():
      df = transformed_data.get(table_name)
      if df is None:
         logger.warning(f"Pas de données pour la table de faits {table_name}")
         continue

      try:
         upsert(get_engine(), df, table_name, unique_cols)
         results["success"].append(table_name)
      except Exception as e:
         logger.error(f"Échec chargement fait {table_name} : {e}", exc_info=True)
         results["failed"].append(table_name)

   return results