from abc import ABC, abstractmethod
from urllib.parse import urlsplit, urlunsplit
import requests, time, os, json

_SENSITIVE_PARAM_NAMES = {"apikey", "api_key", "key", "token", "authorization"}


def _sanitize_url(url: str) -> str:
   """Masque les query params sensibles (clés API, tokens) avant de logguer une URL."""
   try:
      parts = urlsplit(url)
      if not parts.query:
         return url
      redacted_pairs = []
      for pair in parts.query.split("&"):
         name = pair.split("=", 1)[0]
         if name.lower() in _SENSITIVE_PARAM_NAMES:
            redacted_pairs.append(f"{name}=***")
         else:
            redacted_pairs.append(pair)
      return urlunsplit(parts._replace(query="&".join(redacted_pairs)))
   except Exception:
      return "<url non affichable>"


class BaseCollector(ABC):
   def __init__(self, base_url: str, output_dir: str, logger, timeout: int = 15, max_retries: int = 3):
      self.base_url = base_url
      self.output_dir = output_dir
      self.logger = logger
      self.timeout = timeout
      self.max_retries = max_retries

   def _request_with_retry(self, url: str = None, **kwargs) -> requests.Response | None:
      url = url or self.base_url
      kwargs.setdefault("timeout", self.timeout)
      safe_url = _sanitize_url(url)

      for attempt in range(1, self.max_retries + 1):
         try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response

         except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout sur {safe_url} (tentative {attempt}/{self.max_retries})")

         except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status is not None and 400 <= status < 500:
               self.logger.error(f"Erreur client {status} sur {safe_url}, pas de retry")
               return None
            self.logger.warning(f"Erreur HTTP {status} sur {safe_url} (tentative {attempt}/{self.max_retries})")

         except requests.exceptions.RequestException:
            self.logger.warning(f"Erreur de connexion sur {safe_url} (tentative {attempt}/{self.max_retries})")

         if attempt < self.max_retries:
            wait = 2 ** attempt
            time.sleep(wait)

      self.logger.error(f"Échec après toutes les tentatives sur {safe_url}")
      return None

   def _safe_json(self, response: requests.Response, context: str = "") -> dict | list | None:
      try:
         return response.json()
      except ValueError as e:
         suffix = f" ({context})" if context else ""
         self.logger.error(f"Réponse JSON invalide{suffix} : {e}")
         return None

   def _resolve_path(self, filename: str) -> str:
      os.makedirs(self.output_dir, exist_ok=True)
      return f"{self.output_dir}/{filename}"

   def _save_json(self, data, filename: str) -> str:
      path = self._resolve_path(filename)
      with open(path, "w", encoding="utf-8") as f:
         json.dump(data, f, indent=2, ensure_ascii=False)
      self.logger.info(f"Sauvegardé dans {path}")
      return path

   def _save_bytes(self, content: bytes, filename: str) -> str:
      path = self._resolve_path(filename)
      with open(path, "wb") as f:
         f.write(content)
      self.logger.info(f"Sauvegardé dans {path}")
      return path

   def _save_dated_and_latest(self, save_fn, data, base_name: str, date_str: str, ext: str) -> None:
      save_fn(data, f"{base_name}_{date_str}.{ext}")
      save_fn(data, f"{base_name}_latest.{ext}")

   @abstractmethod
   def collect(self):
      pass

   @abstractmethod
   def save(self, data):
      pass