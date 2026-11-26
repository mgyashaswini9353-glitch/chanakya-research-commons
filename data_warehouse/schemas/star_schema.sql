-- ==============================================================================
-- Chanakya Research Commons - Analytical Star Schema (DuckDB over Parquet)
-- Conforms to Dimensional Modelling (Kimball Star Schema) for F9 Analytics
-- ==============================================================================

-- ========================
-- DIMENSION TABLES
-- ========================

CREATE OR REPLACE TABLE dim_date AS
SELECT * FROM read_parquet('data/parquet/dim_date.parquet');

CREATE OR REPLACE TABLE dim_department AS
SELECT * FROM read_parquet('data/parquet/dim_department.parquet');

CREATE OR REPLACE TABLE dim_member AS
SELECT * FROM read_parquet('data/parquet/dim_member.parquet');

CREATE OR REPLACE TABLE dim_topic AS
SELECT * FROM read_parquet('data/parquet/dim_topic.parquet');

CREATE OR REPLACE TABLE dim_paper AS
SELECT * FROM read_parquet('data/parquet/dim_paper.parquet');

-- ========================
-- FACT TABLES
-- ========================

CREATE OR REPLACE TABLE fact_research_activity AS
SELECT * FROM read_parquet('data/parquet/fact_research_activity.parquet');

CREATE OR REPLACE TABLE fact_paper_saves AS
SELECT * FROM read_parquet('data/parquet/fact_paper_saves.parquet');

CREATE OR REPLACE TABLE fact_search_events AS
SELECT * FROM read_parquet('data/parquet/fact_search_events.parquet');

CREATE OR REPLACE TABLE fact_post_engagement AS
SELECT * FROM read_parquet('data/parquet/fact_post_engagement.parquet');
