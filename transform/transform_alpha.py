import glob, os
import pandas as pd
from config.settings import output_dir_alpha
from .io_utils import load_json

def clean(df: pd.DataFrame) -> pd.DataFrame:
   df = df.dropna(subset=["open", "high", "low", "close"])
   df["date"] = pd.to_datetime(df["date"])
   return df

def run() -> pd.DataFrame:
   files = glob.glob(os.path.join(output_dir_alpha, "*_latest.json"))
   if not files:
      raise FileNotFoundError(f"Aucune donnée Alpha Vantage trouvée dans {output_dir_alpha}")

   all_rows = []
   for filepath in files:
      raw = load_json(filepath)
      symbol = raw["Meta Data"]["2. Symbol"]
      series = raw["Time Series (Daily)"]
      all_rows.extend({
         "symbol": symbol,
         "date": d,
         "open": float(v["1. open"]),
         "high": float(v["2. high"]),
         "low": float(v["3. low"]),
         "close": float(v["4. close"]),
         "volume": int(v["5. volume"]),
      } for d, v in series.items())

   df = pd.DataFrame(all_rows)
   return clean(df)

if __name__ == "__main__":
   result = run()
   print(result)