import time
from datetime import datetime, timezone
from logger_config import get_logger
from config.config import get_api_key_alpha
from config.settings import URL_alpha, output_dir_alpha
from etl.extract.extract_base import BaseCollector

class AlphaVantageCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_alpha, output_dir_alpha, get_logger("alphavantage"))
      self.api_key = get_api_key_alpha()
      self.stocks = ["MOS", "NTR", "CF", "ICL", "YARIY"]

   def collect_symbol(self, symbol: str) -> dict | None:
      if not self.api_key:
         self.logger.critical("Clé API introuvable!")
         return None

      params = {
         "function": "TIME_SERIES_DAILY",
         "symbol": symbol,
         "outputsize": "compact",
         "apikey": self.api_key
      }

      response = self._request_with_retry(params=params)
      if response is None:
         return None

      data = self._safe_json(response, context=symbol)
      if data is None:
         return None

      if "Note" in data or "Information" in data or "Error Message" in data:
         self.logger.error(f"Problème pour {symbol} : {data}")
         return None

      return data

   def collect(self) -> None:
      for i, symbol in enumerate(self.stocks):
         data = self.collect_symbol(symbol)
         if data is not None:
            self.save(data, symbol)
         if i < len(self.stocks) - 1:
            time.sleep(12)

   def save(self, data, symbol) -> None:
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
      self._save_dated_and_latest(self._save_json, data, symbol, timestamp, "json")