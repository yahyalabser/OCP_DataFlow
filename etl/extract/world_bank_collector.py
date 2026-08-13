from io import BytesIO
import pandas as pd
from logger_config import get_logger
from config.settings import URL_world_bank, output_dir_world_bank
from etl.extract.extract_base import BaseCollector
from datetime import datetime, timezone

class WorldBankCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_world_bank, output_dir_world_bank, get_logger("world_bank"), 30)

   def collect(self) -> None:
      self.logger.info("Téléchargement...")

      response = self._request_with_retry()
      if response is None:
         return None

      if not response.content or len(response.content) < 1000:
         self.logger.error("Réponse World Bank vide ou suspecte, abandon de la sauvegarde")
         return None

      content_type = response.headers.get("Content-Type", "")
      if "spreadsheet" not in content_type and "octet-stream" not in content_type:
         self.logger.warning(f"Content-Type inattendu : {content_type} — sauvegarde quand même, à vérifier")

      if not self._is_valid_excel(response.content):
         self.logger.error(
            "Fichier World Bank téléchargé illisible en tant qu'Excel — "
            "conservation de la dernière version valide, 'latest' non écrasé."
         )
         return None

      self.save(response)
      self.logger.info("Téléchargement terminé.")

   def _is_valid_excel(self, content: bytes) -> bool:
      try:
         pd.read_excel(BytesIO(content), sheet_name="Monthly Prices", header=None, nrows=10)
         return True
      except Exception as e:
         self.logger.error(f"Validation Excel échouée : {e}")
         return False

   def save(self, data) -> None:
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
      self._save_dated_and_latest(self._save_bytes, data.content, "commodity_prices", timestamp, "xlsx")