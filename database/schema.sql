CREATE SCHEMA IF NOT EXISTS ocp_dataflow;

CREATE TABLE ocp_dataflow."DimDate" (
   date_key SERIAL PRIMARY KEY,
   full_date DATE NOT NULL UNIQUE,
   year INT NOT NULL,
   quarter INT NOT NULL,
   month INT NOT NULL,
   month_name VARCHAR NOT NULL,
   day INT NOT NULL,
   day_of_week INT NOT NULL,
   day_name VARCHAR NOT NULL,
   is_weekend BOOLEAN NOT NULL,
   week_of_year INT NOT NULL
);

CREATE TABLE ocp_dataflow."DimCompany" (
   company_key SERIAL PRIMARY KEY,
   symbol VARCHAR NOT NULL UNIQUE,
   company_name VARCHAR,
   sector VARCHAR
);


CREATE TABLE ocp_dataflow."FactStockPrices" (
   stock_price_key SERIAL PRIMARY KEY,
   full_date DATE NOT NULL REFERENCES ocp_dataflow."DimDate"(full_date),
   symbol VARCHAR NOT NULL REFERENCES ocp_dataflow."DimCompany"(symbol),
   open DECIMAL(12,4),
   high DECIMAL(12,4),
   low DECIMAL(12,4),
   close DECIMAL(12,4),
   volume BIGINT,
   CONSTRAINT uq_stockprices_grain UNIQUE (full_date, symbol)
);

CREATE TABLE ocp_dataflow."DimCountry" (
   country_key SERIAL PRIMARY KEY,
   country_code INT NOT NULL UNIQUE,
   country_name VARCHAR
);

CREATE TABLE ocp_dataflow."DimCrop" (
   crop_key SERIAL PRIMARY KEY,
   crop_code INT NOT NULL UNIQUE,
   crop_name VARCHAR  
);

CREATE TABLE ocp_dataflow."DimElement" (
   element_key SERIAL PRIMARY KEY,
   element_code INT NOT NULL UNIQUE,
   element_name VARCHAR,
   unit VARCHAR
);

CREATE TABLE ocp_dataflow."FactCropProduction" (
   crop_production_key SERIAL PRIMARY KEY,
   full_date DATE NOT NULL REFERENCES ocp_dataflow."DimDate"(full_date),
   country_code INT NOT NULL REFERENCES ocp_dataflow."DimCountry"(country_code),
   crop_code INT NOT NULL REFERENCES ocp_dataflow."DimCrop"(crop_code),
   element_code INT NOT NULL REFERENCES ocp_dataflow."DimElement"(element_code),
   value DECIMAL(18,2),
   CONSTRAINT uq_cropprod_grain UNIQUE (full_date, country_code, crop_code, element_code)
);


CREATE TABLE ocp_dataflow."FactFoodPriceIndex" (
   full_date DATE PRIMARY KEY REFERENCES ocp_dataflow."DimDate"(full_date),
   food_index DECIMAL(10,2),
   meat_price DECIMAL(10,2),
   dairy_price DECIMAL(10,2),
   cereals_price DECIMAL(10,2),
   oils_price DECIMAL(10,2),
   sugar_price DECIMAL(10,2)
);

CREATE TABLE ocp_dataflow."DimCommodity" (
   commodity_key SERIAL PRIMARY KEY,
   commodity_name VARCHAR NOT NULL UNIQUE,
   commodity_code VARCHAR,
   unit VARCHAR
);

CREATE TABLE ocp_dataflow."FactCommodityPrices" (
   commodity_price_key SERIAL PRIMARY KEY,
   commodity_name VARCHAR NOT NULL REFERENCES ocp_dataflow."DimCommodity"(commodity_name),
   full_date DATE NOT NULL REFERENCES ocp_dataflow."DimDate"(full_date),
   price DECIMAL(14,4),
   CONSTRAINT uq_commodityprices_grain UNIQUE (full_date, commodity_name)
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
   full_date DATE NOT NULL REFERENCES ocp_dataflow."DimDate"(full_date),
   source_name VARCHAR NOT NULL REFERENCES ocp_dataflow."DimNewsSource"(source_name),
   url VARCHAR NOT NULL UNIQUE,
   title VARCHAR,
   author VARCHAR,
   content TEXT,
   published_at TIMESTAMP NOT NULL,
   article_count INT DEFAULT 1
);

CREATE TABLE ocp_dataflow."BridgeArticleKeyword" (
   bridge_key SERIAL PRIMARY KEY,
   url VARCHAR NOT NULL REFERENCES ocp_dataflow."FactNews"(url),
   keyword VARCHAR NOT NULL REFERENCES ocp_dataflow."DimKeyword"(keyword),
   CONSTRAINT uq_bridge_grain UNIQUE (url, keyword)
);

CREATE TABLE ocp_dataflow."FactOCPFinancials" (
   ocp_financials_key SERIAL PRIMARY KEY,
   full_date DATE NOT NULL REFERENCES ocp_dataflow."DimDate"(full_date),
   quarter_label VARCHAR NOT NULL UNIQUE,
   revenue DECIMAL(18,2),
   ebitda DECIMAL(18,2),
   ebitda_margin DECIMAL(6,4),
   net_income DECIMAL(18,2)
);

CREATE TABLE ocp_dataflow."EtlRunLog" (
   run_id SERIAL PRIMARY KEY,
   run_datetime TIMESTAMP NOT NULL DEFAULT now(),
   source VARCHAR NOT NULL,
   rows_extracted INT,
   rows_loaded INT,
   duration_seconds DECIMAL(10,2),
   status VARCHAR NOT NULL CHECK (status IN ('SUCCESS', 'PARTIAL', 'FAILED')),
   error_message TEXT
);
