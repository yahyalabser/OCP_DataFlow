import pandas as pd
from pathlib import Path
from src.config.settings import output_dir_ffpi

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df = df.dropna(axis=1, how="all")
   df = df.dropna(axis=0, how="all")
   df = df.iloc[:, :7]
   df.columns = ["full_date", "food_index", "meat_price", "dairy_price", "cereals_price", "oils_price", "sugar_price"]

   df["full_date"] = pd.to_datetime(df["full_date"])
   value_cols = ["food_index", "meat_price", "dairy_price", "cereals_price", "oils_price", "sugar_price"]
   df[value_cols] = df[value_cols].apply(pd.to_numeric, errors="coerce")
   return df

def run() -> pd.DataFrame:
   filepath = Path(output_dir_ffpi) / "ffpi_latest.csv"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée FFPI trouvée dans {filepath}")

   df = pd.read_csv(filepath, skiprows=4, header=None)
   return clean(df)
