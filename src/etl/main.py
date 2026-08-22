import time
import pandera.pandas as pa
from src.etl.quality_checks import validate
from src.logger_config import get_logger
from src.etl.monitoring import log_run

from src.etl.extract.alpha_vantage_collector import AlphaVantageCollector
from src.etl.extract.world_bank_collector import WorldBankCollector
from src.etl.extract.ocp_financials import OCPFinancialsCollector
from src.etl.extract.ffpi_collector import FFPICollector
from src.etl.extract.news_collector import NewsCollector
from src.etl.extract.fao_collector import FAOCollector
from src.etl.load.load_dimensions import load_dimensions
from src.etl.load.load_facts import load_facts

from src.etl.transform import (
   transform_worldbank
)
from src.etl.transform import transform_alpha, transform_fao, transform_ffpi, transform_news, transform_ocp

PIPELINE = [
   ("AlphaVantageCollector", AlphaVantageCollector, transform_alpha, None),
   ("WorldBankCollector", WorldBankCollector, transform_worldbank, None),
   ("FAOCollector", FAOCollector, transform_fao, None),
   ("FFPICollector", FFPICollector, transform_ffpi, "FactFoodPriceIndex"),
   ("NewsCollector", NewsCollector, transform_news, None),
   ("OCPFinancialsCollector", OCPFinancialsCollector, transform_ocp, "FactOCPFinancials"),
]


def _run_source(name, CollectorClass, transformer, table_name, transformed_data, logger) -> str:
   """Exécute collect -> transform -> validate pour une source.
   Retourne "success", "partial" (au moins une table exclue) ou "failed".
   Un seul appel à log_run par source, à la toute fin, avec le statut définitif
   (SUCCESS / PARTIAL / FAILED) et la durée réellement écoulée."""

   start = time.time()

   # --- Étape 1 : collecte ---
   try:
      collector = CollectorClass()
      collector.collect()
   except Exception as e:
      logger.error(f"[{name}] Échec à l'étape 'collect' : {e}", exc_info=True)
      log_run(name, 0, 0, time.time() - start, "FAILED", str(e))
      return "failed"

   # --- Étape 2 : transformation ---
   try:
      output = transformer.run()
   except FileNotFoundError as e:
      logger.error(f"[{name}] Échec à l'étape 'transform' (fichier source introuvable) : {e}", exc_info=True)
      log_run(name, 0, 0, time.time() - start, "FAILED", str(e))
      return "failed"
   except Exception as e:
      logger.error(f"[{name}] Échec à l'étape 'transform' : {e}", exc_info=True)
      log_run(name, 0, 0, time.time() - start, "FAILED", str(e))
      return "failed"

   # --- Étape 3 : validation ---
   tables = output if isinstance(output, dict) else {table_name: output}

   validated_tables = []
   failed_tables = []
   error_messages = []
   rows_extracted = sum(len(df) for df in tables.values())
   rows_loaded = 0

   for key, df in tables.items():
      try:
         validated = validate(key, df)
         transformed_data[key] = validated
         validated_tables.append(key)
         rows_loaded += len(validated)
      except pa.errors.SchemaErrors as e:
         logger.error(
            f"[{name}] Échec de validation pandera pour la table '{key}' "
            f"({len(e.failure_cases)} ligne(s) en échec) : table exclue, "
            f"les autres tables de la source sont conservées.\n{e.failure_cases}",
            exc_info=True,
         )
         failed_tables.append(key)
         error_messages.append(f"{key}: {e}")
      except Exception as e:
         logger.error(
            f"[{name}] Échec à l'étape 'validate' pour la table '{key}' : {e} "
            f"(table exclue, les autres tables de la source sont conservées)",
            exc_info=True,
         )
         failed_tables.append(key)
         error_messages.append(f"{key}: {e}")

   duration = time.time() - start

   if failed_tables and not validated_tables:
      log_run(name, rows_extracted, 0, duration, "FAILED", " | ".join(error_messages))
      return "failed"

   if failed_tables:
      logger.warning(
         f"[{name}] Terminé partiellement : {', '.join(validated_tables)} validée(s), "
         f"{', '.join(failed_tables)} exclue(s)"
      )
      log_run(name, rows_extracted, rows_loaded, duration, "PARTIAL", " | ".join(error_messages))
      return "partial"

   logger.info(f"[{name}] Terminé avec succès ({', '.join(validated_tables)})")
   log_run(name, rows_extracted, rows_loaded, duration, "SUCCESS")
   return "success"


def run_pipeline(logger=None) -> dict:
   logger = logger or get_logger("run_pipeline")
   results = {"success": [], "partial": [], "failed": []}
   transformed_data = {}

   for name, CollectorClass, transformer, table_name in PIPELINE:
      logger.info(f"--- Démarrage : {name} ---")

      status = _run_source(name, CollectorClass, transformer, table_name, transformed_data, logger)
      results[status].append(name)

   dim_results = load_dimensions(transformed_data)
   fact_results = load_facts(transformed_data)

   logger.info(
      f"Terminé. Succès : {results['success']} | "
      f"Partiels : {results['partial']} | Échecs : {results['failed']}"
   )
   logger.info(f"Dimensions -> Succès : {dim_results['success']} | Échecs : {dim_results['failed']}")
   logger.info(f"Faits -> Succès : {fact_results['success']} | Échecs : {fact_results['failed']}")

   return {
      "results": results,
      "data": transformed_data,
      "dim_results": dim_results,
      "fact_results": fact_results,
   }