-- =============================================================================
-- 01_raw_load.sql                                         layer: raw (landing)
-- -----------------------------------------------------------------------------
-- Purpose : Land the three CMS Care Compare extracts exactly as published
--           (every column as text, names normalized to snake_case) plus the
--           repo's condition-parameter seed. Nothing is cleaned here, so any
--           later number can be traced back to the file CMS published.
-- Inputs  : {raw_dir}/hrrp_readmissions.csv                 CMS HRRP (FY2026 program,
--                                                            performance 2021-07-01..2024-06-30)
--           {raw_dir}/medicare_spending_per_beneficiary.csv  CMS MSPB-1 (CY2024)
--           {raw_dir}/hospital_general_information.csv       CMS Hospital General Information
--           {seed_dir}/condition_params.csv                  repo seed: condition labels and
--                                                            cost parameters (see docs/assumptions.md)
--           raw_dir / seed_dir are DuckDB variables. run.py sets them from
--           config.yaml (or CMS_RAW_DIR in .env). Defaults are used if unset.
-- Outputs : raw_hrrp, raw_mspb, raw_hospital_info, seed_condition_params
-- Run     : python -m src.sql_runner sql/01_raw_load.sql
--      or : duckdb data/warehouse.duckdb -f sql/01_raw_load.sql      (from repo root)
-- =============================================================================

SET VARIABLE raw_dir  = COALESCE(getvariable('raw_dir'),  '~/projects/data-projects/datasets/p4-cms-2025');
SET VARIABLE seed_dir = COALESCE(getvariable('seed_dir'), 'seeds');

CREATE OR REPLACE TABLE raw_hrrp AS
SELECT *
FROM read_csv(getvariable('raw_dir') || '/hrrp_readmissions.csv',
              header = true, all_varchar = true, normalize_names = true);

CREATE OR REPLACE TABLE raw_mspb AS
SELECT *
FROM read_csv(getvariable('raw_dir') || '/medicare_spending_per_beneficiary.csv',
              header = true, all_varchar = true, normalize_names = true);

CREATE OR REPLACE TABLE raw_hospital_info AS
SELECT *
FROM read_csv(getvariable('raw_dir') || '/hospital_general_information.csv',
              header = true, all_varchar = true, normalize_names = true);

CREATE OR REPLACE TABLE seed_condition_params AS
SELECT *
FROM read_csv(getvariable('seed_dir') || '/condition_params.csv', header = true);

-- Row counts as landed (compared with the published counts in 09_dq_checks.sql)
SELECT 'raw_hrrp' AS table_name, count(*) AS n_rows FROM raw_hrrp
UNION ALL SELECT 'raw_mspb', count(*) FROM raw_mspb
UNION ALL SELECT 'raw_hospital_info', count(*) FROM raw_hospital_info
UNION ALL SELECT 'seed_condition_params', count(*) FROM seed_condition_params;
