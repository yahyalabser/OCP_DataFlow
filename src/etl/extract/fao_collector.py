import time
from logger_config import get_logger
from src.config.auth import TokenManager
from src.config.settings import URL_fao, output_dir_fao
from src.config.config import get_fao_credentials
from src.etl.extract.extract_base import BaseCollector

class FAOCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_fao, output_dir_fao, get_logger("fao"))
      FAO_USERNAME, FAO_PASSWORD = get_fao_credentials()
      self.token_manager = TokenManager(FAO_USERNAME, FAO_PASSWORD)
      self.areas = {
         "Morocco": 143,
         "Brazil": 21,
         "India": 100,
         "China": 41,
         "USA": 231,
         "Canada": 33,
         "France": 68,
         "Argentina": 9
      }

      self.items = {
         "Wheat": 15,
         "Maize": 56,
         "Rice": 27,
         "Soybeans": 236,
         "Barley": 44,
         "Rapeseed": 270,
         "Sunflower": 267
      }

      self.years = range(2020, 2025)
      self.element = 2510
      self.request_delay = 1

   def collect(self):
      try:
         self.token_manager.get_token()
      except RuntimeError as e:
         self.logger.critical(f"Impossible de démarrer la collecte FAO : {e}")
         return None

      all_data = []
      total = len(self.areas) * len(self.items) * len(self.years)
      count = 0

      for area_name, area_code in self.areas.items():
         for item_name, item_code in self.items.items():
            for year in self.years:
                  count += 1
                  params = {
                     "area": area_code,
                     "item": item_code,
                     "element": self.element,
                     "year": year
                  }

                  try:
                     token = self.token_manager.get_token()
                  except RuntimeError as e:
                     self.logger.error(f"Token expiré/invalide, arrêt de la collecte FAO : {e}")
                     self.save(all_data)
                     return None

                  headers = {"Authorization": f"Bearer {token}"}
                  response = self._request_with_retry(headers=headers, params=params)
                  if response is None:
                     self.logger.error(f"Échec ({count}/{total}) : {area_name} | {item_name} | {year}")
                     time.sleep(self.request_delay)
                     continue
                  
                  data = self._safe_json(response, context=f"{count}/{total} {area_name}|{item_name}|{year}")
                  if data is None:
                     time.sleep(self.request_delay)
                     continue

                  if "data" in data:
                     all_data.extend(data["data"])
                     self.logger.info(f"✔ ({count}/{total}) {area_name} | {item_name} | {year}")
                  else:
                     self.logger.info(f"Aucune donnée ({count}/{total}) : {area_name} | {item_name} | {year}")

                  time.sleep(self.request_delay)
      
      self.save(all_data)

   def save(self, data):
      self._save_json(data, "crop_production.json")
      self.logger.info(f"Nombre total d'enregistrements : {len(data)}")
