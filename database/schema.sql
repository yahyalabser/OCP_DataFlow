CREATE SCHEMA IF NOT EXISTS ocp_dataflow;

CREATE TABLE ocp_dataflow."DimDate" (
   date_key SERIAL PRIMARY KEY,
   full_date DATE NOT NULL UNIQUE,
   day INT NOT NULL,
   month INT NOT NULL,
   quarter INT NOT NULL,
   year INT NOT NULL
);

CREATE TABLE ocp_dataflow."DimCompany" (
   company_key SERIAL PRIMARY KEY,
   symbol VARCHAR NOT NULL UNIQUE,
   company_name VARCHAR,
   sector VARCHAR
);


CREATE TABLE ocp_dataflow."FactStockPrices" (
   stock_price_key SERIAL PRIMARY KEY,
   date_key INT NOT NULL REFERENCES ocp_dataflow."DimDate"(date_key),
   company_key INT NOT NULL REFERENCES ocp_dataflow."DimCompany"(company_key),
   open DECIMAL(12,4),
   high DECIMAL(12,4),
   low DECIMAL(12,4),
   close DECIMAL(12,4),
   volume BIGINT,
   CONSTRAINT uq_stockprices_grain UNIQUE (date_key, company_key)
);

CREATE TABLE ocp_dataflow."DimCountry" (
   country_key SERIAL PRIMARY KEY,
   country_code VARCHAR NOT NULL UNIQUE,
   country_name VARCHAR
);

CREATE TABLE ocp_dataflow."DimCrop" (
   crop_key SERIAL PRIMARY KEY,
   crop_code VARCHAR NOT NULL UNIQUE,
   crop_name VARCHAR  
);

CREATE TABLE ocp_dataflow."DimElement" (
   element_key SERIAL PRIMARY KEY,
   element_code VARCHAR NOT NULL UNIQUE,
   element_name VARCHAR,
   unit VARCHAR
);

CREATE TABLE ocp_dataflow."FactCropProduction" (
   crop_production_key SERIAL PRIMARY KEY,
   date_key INT NOT NULL REFERENCES ocp_dataflow."DimDate"(date_key),
   country_key INT NOT NULL REFERENCES ocp_dataflow."DimCountry"(country_key),
   crop_key INT NOT NULL REFERENCES ocp_dataflow."DimCrop"(crop_key),
   element_key INT NOT NULL REFERENCES ocp_dataflow."DimElement"(element_key),
   value DECIMAL(18,2),
   CONSTRAINT uq_cropprod_grain UNIQUE (date_key, country_key, crop_key, element_key)
);


CREATE TABLE ocp_dataflow."FactFoodPriceIndex" (
   date_key INT PRIMARY KEY REFERENCES ocp_dataflow."DimDate"(date_key),
   food_index DECIMAL(10,2),
   meat_price DECIMAL(10,2),
   dairy_price DECIMAL(10,2),
   cereals_price DECIMAL(10,2),
   oils_price DECIMAL(10,2),
   sugar_price DECIMAL(10,2)
);

CREATE TABLE ocp_dataflow."DimCommodity" (
   commodity_key SERIAL PRIMARY KEY,
   commodity_code VARCHAR NOT NULL UNIQUE,
   commodity_name VARCHAR,
   unit VARCHAR
);

CREATE TABLE ocp_dataflow."FactCommodityPrices" (
   commodity_price_key SERIAL PRIMARY KEY,
   commodity_key INT NOT NULL REFERENCES ocp_dataflow."DimCommodity"(commodity_key),
   date_key INT NOT NULL REFERENCES ocp_dataflow."DimDate"(date_key),
   price DECIMAL(14,4),
   CONSTRAINT uq_commodityprices_grain UNIQUE (date_key, commodity_key)
);

CREATE TABLE ocp_dataflow."DimNewsSource" (
   source_key SERIAL PRIMARY KEY,
   source_name VARCHAR NOT NULL UNIQUE
);

CREATE TABLE ocp_dataflow."DimKeyword" (
   keyword_key SERIAL PRIMARY KEY,
   keyword VARCHAR NOT NULL UNIQUE
);

CREATE TABLE ocp_dataflow."FactNews" (
   news_key SERIAL PRIMARY KEY,
   date_key INT NOT NULL REFERENCES ocp_dataflow."DimDate"(date_key),
   source_key INT NOT NULL REFERENCES ocp_dataflow."DimNewsSource"(source_key),
   url VARCHAR NOT NULL UNIQUE,
   title VARCHAR,
   author VARCHAR,
   content TEXT,
   article_count INT DEFAULT 1
);

CREATE TABLE ocp_dataflow."BridgeArticleKeyword" (
   bridge_key SERIAL PRIMARY KEY,
   news_key INT NOT NULL REFERENCES ocp_dataflow."FactNews"(news_key),
   keyword_key INT NOT NULL REFERENCES ocp_dataflow."DimKeyword"(keyword_key),
   CONSTRAINT uq_bridge_grain UNIQUE (news_key, keyword_key)
);

CREATE TABLE ocp_dataflow."FactOCPFinancials" (
   ocp_financials_key SERIAL PRIMARY KEY,
   date_key INT NOT NULL REFERENCES ocp_dataflow."DimDate"(date_key),
   quarter_label VARCHAR NOT NULL UNIQUE,
   revenue DECIMAL(18,2),
   ebitda DECIMAL(18,2),
   ebitda_margin DECIMAL(6,4),
   net_income DECIMAL(18,2)
);