import os
from logger_config import get_logger
from config.settings import URL_world_bank, output_dir_world_bank
from collectors.base_collector import BaseCollector

class WorldBankCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_world_bank, output_dir_world_bank, get_logger("world_bank"), 30)
      
   def collect(self) -> None:
      self.logger.info("Téléchargement...")

      response = self._request_with_retry()
      if response is None:
         return None
      
      self.save(response)
      self.logger.info("Téléchargement terminé.")
   
   def save(self, data) -> None:
      os.makedirs(self.output_dir, exist_ok=True)
      filename = f"{self.output_dir}/commodity_prices.xlsx"
      with open(filename, "wb") as f:
         f.write(data.content)
      self.logger.info(f"Sauvegardé dans {filename}")
