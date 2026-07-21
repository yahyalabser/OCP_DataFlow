from abc import ABC, abstractmethod
import requests, time

class BaseCollector(ABC):
   def __init__(self, base_url: str, output_dir: str, logger, timeout: int = 15, max_retries: int = 3):
      self.base_url = base_url
      self.output_dir = output_dir
      self.logger = logger
      self.timeout = timeout
      self.max_retries = max_retries

   def _request_with_retry(self, url: str = None, method: str = "GET", **kwargs) -> requests.Response | None:
      url = url or self.base_url
      kwargs.setdefault("timeout", self.timeout)

      for attempt in range(1, self.max_retries + 1):
         try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response

         except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout (tentative {attempt}/{self.max_retries})")
         except requests.exceptions.HTTPError as e:
            self.logger.warning(f"Erreur HTTP : {e}")
         except requests.exceptions.RequestException as e:
            self.logger.warning(f"Erreur de connexion : {e}")

         if attempt < self.max_retries:
            wait = 2 ** attempt
            time.sleep(wait)

      self.logger.error("Échec après toutes les tentatives")
      return None

   def _safe_json(self, response: requests.Response) -> dict | list | None:
      try:
         return response.json()
      except ValueError as e:
         self.logger.error(f"Réponse non-JSON reçue : {e}")
         return None

   @abstractmethod
   def collect(self):
      pass

   @abstractmethod
   def save(self):
      pass