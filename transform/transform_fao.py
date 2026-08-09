import pandas as pd
from config.settings import output_dir_fao
from .io_utils import load_json
from pathlib import Path

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df = df.dropna(subset=["Value"])
   df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
   df = df.dropna(subset=["Value"])
   return df

def transform(df : pd.DataFrame) -> pd.DataFrame:
   df = df.rename(columns={
      "Area Code": "country_code",
      "Item Code": "crop_code",
      "Element Code": "element_code",
      "Value": "value",
   })
   df["full_date"] = pd.to_datetime(df["Year"].astype(str) + "-01-01")
   return df

def run() -> pd.DataFrame:
   filepath = Path(output_dir_fao) / "crop_production.json"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée FAOSTAT trouvée dans {filepath}")

   raw = load_json(filepath)
   df = pd.DataFrame(raw)
   df = clean(df)
   df = transform(df)
   return df

if __name__ == "__main__":
   result = run()
   print(result)