import time
from logger_config import get_logger
from config.config import get_api_key_news
from config.settings import URL_news, output_dir_news
from etl.extract.extract_base import BaseCollector
from etl.extract.state import get_last_success, set_last_success
from datetime import datetime, timedelta, timezone

class NewsCollector(BaseCollector):
   SOURCE_NAME = "news"
   MAX_DAYS_BACK = 30

   def __init__(self):
      super().__init__(URL_news, output_dir_news, get_logger("news"))
      self.api_key = get_api_key_news()
      self.keywords = ['OCP Group OR "OCP Morocco"', "phosphate", "fertilizer", "agriculture AND fertilizer", 'Mosaic OR Nutrien OR Yara OR "CF Industries" OR "ICL Group"']

   def _compute_days_back(self, floor: int = 2) -> int:
      last_ok = get_last_success(self.SOURCE_NAME)
      if last_ok is None:
         self.logger.warning(
            f"Aucun run réussi connu pour '{self.SOURCE_NAME}', "
            f"fenêtre max ({self.MAX_DAYS_BACK}j) utilisée par précaution."
         )
         return self.MAX_DAYS_BACK
      days_since = (datetime.now(timezone.utc) - last_ok).days
      days_back = min(max(days_since, floor), self.MAX_DAYS_BACK)
      if days_since > self.MAX_DAYS_BACK:
         self.logger.warning(
            f"Dernier run réussi il y a {days_since}j, plafonné à {self.MAX_DAYS_BACK}j "
            f"— des articles plus anciens peuvent être manqués."
         )
      return days_back

   def collect_keyword(self, keyword: str, days_back: int) -> list[dict] | None:
      if not self.api_key:
         self.logger.critical("Clé API introuvable!")
         return None

      from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")

      all_articles = []
      page = 1
      max_pages = 3

      while page <= max_pages:
         param = {
            "q": keyword,
            "from": from_date,
            "pageSize": 100,
            "page": page,
            "sortBy": "publishedAt",
            "language": "en",
            "apiKey": self.api_key
         }

         response = self._request_with_retry(params=param)
         if response is None:
            break

         payload = self._safe_json(response, context=keyword)
         if payload is None:
            break

         if payload.get("status") == "error":
            self.logger.error(f"Erreur API pour '{keyword}' : {payload.get('message')}")
            break

         articles = payload.get("articles", [])
         all_articles.extend(articles)

         total_results = payload.get("totalResults", 0)
         if len(all_articles) >= total_results or not articles:
            break
         page += 1
         time.sleep(1) 

      self.logger.info(f"{len(all_articles)} articles récupérés pour '{keyword}' ({page} page(s))")
      return all_articles or None

   def collect(self) -> None:
      days_back = self._compute_days_back()
      self.logger.info(f"Collecte news sur {days_back} jour(s) glissants")

      all_news = {}
      any_success = False
      for keyw in self.keywords:
         result = self.collect_keyword(keyw, days_back)
         all_news[keyw] = result or []
         if result is not None:
            any_success = True
         time.sleep(1)

      self.save(all_news)

      if any_success:
         set_last_success(self.SOURCE_NAME)
      else:
         self.logger.error("Aucun mot-clé n'a réussi, 'last_success' non mis à jour.")

   def save(self, data: dict) -> None:
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
      self._save_dated_and_latest(self._save_json, data, "news", timestamp, "json")