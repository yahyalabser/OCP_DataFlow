import pandera.pandas as pa
from etl.quality_checks import validate
from logger_config import get_logger

from etl.extract.alpha_vantage_collector import AlphaVantageCollector
from etl.extract.world_bank_collector import WorldBankCollector
from etl.extract.ocp_financials import OCPFinancialsCollector
from etl.extract.ffpi_collector import FFPICollector
from etl.extract.news_collector import NewsCollector
from etl.extract.fao_collector import FAOCollector
from etl.load.load_dimensions import load_dimensions
from etl.load.load_facts import load_facts

from etl.transform import (
   transform_ocp,
   transform_alpha,
   transform_worldbank,
   transform_fao,
   transform_ffpi,
   transform_news
)

PIPELINE = [
   ("AlphaVantageCollector", AlphaVantageCollector, transform_alpha, None),
   ("WorldBankCollector", WorldBankCollector, transform_worldbank, None),
   ("FAOCollector", FAOCollector, transform_fao, None),
   ("FFPICollector", FFPICollector, transform_ffpi, "FactFoodPriceIndex"),
   ("NewsCollector", NewsCollector, transform_news, None),
   ("OCPFinancialsCollector", OCPFinancialsCollector, transform_ocp, "FactOCPFinancials"),
]


def _run_source(name, CollectorClass, transformer, table_name, transformed_data, logger) -> bool:
   """Exécute collect -> transform -> validate pour une source.
   Retourne True en cas de succès, False sinon. Chaque étape logue
   précisément où ça a échoué pour faciliter le debug en prod."""

   # --- Étape 1 : collecte ---
   try:
      collector = CollectorClass()
      collector.collect()
   except Exception as e:
      logger.error(f"[{name}] Échec à l'étape 'collect' : {e}", exc_info=True)
      return False

   # --- Étape 2 : transformation ---
   try:
      output = transformer.run()
   except FileNotFoundError as e:
      logger.error(f"[{name}] Échec à l'étape 'transform' (fichier source introuvable) : {e}", exc_info=True)
      return False
   except Exception as e:
      logger.error(f"[{name}] Échec à l'étape 'transform' : {e}", exc_info=True)
      return False

   # --- Étape 3 : validation ---
   # Chaque table est validée indépendamment : si une table échoue, elle est
   # exclue mais les autres tables valides de la même source sont quand même
   # conservées et chargées.
   tables = output if isinstance(output, dict) else {table_name: output}

   validated_tables = []
   failed_tables = []

   for key, df in tables.items():
      try:
         validated = validate(key, df)
         transformed_data[key] = validated
         validated_tables.append(key)
      except pa.errors.SchemaErrors as e:
         logger.error(
            f"[{name}] Échec de validation pandera pour la table '{key}' "
            f"({len(e.failure_cases)} ligne(s) en échec) : table exclue, "
            f"les autres tables de la source sont conservées.\n{e.failure_cases}",
            exc_info=True,
         )
         failed_tables.append(key)
      except Exception as e:
         logger.error(
            f"[{name}] Échec à l'étape 'validate' pour la table '{key}' : {e} "
            f"(table exclue, les autres tables de la source sont conservées)",
            exc_info=True,
         )
         failed_tables.append(key)

   if failed_tables and not validated_tables:
      # Aucune table de la source n'a pu être validée : la source est un échec complet.
      return False

   if failed_tables:
      logger.warning(
         f"[{name}] Terminé partiellement : {', '.join(validated_tables)} validée(s), "
         f"{', '.join(failed_tables)} exclue(s)"
      )
      # Succès partiel : on considère la source comme un succès puisqu'au moins
      # une table a pu être chargée, mais on le distingue dans les logs ci-dessus.
      return True

   logger.info(f"[{name}] Terminé avec succès ({', '.join(validated_tables)})")
   return True


def run_pipeline(logger=None) -> dict:
   logger = logger or get_logger("run_pipeline")
   results = {"success": [], "failed": []}
   transformed_data = {}

   for name, CollectorClass, transformer, table_name in PIPELINE:
      logger.info(f"--- Démarrage : {name} ---")

      ok = _run_source(name, CollectorClass, transformer, table_name, transformed_data, logger)

      if ok:
         results["success"].append(name)
      else:
         results["failed"].append(name)

   dim_results = load_dimensions(transformed_data)
   fact_results = load_facts(transformed_data)

   logger.info(f"Terminé. Succès : {results['success']} | Échecs : {results['failed']}")
   logger.info(f"Dimensions -> Succès : {dim_results['success']} | Échecs : {dim_results['failed']}")
   logger.info(f"Faits -> Succès : {fact_results['success']} | Échecs : {fact_results['failed']}")

   return {"results": results, "data": transformed_data}