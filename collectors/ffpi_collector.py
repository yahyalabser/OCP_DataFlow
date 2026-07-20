import os
from datetime import datetime, timezone
from logger_config import get_logger
from config.settings import URL_ffpi, output_dir_ffpi
from collectors.base_collector import BaseCollector


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
      os.makedirs(self.output_dir, exist_ok=True)

      # Copie horodatée pour garder un historique des publications mensuelles
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m")
      filename = f"{self.output_dir}/ffpi_{timestamp}.csv"

      with open(filename, "wb") as f:
         f.write(data.content)

      # Copie "latest" écrasée à chaque run, pratique pour les étapes suivantes du pipeline
      latest_path = f"{self.output_dir}/ffpi_latest.csv"
      with open(latest_path, "wb") as f:
         f.write(data.content)

      self.logger.info(f"Sauvegardé dans {filename} (et {latest_path})")