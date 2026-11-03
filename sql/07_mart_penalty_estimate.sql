-- =============================================================================
-- 07_mart_penalty_estimate.sql                          layer: mart (base case)
-- -----------------------------------------------------------------------------
-- Purpose : Base-case estimate of each hospital's annual HRRP penalty, using the
--           CMS payment-adjustment formula (docs/02_metric_definitions.md):
--
--     reduction % = NM x sum over conditions of
--                   (condition payments / total payments) x max(ERR - threshold, 0)
--     capped at 3%. NM is CMS's neutrality modifier (0.9627 in FY2026), a single
--     national multiplier that keeps peer grouping budget neutral. Multiplying by
--     total payments gives the dollar penalty:
--     penalty $   = NM x sum over conditions of condition payments x max(ERR - threshold, 0)
--
--   condition payments (per year) = estimated eligible discharges per year x
--   average base operating DRG payment per discharge for that condition
--   (seed_condition_params: FY2026 heart-failure base payment x CMS's published
--   relative payment per case by condition). Total payments are not in the CMS files; they are
--   approximated as HRRP-condition payments / hrrp_payment_share, and are used
--   only to apply the 3% cap and to express the penalty as a percentage.
--
--   The same logic is implemented in src/penalty.py (used by the dashboard for
--   what-if scenarios); 09_dq_checks.sql and src/quality.py reconcile the two.
-- Grain   : mart_penalty_condition = facility_id x condition_code
--           mart_penalty_hospital  = facility_id
-- Inputs  : fct_hospital_condition, seed_condition_params
-- Outputs : mart_penalty_condition, mart_penalty_hospital
-- Params  : penalty_cap_pct (0.03), hrrp_payment_share (0.133), neutrality_modifier (0.9627)
-- Run     : python -m src.sql_runner sql/07_mart_penalty_estimate.sql
-- =============================================================================

SET VARIABLE penalty_cap_pct    = COALESCE(getvariable('penalty_cap_pct'), 0.03);
SET VARIABLE hrrp_payment_share = COALESCE(getvariable('hrrp_payment_share'), 0.133);
SET VARIABLE neutrality_modifier = COALESCE(getvariable('neutrality_modifier'), 0.9627);

CREATE OR REPLACE TABLE mart_penalty_condition AS
SELECT
    f.facility_id,
    f.condition_code,
    f.has_err,
    f.is_payment_eligible,
    f.err,
    f.penalty_threshold_err,
    f.excess_ratio_over_threshold,
    f.discharges_est_annual,
    s.base_payment_per_discharge,
    CASE WHEN f.has_err THEN f.discharges_est_annual * s.base_payment_per_discharge ELSE 0 END
                                                        AS condition_payments_annual,
    CASE WHEN f.has_err AND f.is_payment_eligible
         THEN getvariable('neutrality_modifier') * f.discharges_est_annual
              * s.base_payment_per_discharge * f.excess_ratio_over_threshold
         ELSE 0 END                                     AS penalty_contribution_uncapped
FROM fct_hospital_condition f
JOIN seed_condition_params s USING (condition_code);

CREATE OR REPLACE TABLE mart_penalty_hospital AS
WITH agg AS (
    SELECT
        facility_id,
        bool_or(is_payment_eligible)                    AS is_payment_eligible,
        sum(condition_payments_annual)                  AS hrrp_condition_payments_annual,
        sum(penalty_contribution_uncapped)              AS penalty_uncapped_annual,
        count(*) FILTER (WHERE penalty_contribution_uncapped > 0)
                                                        AS n_conditions_penalized
    FROM mart_penalty_condition
    GROUP BY facility_id
),
capped AS (
    SELECT
        *,
        hrrp_condition_payments_annual / getvariable('hrrp_payment_share')
                                                        AS est_total_base_payments_annual,
        getvariable('penalty_cap_pct') * hrrp_condition_payments_annual
            / getvariable('hrrp_payment_share')         AS penalty_cap_annual
    FROM agg
)
SELECT
    *,
    least(penalty_uncapped_annual, penalty_cap_annual)  AS penalty_est_annual,
    penalty_uncapped_annual > penalty_cap_annual        AS hits_cap,
    is_payment_eligible AND penalty_uncapped_annual > 0 AS is_penalized,
    least(penalty_uncapped_annual, penalty_cap_annual)
        / nullif(est_total_base_payments_annual, 0)     AS payment_reduction_pct
FROM capped;

-- Allocate the (possibly capped) hospital penalty back to conditions
CREATE OR REPLACE TABLE mart_penalty_condition AS
SELECT
    c.*,
    CASE WHEN h.penalty_uncapped_annual > 0
         THEN c.penalty_contribution_uncapped * h.penalty_est_annual / h.penalty_uncapped_annual
         ELSE 0 END                                     AS penalty_contribution_annual
FROM mart_penalty_condition c
JOIN mart_penalty_hospital h USING (facility_id);

SELECT count(*) FILTER (WHERE is_penalized)               AS n_hospitals_penalized,
       count(*) FILTER (WHERE hits_cap)                   AS n_hospitals_at_cap,
       round(sum(penalty_est_annual) / 1e6, 1)            AS total_penalty_musd,
       round(median(payment_reduction_pct) FILTER (WHERE is_penalized) * 100, 3)
                                                          AS median_reduction_pct
FROM mart_penalty_hospital;
