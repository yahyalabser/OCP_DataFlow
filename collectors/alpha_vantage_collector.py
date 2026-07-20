import os, json, time
from datetime import datetime, timezone
from logger_config import get_logger
from config.config import API_KEY_alpha
from config.settings import URL_alpha, output_dir_alpha
from collectors.base_collector import BaseCollector

class AlphaVantageCollector(BaseCollector):
   def __init__(self):
      super().__init__(URL_alpha, output_dir_alpha, get_logger("alphavantage"))
      self.api_key = API_KEY_alpha
      self.stocks = ["MOS", "NTR", "CF", "ICL", "YARIY"]

   def collect_symbol(self, symbol: str) -> dict | None:
      if not self.api_key:
         self.logger.critical("Clé API introuvable!")
         return None

      params = {
         "function": "TIME_SERIES_DAILY",
         "symbol": symbol,
         "outputsize": "compact",  # plan gratuit : 100 derniers jours max
         "apikey": self.api_key
      }

      response = self._request_with_retry(params=params)
      if response is None:
         return None

      try:
         data = response.json()
      except ValueError as e:
         self.logger.error(f"Réponse JSON invalide pour {symbol} : {e}")
         return None

      if "Note" in data or "Information" in data or "Error Message" in data:
         self.logger.error(f"Problème pour {symbol} : {data}")
         return None

      return data

   def collect(self) -> None:
      for symbol in self.stocks:
         data = self.collect_symbol(symbol)
         if data is not None:
            self.save(data, symbol)
         time.sleep(12)  # limite Alpha Vantage : 5 req/min sur plan gratuit

   def save(self, data, symbol) -> None:
      os.makedirs(self.output_dir, exist_ok=True)

      # Copie horodatée : accumule l'historique jour après jour
      # (contourne la limite outputsize=compact en construisant
      # une série longue via des runs quotidiens successifs)
      timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
      dated_filename = f"{self.output_dir}/{symbol}_{timestamp}.json"
      with open(dated_filename, "w") as f:
         json.dump(data, f, indent=2)

      # Copie "latest" écrasée à chaque run, pratique pour l'étape suivante du pipeline
      latest_filename = f"{self.output_dir}/{symbol}_latest.json"
      with open(latest_filename, "w") as f:
         json.dump(data, f, indent=2)

      self.logger.info(f"Sauvegardé {symbol} ({dated_filename} et {latest_filename})")