import pandera.pandas as pa
from pandera import Column, Check

SCHEMAS = {
   "stock_prices": pa.DataFrameSchema({
      "symbol": Column(str, nullable=False),
      "date": Column("datetime64[ns]", nullable=False),
      "open": Column(float, Check.ge(0), nullable=False),
      "high": Column(float, Check.ge(0), nullable=False),
      "low": Column(float, Check.ge(0), nullable=False),
      "close": Column(float, Check.ge(0), nullable=False),
      "volume": Column(int, Check.ge(0), nullable=False),
   }, unique=["symbol", "date"]),
   "crop_production" : pa.DataFrameSchema({
      "country_code" : Column(int, Check.ge(0), nullable=False),
      "country_name" : Column(str, nullable=False),
      "element_code" : Column(int, Check.ge(0), nullable=False),
      "element_name" : Column(str, nullable=False),
      "crop_code" : Column(int, Check.ge(0), nullable=False),
      "crop_name" : Column(str, nullable=False),
      "Unit" : Column(str, nullable=False),
      "value" : Column(float, Check.ge(0), nullable=False),
      "full_date" : Column("datetime64[ns]", nullable=False),
   }, unique=["full_date", "country_code", "crop_code", "element_code"]),
   "food_price_index" : pa.DataFrameSchema({
      "full_date" : Column("datetime64[ns]", nullable=False),
      "food_index" : Column(float, Check.ge(0), nullable=False),
      "meat_price" : Column(float, Check.ge(0), nullable=False),
      "dairy_price" : Column(float, Check.ge(0), nullable=False) ,
      "cereals_price" : Column(float, Check.ge(0), nullable=False),
      "oils_price" : Column(float, Check.ge(0), nullable=False),
      "sugar_price" : Column(float, Check.ge(0), nullable=False) 
   }, unique=["full_date"]),
   "ocp_financials": pa.DataFrameSchema({
      "quarter_label": Column(str, nullable=False),
      "revenue": Column(float, Check.ge(0), nullable=False),
      "ebitda": Column(float, Check.ge(0), nullable=False),
      "ebitda_margin": Column(float, Check.in_range(0, 1), nullable=True),
      "net_income": Column(float, nullable=False),
      "full_date" : Column("datetime64[ns]", nullable=False)
   }, unique=["quarter_label"]),
   "news": pa.DataFrameSchema({
      "date": Column("datetime64[ns]", nullable=False),
      "source_name": Column(str, nullable=False),
      "url": Column(str, nullable=False),
      "title": Column(str, nullable=False),
      "author": Column(str, nullable=False),
      "content": Column(str, nullable=False),
   }, unique=["url"]),
   "bridge": pa.DataFrameSchema({
      "url": Column(str, nullable=False),
      "keyword": Column(str, nullable=False),
   }, unique=["url", "keyword"]),
   "Commodity": pa.DataFrameSchema({
      "commodity_name": Column(str, nullable=False),
      "unit": Column(str, nullable=False),
   }, unique=["commodity_name"]),
   "Commodity Prices": pa.DataFrameSchema({
      "full_date": Column("datetime64[ns]", nullable=False),
      "commodity_name": Column(str, nullable=False),
      "price": Column(float, Check.ge(0), nullable=True),
   }, unique=["full_date", "commodity_name"])
}

def validate(table_name: str, df):
   schema = SCHEMAS.get(table_name)
   if schema is None:
      raise ValueError(f"Aucun schéma trouvé pour : {table_name}")
   return schema.validate(df, lazy=True)