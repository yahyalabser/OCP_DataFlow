from logger_config import get_logger
from config.settings import URL_world_bank, output_dir_world_bank
from extract.extract_base import BaseCollector

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
      
      self.save(response)
      self.logger.info("Téléchargement terminé.")
   
   def save(self, data) -> None:
      self._save_bytes(data.content, "commodity_prices.xlsx")
