import pandas as pd
from pathlib import Path
from config.settings import output_dir_world_bank

def clean(df : pd.DataFrame) -> pd.DataFrame:
   category_row = df.iloc[4]
   unit_row = df.iloc[5]
   
   columns = []
   for cat, unit in zip(category_row, unit_row):
      cat = str(cat).strip() if pd.notna(cat) else ""
      unit = str(unit).strip() if pd.notna(unit) else ""
      columns.append(f"{cat} {unit}".strip())
   columns[0] = "full_date"

   dfc = df.iloc[6:].copy()
   dfc.columns = columns
   dfc = dfc.reset_index(drop=True)

   dfc["full_date"] = pd.to_datetime(dfc["full_date"].str.replace("M", "-"))
   return dfc

def transform(df: pd.DataFrame) -> dict:
   long_df = df.melt(id_vars=["full_date"], var_name="commodity_raw", value_name="price")
   extracted = long_df["commodity_raw"].str.extract(r"^(.*?)\s*\(([^)]+)\)\s*$")
   long_df["commodity_name"] = extracted[0].str.strip()
   long_df["unit"] = extracted[1].str.strip()
   long_df = long_df.drop(columns=["commodity_raw"]).dropna(subset=["price"])

   dim_commodity = long_df[["commodity_name", "unit"]].drop_duplicates().reset_index(drop=True)
   fact_commodity_prices = long_df[["full_date", "commodity_name", "price"]]

   return {"Commodity": dim_commodity, "Commodity Prices": fact_commodity_prices}

def run() -> pd.DataFrame:
   filepath = Path(output_dir_world_bank) / "commodity_prices.xlsx"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée News trouvée dans {filepath}")

   raw = pd.read_excel(filepath, sheet_name="Monthly Prices", header=None)

   df = clean(raw)
   df = transform(df)
   return df

if __name__ == "__main__":
   result = run()
   print(result["Commodity"].head())
   print(result["Commodity Prices"].head())