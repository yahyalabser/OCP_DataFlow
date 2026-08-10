import pandas as pd
from pathlib import Path
from config.settings import output_dir_ocpfinancials
from .io_utils import load_json

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df = df.drop(columns=["source"])
   df = df.rename(columns={"published_at" : "full_date", "quarter" : "quarter_label"})
   df["revenue"] = df["revenue"].astype("float64")
   df["ebitda"] = df["ebitda"].astype("float64")
   df["net_income"] = df["net_income"].astype("float64")
   df["full_date"] = pd.to_datetime(df["full_date"])
   df = df.drop_duplicates(subset=["quarter_label"], keep="last")
   return df

def run() -> pd.DataFrame:
   filepath = Path(output_dir_ocpfinancials) / "ocp_financials.json"
   if not filepath.exists():
      raise FileNotFoundError(f"Aucune donnée OCP Financial trouvée dans {filepath}")

   raw = load_json(filepath)
   df = pd.DataFrame(raw)
   return clean(df)
