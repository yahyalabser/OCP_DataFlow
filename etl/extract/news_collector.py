import time
from logger_config import get_logger
from config.config import API_KEY_NEWS
from config.settings import URL_news, output_dir_news
from etl.extract.extract_base import BaseCollector
from datetime import datetime, timedelta, timezone

class NewsCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_news, output_dir_news, get_logger("news"))
      self.api_key = API_KEY_NEWS
      self.keywords = ['OCP Group OR "OCP Morocco"', "phosphate", "fertilizer", "agriculture AND fertilizer", 'Mosaic OR Nutrien OR Yara OR "CF Industries" OR "ICL Group"']

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

      payload = self._safe_json(response, context=keyword)
      if payload is None:
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
         all_news[keyw] = self.collect_keyword(keyw) or []
         time.sleep(1)
      self.save(all_news)

   def save(self, data: dict) -> None:
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
      self._save_dated_and_latest(self._save_json, data, "news", timestamp, "json")