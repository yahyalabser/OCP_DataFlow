import pandera.pandas as pa
from pandera import Column, Check

SCHEMAS = {
   "DimCompany" : pa.DataFrameSchema({
      "symbol": Column(str, nullable=False),
      "company_name": Column(str, nullable=False),
      "sector": Column(str, nullable=False),
   }, unique=["symbol"]),
   "FactStockPrices": pa.DataFrameSchema({
      "symbol": Column(str, nullable=False),
      "full_date": Column("datetime64[ns]", nullable=False),
      "open": Column(float, Check.ge(0), nullable=False),
      "high": Column(float, Check.ge(0), nullable=False),
      "low": Column(float, Check.ge(0), nullable=False),
      "close": Column(float, Check.ge(0), nullable=False),
      "volume": Column(int, Check.ge(0), nullable=False),
   }, unique=["symbol", "full_date"]),
   "FactCropProduction" : pa.DataFrameSchema({
      "full_date" : Column("datetime64[ns]", nullable=False),
      "country_code" : Column(int, Check.ge(0), nullable=False),
      "crop_code" : Column(int, Check.ge(0), nullable=False),
      "element_code" : Column(int, Check.ge(0), nullable=False),
      "value" : Column(float, Check.ge(0), nullable=False),
   }, unique=["full_date", "country_code", "crop_code", "element_code"]),
   "DimCountry" : pa.DataFrameSchema({
      "country_code" : Column(int, Check.ge(0), nullable=False),
      "country_name" : Column(str, nullable=False),
   }, unique=["country_code"]),
   "DimCrop" : pa.DataFrameSchema({
      "crop_code" : Column(int, Check.ge(0), nullable=False),
      "crop_name" : Column(str, nullable=False),
   }, unique=["crop_code"]),
   "DimElement" : pa.DataFrameSchema({
      "element_code" : Column(int, Check.ge(0), nullable=False),
      "element_name" : Column(str, nullable=False),
      "unit" : Column(str, nullable=False),
   }, unique=["element_code"]),
   "FactFoodPriceIndex" : pa.DataFrameSchema({
      "full_date" : Column("datetime64[ns]", nullable=False),
      "food_index" : Column(float, Check.ge(0), nullable=False),
      "meat_price" : Column(float, Check.ge(0), nullable=False),
      "dairy_price" : Column(float, Check.ge(0), nullable=False) ,
      "cereals_price" : Column(float, Check.ge(0), nullable=False),
      "oils_price" : Column(float, Check.ge(0), nullable=False),
      "sugar_price" : Column(float, Check.ge(0), nullable=False) 
   }, unique=["full_date"]),
   "FactOCPFinancials": pa.DataFrameSchema({
      "quarter_label": Column(str, nullable=False),
      "revenue": Column(float, Check.ge(0), nullable=False),
      "ebitda": Column(float, Check.ge(0), nullable=False),
      "ebitda_margin": Column(float, Check.in_range(0, 1), nullable=True),
      "net_income": Column(float, nullable=False),
      "full_date" : Column("datetime64[ns]", nullable=False)
   }, unique=["quarter_label"]),
   "DimNewsSource" : pa.DataFrameSchema({
      "source_name": Column(str, nullable=False),
   }, unique=["source_name"]),
   "DimKeyword" : pa.DataFrameSchema({
      "keyword": Column(str, nullable=False),
   }, unique=["keyword"]),
   "FactNews": pa.DataFrameSchema({
      "full_date": Column("datetime64[ns]", nullable=False),
      "source_name": Column(str, nullable=False),
      "url": Column(str, nullable=False),
      "title": Column(str, nullable=False),
      "author": Column(str, nullable=False),
      "content": Column(str, nullable=False),
      "published_at" : Column("datetime64[ns, UTC]", nullable=False)
   }, unique=["url"]),
   "BridgeArticleKeyword": pa.DataFrameSchema({
      "url": Column(str, nullable=False),
      "keyword": Column(str, nullable=False),
   }, unique=["url", "keyword"]),
   "DimCommodity": pa.DataFrameSchema({
      "commodity_code": Column(str, nullable=False),
      "commodity_name": Column(str, nullable=False),
      "unit": Column(str, nullable=False),
   }, unique=["commodity_name"]),
   "FactCommodityPrices": pa.DataFrameSchema({
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