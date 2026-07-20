import os, json, time
from logger_config import get_logger
from config.config import API_KEY_NEWS
from config.settings import URL_news, output_dir_news
from collectors.base_collector import BaseCollector
from datetime import datetime, timedelta, timezone

class NewsCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_news, output_dir_news, get_logger("news"))
      self.api_key = API_KEY_NEWS
      self.keywords = ['"OCP Group"', '"OCP SA"', "phosphate", "fertilizer", "agriculture"]

   def collect_keyword(self, keyword: str, days_back: int = 1) -> list[dict] | None:
      if not self.api_key:
         self.logger.critical("Clé API introuvable!")
         return None

      safe_days_back = max(days_back, 2)
      from_date = (datetime.now(timezone.utc) - timedelta(days=safe_days_back)).strftime("%Y-%m-%d")

      param = {
         "q": keyword,
         "from": from_date,
         "pageSize": 20,
         "sortBy": "publishedAt",
         "language": "en",
         "apiKey": self.api_key
      }

      response = self._request_with_retry(params=param)
      if response is None:
         return None

      try:
         payload = response.json()
      except ValueError as e:
         self.logger.error(f"Réponse JSON invalide pour '{keyword}' : {e}")
         return None

      if payload.get("status") == "error":
         self.logger.error(f"Erreur API pour '{keyword}' : {payload.get('message')}")
         return None

      articles = payload.get("articles", [])
      self.logger.info(f"{len(articles)} articles récupérés pour '{keyword}'")
      return articles

   def collect(self) -> None:
      all_news = {}
      for keyw in self.keywords:
         all_news[keyw] = self.collect_keyword(keyw)
         time.sleep(1)
      self.save(all_news)

   def save(self, data: dict) -> None:
      os.makedirs(self.output_dir, exist_ok=True)
      filename = f"{self.output_dir}/news_{datetime.now(timezone.utc):%Y-%m-%d_%H%M%S}.json"
      with open(filename, "w") as f:
         json.dump(data, f, indent=2, ensure_ascii=False)
      self.logger.info(f"Sauvegardé dans {filename}")