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

def transform(df : pd.DataFrame) -> dict:
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

   # --- Extraction des dimensions ---
   dim_country = df[["country_code", "country_name"]].drop_duplicates().reset_index(drop=True)
   dim_crop = df[["crop_code", "crop_name"]].drop_duplicates().reset_index(drop=True)

   dim_element = (
      df[["element_code", "element_name", "Unit"]]
      .drop_duplicates(subset=["element_code"])
      .reset_index(drop=True)
      .rename(columns={"Unit": "unit"})
   )

   # --- Table de faits allégée (sans les noms, juste les codes) ---
   fact_crop_production = df.drop(columns=["country_name", "crop_name", "element_name", "Unit"])
   fact_crop_production = fact_crop_production.drop_duplicates(
      subset=["full_date", "country_code", "crop_code", "element_code"]
   )
   return {
      "DimCountry": dim_country,
      "DimCrop": dim_crop,
      "DimElement": dim_element,
      "FactCropProduction": fact_crop_production,
   }

def run() -> dict:
   filepath = Path(output_dir_fao) / "crop_production.json"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée FAOSTAT trouvée dans {filepath}")

   raw = load_json(filepath)
   df = pd.DataFrame(raw)
   df = clean(df)
   df = transform(df)
   return df
