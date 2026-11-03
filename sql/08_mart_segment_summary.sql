-- =============================================================================
-- 08_mart_segment_summary.sql                                   layer: mart
-- -----------------------------------------------------------------------------
-- Purpose : "Where do excess readmissions and penalties concentrate?" One long
--           table of segment statistics (by condition, region, state,
--           ownership, size, star rating, spending band, emergency services),
--           used by the National Picture page and the report.
--           Universe: payment-eligible hospitals (excludes Maryland and
--           hospitals no longer listed by CMS).
--           mean_err_ci_* is a normal-approximation 95% interval for the
--           segment mean; segments with fewer than 30 results are flagged.
-- Grain   : segment_dimension x segment_value x condition_code ('ALL' = all six)
-- Inputs  : fct_hospital_condition, dim_hospital, mart_penalty_condition,
--           mart_penalty_hospital
-- Outputs : mart_segment_summary
-- Run     : python -m src.sql_runner sql/08_mart_segment_summary.sql
-- =============================================================================

CREATE OR REPLACE TABLE mart_segment_summary AS
WITH seg AS (
    UNPIVOT (
        SELECT
            facility_id,
            'All hospitals'                     AS "National",
            census_region                       AS "Census region",
            state                               AS "State",
            ownership_group                     AS "Ownership",
            size_band                           AS "Size",
            star_rating_label                   AS "Star rating",
            mspb_band                           AS "Spending (MSPB)",
            emergency_services_label            AS "Emergency services"
        FROM dim_hospital
        WHERE is_payment_eligible
    )
    ON "National", "Census region", "State", "Ownership", "Size", "Star rating",
       "Spending (MSPB)", "Emergency services"
    INTO NAME segment_dimension VALUE segment_value
),
hc AS (
    SELECT f.*, p.penalty_contribution_annual, ph.is_penalized
    FROM fct_hospital_condition f
    JOIN mart_penalty_condition p USING (facility_id, condition_code)
    JOIN mart_penalty_hospital ph USING (facility_id)
    WHERE f.has_err AND f.is_payment_eligible
),
by_condition AS (
    SELECT
        s.segment_dimension, s.segment_value, hc.condition_code,
        count(DISTINCT hc.facility_id)                      AS n_hospitals,
        count(*)                                            AS n_results,
        avg(hc.err)                                         AS mean_err,
        median(hc.err)                                      AS median_err,
        stddev_samp(hc.err)                                 AS sd_err,
        avg(hc.is_above_threshold::INT)                     AS share_above_threshold,
        count(DISTINCT hc.facility_id) FILTER (WHERE hc.is_penalized)
                                                            AS n_hospitals_penalized,
        sum(hc.discharges_est_annual)                       AS discharges_annual,
        sum(hc.excess_readmissions_annual_pos)              AS excess_readmissions_annual_pos,
        sum(hc.excess_readmissions_annual)                  AS excess_readmissions_annual_net,
        sum(hc.penalty_contribution_annual)                 AS penalty_annual
    FROM seg s
    JOIN hc USING (facility_id)
    GROUP BY GROUPING SETS ((s.segment_dimension, s.segment_value, hc.condition_code),
                            (s.segment_dimension, s.segment_value))
)
SELECT
    segment_dimension,
    segment_value,
    coalesce(condition_code, 'ALL')                                    AS condition_code,
    n_hospitals, n_results, mean_err, median_err, sd_err,
    mean_err - 1.96 * sd_err / sqrt(n_results)                         AS mean_err_ci_low,
    mean_err + 1.96 * sd_err / sqrt(n_results)                         AS mean_err_ci_high,
    n_results < 30                                                     AS small_sample_flag,
    share_above_threshold,
    n_hospitals_penalized,
    n_hospitals_penalized / n_hospitals                                AS share_hospitals_penalized,
    discharges_annual,
    excess_readmissions_annual_pos,
    excess_readmissions_annual_net,
    penalty_annual,
    penalty_annual / nullif(discharges_annual, 0)                      AS penalty_per_discharge
FROM by_condition;

SELECT segment_value, condition_code, n_hospitals, round(mean_err, 4) AS mean_err,
       round(excess_readmissions_annual_pos) AS excess_readm, round(penalty_annual / 1e6, 1) AS penalty_musd
FROM mart_segment_summary
WHERE segment_dimension = 'National'
ORDER BY condition_code;
