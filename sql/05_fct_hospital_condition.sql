-- =============================================================================
-- 05_fct_hospital_condition.sql                       layer: fact (hospital x condition)
-- -----------------------------------------------------------------------------
-- Purpose : The analysis-ready hospital x condition table. Adds three things the
--           raw file does not have:
--
--   1. Estimated discharges where CMS suppressed them. When a hospital had 1-10
--      readmissions CMS hides BOTH counts but still publishes the ERR. We know
--      the hidden discharge count is at least 25 (CMS needs 25 cases to publish
--      an ERR) and at most about 10 / predicted rate (otherwise there would
--      have been 11+ readmissions). Base case = midpoint of that range; the low
--      (25) and high (upper bound) cases are kept for sensitivity testing.
--
--   2. Excess readmissions = discharges x (predicted rate - expected rate).
--      This is the number of readmissions above what an average hospital
--      would have had with the same patients (negative = fewer than expected).
--
--   3. Distance from the penalty threshold. HRRP penalizes a condition when
--      ERR is above the median ERR of the hospital's peer group. Peer groups
--      (dual-eligible quintiles) are not in our data, so the national median
--      ERR per condition is used as the threshold (see docs/assumptions.md).
--
--   Payment-eligible hospitals: excludes Maryland (exempt from HRRP payment
--   reductions under its state all-payer model) and hospitals no longer listed
--   in Hospital General Information (closed / converted since the period).
-- Grain   : one row per facility_id x condition_code
-- Inputs  : stg_hrrp_readmissions, stg_hospital_info, seed_condition_params
-- Outputs : fct_hospital_condition
-- Params  : performance_years (default 3; the HRRP window is 36 months)
-- Run     : python -m src.sql_runner sql/05_fct_hospital_condition.sql
-- =============================================================================

SET VARIABLE performance_years = COALESCE(getvariable('performance_years'), 3);

CREATE OR REPLACE TABLE fct_hospital_condition AS
WITH base AS (
    SELECT
        h.*,
        s.condition_label,
        s.care_type,
        s.sort_order,
        (h.state <> 'MD' AND i.facility_id IS NOT NULL)          AS is_payment_eligible,
        CASE WHEN h.reporting_status = 'counts_suppressed'
             THEN greatest(25, floor(10.0 / (h.predicted_rate_pct / 100.0)))
        END                                                      AS discharges_upper_bound
    FROM stg_hrrp_readmissions h
    LEFT JOIN stg_hospital_info i USING (facility_id)
    LEFT JOIN seed_condition_params s USING (condition_code)
),
threshold AS (
    -- national median ERR per condition among payment-eligible hospitals
    SELECT condition_code, median(err) AS penalty_threshold_err
    FROM base
    WHERE has_err AND is_payment_eligible
    GROUP BY condition_code
),
est AS (
    SELECT
        b.*,
        t.penalty_threshold_err,
        CASE WHEN b.reporting_status = 'reported'          THEN b.discharges
             WHEN b.reporting_status = 'counts_suppressed' THEN round((25 + b.discharges_upper_bound) / 2.0)
        END::DOUBLE                                              AS discharges_est,
        CASE WHEN b.reporting_status = 'reported'          THEN b.discharges
             WHEN b.reporting_status = 'counts_suppressed' THEN 25
        END::DOUBLE                                              AS discharges_est_low,
        CASE WHEN b.reporting_status = 'reported'          THEN b.discharges
             WHEN b.reporting_status = 'counts_suppressed' THEN b.discharges_upper_bound
        END::DOUBLE                                              AS discharges_est_high,
        b.reporting_status = 'counts_suppressed'                 AS discharges_imputed
    FROM base b
    LEFT JOIN threshold t USING (condition_code)
)
SELECT
    facility_id, facility_name_hrrp, state, condition_code, condition_label, care_type,
    sort_order, measure_name, reporting_status, footnote, has_footnote_29, has_err,
    is_payment_eligible, period_start, period_end,
    err, predicted_rate_pct, expected_rate_pct, observed_rate_pct,
    discharges, readmissions, readmissions_suppressed,
    discharges_imputed, discharges_upper_bound,
    discharges_est, discharges_est_low, discharges_est_high,
    discharges_est / getvariable('performance_years')                       AS discharges_est_annual,
    -- excess readmissions over the 3-year window and per year (signed)
    discharges_est * (predicted_rate_pct - expected_rate_pct) / 100.0        AS excess_readmissions_3yr,
    discharges_est * (predicted_rate_pct - expected_rate_pct) / 100.0
        / getvariable('performance_years')                                   AS excess_readmissions_annual,
    greatest(discharges_est * (predicted_rate_pct - expected_rate_pct) / 100.0, 0)
        / getvariable('performance_years')                                   AS excess_readmissions_annual_pos,
    -- penalty threshold distance
    penalty_threshold_err,
    err - penalty_threshold_err                                              AS err_minus_threshold,
    coalesce(err > penalty_threshold_err, false)                             AS is_above_threshold,
    CASE WHEN has_err THEN greatest(err - penalty_threshold_err, 0) ELSE 0 END
                                                                             AS excess_ratio_over_threshold
FROM est;

SELECT condition_code, count(*) FILTER (WHERE has_err) AS n_with_err,
       round(any_value(penalty_threshold_err), 4) AS threshold_err,
       round(sum(excess_readmissions_annual_pos)) AS excess_readm_per_year
FROM fct_hospital_condition
GROUP BY ALL ORDER BY condition_code;
