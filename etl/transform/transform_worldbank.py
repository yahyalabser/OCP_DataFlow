import re
import pandas as pd
from pathlib import Path
from config.settings import output_dir_world_bank

_DATE_PATTERN = re.compile(r"^\d{4}M\d{2}$")

def _find_data_start(df: pd.DataFrame) -> int:
   """Localise l'index de la première ligne de données en cherchant le motif 'YYYYMxx'
   dans la première colonne, plutôt que de supposer une position fixe (ligne 6)."""
   for i, val in enumerate(df.iloc[:, 0]):
      if isinstance(val, str) and _DATE_PATTERN.match(val.strip()):
         return i
   raise ValueError(
      "World Bank : impossible de localiser le début des données "
      "(motif de date 'YYYYMxx' introuvable en colonne A). "
      "Le format du fichier source a probablement changé."
   )

def clean(df: pd.DataFrame) -> pd.DataFrame:
   data_start = _find_data_start(df)
   if data_start < 2:
      raise ValueError(
         f"World Bank : données détectées dès la ligne {data_start}, "
         f"pas assez de lignes au-dessus pour catégorie+unité — format inattendu."
      )

   category_row = df.iloc[data_start - 2]
   unit_row = df.iloc[data_start - 1]

   columns = []
   for cat, unit in zip(category_row, unit_row):
      cat = str(cat).strip() if pd.notna(cat) else ""
      unit = str(unit).strip() if pd.notna(unit) else ""
      columns.append(f"{cat} {unit}".strip())
   columns[0] = "full_date"

   dfc = df.iloc[data_start:].copy()
   dfc.columns = columns
   dfc = dfc.reset_index(drop=True)

   dfc["full_date"] = pd.to_datetime(dfc["full_date"].str.replace("M", "-"))
   return dfc

def transform(df: pd.DataFrame) -> dict:
   long_df = df.melt(id_vars=["full_date"], var_name="commodity_raw", value_name="price")
   long_df["price"] = pd.to_numeric(long_df["price"], errors="coerce")
   extracted = long_df["commodity_raw"].str.extract(r"^(.*?)\s*\(([^)]+)\)\s*$")
   long_df["commodity_name"] = extracted[0].str.strip()
   long_df["unit"] = extracted[1].str.strip()
   long_df = long_df.drop(columns=["commodity_raw"]).dropna(subset=["price"])

   dim_commodity = long_df[["commodity_name", "unit"]].drop_duplicates().reset_index(drop=True)
   dim_commodity["commodity_code"] = "Unknown"
   fact_commodity_prices = long_df[["full_date", "commodity_name", "price"]]

   return {"DimCommodity": dim_commodity, "FactCommodityPrices": fact_commodity_prices}

def run() -> pd.DataFrame:
   filepath = Path(output_dir_world_bank) / "commodity_prices_latest.xlsx"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée World Bank trouvée dans {filepath}")

   raw = pd.read_excel(filepath, sheet_name="Monthly Prices", header=None)

   df = clean(raw)
   df = transform(df)
   return df
