-- =============================================================================
-- 02_stg_hrrp_readmissions.sql                                 layer: staging
-- -----------------------------------------------------------------------------
-- Purpose : Type-cast the HRRP extract and label every row with WHY a value is
--           missing. CMS hides small numbers, and the reason a row is blank
--           decides how it can be used later:
--             reported          ERR, discharges and readmissions all published
--             counts_suppressed ERR published, but readmissions were 1-10 so CMS
--                               hid both readmissions and discharges ("Too Few
--                               to Report"); discharges are imputed in 05_
--             too_few_cases     footnote 1: fewer than 25 eligible discharges, no ERR
--             not_available     footnote 5: no result for this period
--             no_cases          footnote 7: no patients met the measure criteria
-- Grain   : one row per facility_id x condition_code (6 HRRP conditions)
-- Inputs  : raw_hrrp (01_raw_load.sql)
-- Outputs : stg_hrrp_readmissions
-- Run     : python -m src.sql_runner sql/02_stg_hrrp_readmissions.sql
-- =============================================================================

CREATE OR REPLACE TABLE stg_hrrp_readmissions AS
WITH typed AS (
    SELECT
        facility_id,
        trim(facility_name)                                         AS facility_name_hrrp,
        state,
        measure_name,
        replace(regexp_extract(measure_name, '^READM-30-(.+)-HRRP$', 1), '-', '_')
                                                                    AS condition_code,
        TRY_CAST(number_of_discharges       AS INTEGER)             AS discharges,
        TRY_CAST(excess_readmission_ratio   AS DOUBLE)              AS err,
        TRY_CAST(predicted_readmission_rate AS DOUBLE)              AS predicted_rate_pct,
        TRY_CAST(expected_readmission_rate  AS DOUBLE)              AS expected_rate_pct,
        TRY_CAST(number_of_readmissions     AS INTEGER)             AS readmissions,
        number_of_readmissions = 'Too Few to Report'                AS readmissions_suppressed,
        NULLIF(trim(footnote), '')                                  AS footnote,
        strptime(start_date, '%m/%d/%Y')::DATE                      AS period_start,
        strptime(end_date,   '%m/%d/%Y')::DATE                      AS period_end
    FROM raw_hrrp
)
SELECT
    *,
    CASE
        WHEN err IS NOT NULL AND discharges IS NOT NULL AND readmissions IS NOT NULL
            THEN 'reported'
        WHEN err IS NOT NULL AND discharges IS NULL AND readmissions_suppressed
            THEN 'counts_suppressed'
        WHEN err IS NULL AND footnote = '1' THEN 'too_few_cases'
        WHEN err IS NULL AND footnote = '5' THEN 'not_available'
        WHEN err IS NULL AND footnote = '7' THEN 'no_cases'
        ELSE 'other'
    END                                                             AS reporting_status,
    err IS NOT NULL                                                 AS has_err,
    coalesce(footnote = '29', false)                                AS has_footnote_29,
    CASE WHEN discharges > 0 AND readmissions IS NOT NULL
         THEN 100.0 * readmissions / discharges END                 AS observed_rate_pct
FROM typed;

SELECT reporting_status, count(*) AS n_rows
FROM stg_hrrp_readmissions
GROUP BY ALL
ORDER BY n_rows DESC;
