import pandas as pd
from pathlib import Path
from src.config.settings import output_dir_ffpi

_EXPECTED_COLS = ["full_date", "food_index", "meat_price", "dairy_price", "cereals_price", "oils_price", "sugar_price"]

def _find_data_start(df: pd.DataFrame) -> int:
   """Cherche la première ligne où la colonne 0 ressemble à une date (YYYY-MM ou similaire)."""
   for i, val in enumerate(df.iloc[:, 0]):
      if pd.notna(val):
         parsed = pd.to_datetime(val, errors="coerce")
         if pd.notna(parsed):
            return i
   raise ValueError(
      "FFPI : impossible de localiser le début des données "
      "(aucune valeur de date reconnue en colonne A). "
      "Le format du fichier source a probablement changé."
   )

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df = df.dropna(axis=1, how="all")
   df = df.dropna(axis=0, how="all")

   data_start = _find_data_start(df)
   df = df.iloc[data_start:, :7].reset_index(drop=True)
   df.columns = _EXPECTED_COLS

   df["full_date"] = pd.to_datetime(df["full_date"])
   value_cols = _EXPECTED_COLS[1:]
   df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce")
   return df

def run() -> pd.DataFrame:
   filepath = Path(output_dir_ffpi) / "ffpi_latest.csv"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée FFPI trouvée dans {filepath}")

   df = pd.read_csv(filepath, header=None)
   return clean(df)
