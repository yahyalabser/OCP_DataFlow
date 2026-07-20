from collectors.alpha_vantage_collector import AlphaVantageCollector
from collectors.world_bank_collector import WorldBankCollector
from collectors.ocp_financials import OCPFinancialsCollector
from collectors.ffpi_collector import FFPICollector
from collectors.news_collector import NewsCollector
from collectors.fao_collector import FAOCollector
from logger_config import get_logger

logger = get_logger("run_collectors")

collectors = [
   # NewsCollector(),
   # AlphaVantageCollector(),
   # WorldBankCollector(),
   FAOCollector(),
   FFPICollector(),
   OCPFinancialsCollector()
]

results = {"success": [], "failed": []}

for collector in collectors:
   name = collector.__class__.__name__
   try:
      logger.info(f"--- Démarrage : {name} ---")
      collector.collect()
      results["success"].append(name)
   except Exception as e:
      logger.error(f"Échec du collector {name} : {e}", exc_info=True)
      results["failed"].append(name)

logger.info(f"Terminé. Succès : {results['success']} | Échecs : {results['failed']}")