import pandas as pd
from config.settings import output_dir_fao
from .io_utils import load_json
from pathlib import Path

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df = df.dropna(subset=["Value"])
   df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
   df = df.dropna(subset=["Value"])
   df = df.drop(columns=["Domain Code", "Domain", "Note", "Flag", "Flag Description", "Year Code"])
   return df

def transform(df : pd.DataFrame) -> pd.DataFrame:
   df = df.rename(columns={
      "Area Code": "country_code",
      "Area" : "country_name",
      "Item Code": "crop_code",
      "Item" : "crop_name",
      "Element Code": "element_code",
      "Element" : "element_name",
      "Value": "value",
   })
   df["full_date"] = pd.to_datetime(df["Year"].astype(str) + "-01-01")
   df = df.drop(columns=["Year"])
   df["country_code"] = df["country_code"].astype("int64")
   df["element_code"] = df["element_code"].astype("int64")
   df["crop_code"] = df["crop_code"].astype("int64")

   cols = ["full_date", "country_code", "crop_code", "element_code"]

   df = df.drop_duplicates(subset=cols)
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
