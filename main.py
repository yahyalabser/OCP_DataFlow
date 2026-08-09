from logger_config import get_logger

from extract.alpha_vantage_collector import AlphaVantageCollector
from extract.world_bank_collector import WorldBankCollector
from extract.ocp_financials import OCPFinancialsCollector
from extract.ffpi_collector import FFPICollector
from extract.news_collector import NewsCollector
from extract.fao_collector import FAOCollector

from transform import (
   transform_alpha,
   transform_worldbank,
   transform_fao,
   transform_ffpi,
   transform_news,
   transform_ocp,
)

# Associe chaque collector à son transformer et au(x) nom(s) de table produite(s)
PIPELINE = [
   ("AlphaVantageCollector", AlphaVantageCollector, transform_alpha, "stock_prices"),
   ("WorldBankCollector", WorldBankCollector, transform_worldbank, "commodity_prices"),
   ("FAOCollector", FAOCollector, transform_fao, "crop_production"),
   ("FFPICollector", FFPICollector, transform_ffpi, "food_price_index"),
   ("NewsCollector", NewsCollector, transform_news, None),
   ("OCPFinancialsCollector", OCPFinancialsCollector, transform_ocp, "ocp_financials"),
]

def run_pipeline(logger=None) -> dict:
   logger = logger or get_logger("run_pipeline")
   results = {"success": [], "failed": []}
   transformed_data = {}

   for name, CollectorClass, transformer, table_name in PIPELINE:
      try:
         logger.info(f"--- Démarrage : {name} ---")
         collector = CollectorClass()
         collector.collect()

         output = transformer.run()

         if isinstance(output, dict):
            transformed_data.update(output)
         else:
            transformed_data[table_name] = output

         results["success"].append(name)

      except Exception as e:
         logger.error(f"Échec {name} : {e}", exc_info=True)
         results["failed"].append(name)

   logger.info(f"Terminé. Succès : {results['success']} | Échecs : {results['failed']}")
   return {"results": results, "data": transformed_data}