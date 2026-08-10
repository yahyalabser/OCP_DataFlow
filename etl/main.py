import pandera.pandas as pa
from etl.quality_checks import validate
from logger_config import get_logger

from etl.extract.alpha_vantage_collector import AlphaVantageCollector
from etl.extract.world_bank_collector import WorldBankCollector
from etl.extract.ocp_financials import OCPFinancialsCollector
from etl.extract.ffpi_collector import FFPICollector
from etl.extract.news_collector import NewsCollector
from etl.extract.fao_collector import FAOCollector

from etl.transform import (
   transform_ocp,
   transform_alpha,
   transform_worldbank,
   transform_fao,
   transform_ffpi,
   transform_news
)

PIPELINE = [
   ("AlphaVantageCollector", AlphaVantageCollector, transform_alpha, "stock_prices"),
   ("WorldBankCollector", WorldBankCollector, transform_worldbank, None),
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
            for key, df in output.items():
               validated = validate(key, df)
               transformed_data[key] = validated
         else:
            validated = validate(table_name, output)
            transformed_data[table_name] = validated

         results["success"].append(name)

      except pa.errors.SchemaErrors as e:
         logger.error(f"Error pandera : {e}", exc_info=True)
         results["failed"].append(name)
      except Exception as e:
         logger.error(f"Échec {name} : {e}", exc_info=True)
         results["failed"].append(name)

   logger.info(f"Terminé. Succès : {results['success']} | Échecs : {results['failed']}")
   return {"results": results, "data": transformed_data}