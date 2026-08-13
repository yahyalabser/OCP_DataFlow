import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta


def generate_dim_date(start="1960-01-01", end=None, years_ahead: int = 5) -> pd.DataFrame:
   """Génère la dimension date.

   Si `end` n'est pas fourni, la borne finale est calculée dynamiquement
   comme aujourd'hui + `years_ahead` années (par défaut 5 ans), pour éviter
   d'avoir une date en dur à surveiller/mettre à jour manuellement.
   """
   if end is None:
      end = date.today() + relativedelta(years=years_ahead)

   dates = pd.date_range(start=start, end=end, freq="D")
   df = pd.DataFrame({"full_date": dates})

   df["year"] = df["full_date"].dt.year
   df["quarter"] = df["full_date"].dt.quarter
   df["month"] = df["full_date"].dt.month
   df["month_name"] = df["full_date"].dt.month_name()
   df["day"] = df["full_date"].dt.day
   df["day_of_week"] = df["full_date"].dt.dayofweek
   df["day_name"] = df["full_date"].dt.day_name()
   df["is_weekend"] = df["day_of_week"].isin([5, 6])
   df["week_of_year"] = df["full_date"].dt.isocalendar().week

   return df