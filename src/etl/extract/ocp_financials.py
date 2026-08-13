import os, json
from logger_config import get_logger
from src.config.settings import config_path_ocpfinancials, output_dir_ocpfinancials
from src.etl.extract.extract_base import BaseCollector

class OCPFinancialsCollector(BaseCollector):

   def __init__(self, config_path: str = config_path_ocpfinancials):
      super().__init__("", output_dir_ocpfinancials, get_logger("ocp_financials"))
      self.config_path = config_path
      self.source = "OCP Group communiqué"
      self.REQUIRED_FIELDS = ["quarter", "revenue", "ebitda", "net_income", "published_at"]

   def _load_config(self) -> list[dict] | None:
      if not os.path.exists(self.config_path):
         self.logger.critical(f"Fichier de config introuvable : {self.config_path}")
         return None

      with open(self.config_path, "r", encoding="utf-8") as f:
         try:
            data = json.load(f)
         except json.JSONDecodeError as e:
            self.logger.error(f"Config JSON invalide : {e}")
            return None

      if not isinstance(data, list):
         self.logger.error("Le fichier de config doit contenir une liste de trimestres")
         return None

      return data

   def _validate_entry(self, entry: dict) -> bool:
      if not isinstance(entry, dict):
         self.logger.warning(f"Entrée ignorée, format invalide (attendu un objet JSON) : {entry}")
         return False

      missing = [f for f in self.REQUIRED_FIELDS if f not in entry or entry[f] in (None, "")]
      if missing:
         self.logger.warning(f"Entrée ignorée, champs manquants {missing} : {entry}")
         return False

      # revenue et ebitda ne peuvent pas être négatifs
      for field in ("revenue", "ebitda"):
         if not isinstance(entry[field], (int, float)) or entry[field] < 0:
            self.logger.warning(f"Valeur invalide pour '{field}' dans {entry.get('quarter')} : {entry[field]}")
            return False

      # net_income peut être négatif (perte trimestrielle) — on vérifie juste le type
      if not isinstance(entry["net_income"], (int, float)):
         self.logger.warning(f"Valeur invalide pour 'net_income' dans {entry.get('quarter')} : {entry['net_income']}")
         return False

      return True

   def collect(self) -> None:
      raw_entries = self._load_config()
      if raw_entries is None:
         return None

      validated = []
      seen_quarters = set()

      for entry in raw_entries:
         if not self._validate_entry(entry):
            continue

         quarter = entry["quarter"]
         if quarter in seen_quarters:
            self.logger.warning(f"Doublon ignoré pour le trimestre {quarter}")
            continue
         seen_quarters.add(quarter)

         if "ebitda_margin" not in entry or entry["ebitda_margin"] in (None, ""):
            entry["ebitda_margin"] = round(entry["ebitda"] / entry["revenue"], 4) if entry["revenue"] else None

         entry.setdefault("source", self.source)
         validated.append(entry)
         self.logger.info(f"✔ Trimestre validé : {quarter}")

      if not validated:
         self.logger.error("Aucune donnée valide à sauvegarder")
         return None

      self.save(validated)

   def save(self, data: list[dict]) -> None:
      self._save_json(data, "ocp_financials.json")
      self.logger.info(f"Sauvegardé {len(data)} trimestre(s)")
