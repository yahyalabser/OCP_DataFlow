from datetime import datetime, timezone
from logger_config import get_logger
from src.config.settings import URL_ffpi, output_dir_ffpi
from src.etl.extract.extract_base import BaseCollector

class FFPICollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_ffpi, output_dir_ffpi, get_logger("ffpi"), timeout=30)

   def collect(self) -> None:
      self.logger.info("Téléchargement du FAO Food Price Index...")

      response = self._request_with_retry()
      if response is None:
         self.logger.error("Échec de la collecte FFPI")
         return None

      if not response.content or len(response.content) < 100:
         self.logger.error("Réponse FFPI vide ou suspecte, abandon de la sauvegarde")
         return None

      self.save(response)
      self.logger.info("Téléchargement FFPI terminé.")

   def save(self, data) -> None:
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m")
      self._save_dated_and_latest(self._save_bytes, data.content, "ffpi", timestamp, "csv")