-- =============================================================================
-- 03_stg_mspb.sql                                              layer: staging
-- -----------------------------------------------------------------------------
-- Purpose : Type-cast Medicare Spending Per Beneficiary (MSPB-1). The score is a
--           ratio: a hospital's risk-adjusted, price-standardized spending per
--           episode (3 days before admission to 30 days after discharge)
--           divided by the national median episode. 1.00 = national median.
--           "Not Available" scores become NULL with the footnote kept.
-- Grain   : one row per facility_id
-- Inputs  : raw_mspb (01_raw_load.sql)
-- Outputs : stg_mspb
-- Run     : python -m src.sql_runner sql/03_stg_mspb.sql
-- =============================================================================

CREATE OR REPLACE TABLE stg_mspb AS
SELECT
    facility_id,
    measure_id,
    TRY_CAST(score AS DOUBLE)                    AS mspb_ratio,
    NULLIF(trim(footnote), '')                   AS mspb_footnote,
    strptime(start_date, '%m/%d/%Y')::DATE       AS mspb_period_start,
    strptime(end_date,   '%m/%d/%Y')::DATE       AS mspb_period_end
FROM raw_mspb;

SELECT count(*) AS n_rows, count(mspb_ratio) AS n_with_score,
       round(median(mspb_ratio), 3) AS median_ratio
FROM stg_mspb;
