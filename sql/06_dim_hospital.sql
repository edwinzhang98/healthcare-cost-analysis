-- =============================================================================
-- 06_dim_hospital.sql                                   layer: dimension (hospital)
-- -----------------------------------------------------------------------------
-- Purpose : One row per hospital in the HRRP file with its attributes, join
--           flags and the segment labels used across the dashboard:
--             size_band  HRRP volume = eligible Medicare fee-for-service discharges
--                        for the six conditions over the 3-year window (bed counts
--                        are not in these files): Low volume < 400, Mid volume
--                        400-999, High volume >= 1,000 (about terciles). This is
--                        Medicare HRRP volume, not overall hospital size.
--             mspb_band  Medicare spending per episode vs national median
--             readmission_index  discharge-weighted average ERR across the
--                        hospital's reported conditions (1.00 = as expected)
-- Grain   : one row per facility_id (universe = hospitals in the HRRP file)
-- Inputs  : fct_hospital_condition, stg_hospital_info, stg_mspb
-- Outputs : dim_hospital
-- Run     : python -m src.sql_runner sql/06_dim_hospital.sql
-- =============================================================================

CREATE OR REPLACE TABLE dim_hospital AS
WITH hrrp AS (
    SELECT
        facility_id,
        any_value(facility_name_hrrp)                                       AS facility_name_hrrp,
        any_value(state)                                                    AS state,
        bool_or(is_payment_eligible)                                        AS is_payment_eligible,
        count(*) FILTER (WHERE has_err)                                     AS n_conditions_with_err,
        coalesce(sum(discharges_est) FILTER (WHERE has_err), 0)             AS eligible_discharges_3yr,
        coalesce(sum(discharges_est) FILTER (WHERE has_err AND discharges_imputed), 0)
                                                                            AS imputed_discharges_3yr,
        coalesce(sum(excess_readmissions_annual), 0)                        AS excess_readmissions_annual_net,
        coalesce(sum(excess_readmissions_annual_pos), 0)                    AS excess_readmissions_annual_pos,
        sum(err * discharges_est) FILTER (WHERE has_err)
            / nullif(sum(discharges_est) FILTER (WHERE has_err), 0)         AS readmission_index,
        count(*) FILTER (WHERE is_above_threshold)                          AS n_conditions_above_threshold
    FROM fct_hospital_condition
    GROUP BY facility_id
)
SELECT
    h.facility_id,
    coalesce(i.facility_name, h.facility_name_hrrp)                         AS facility_name,
    h.facility_name_hrrp,
    h.state,
    i.city,
    i.county,
    coalesce(i.census_region, 'Unknown')                                    AS census_region,
    i.hospital_type,
    i.hospital_ownership,
    coalesce(i.ownership_group, 'Unknown')                                  AS ownership_group,
    i.has_emergency_services,
    CASE WHEN i.has_emergency_services THEN 'Has emergency dept'
         WHEN NOT i.has_emergency_services THEN 'No emergency dept'
         ELSE 'Unknown' END                                                 AS emergency_services_label,
    i.star_rating,
    CASE WHEN i.star_rating IS NOT NULL THEN i.star_rating::VARCHAR || ' star'
         ELSE 'Not rated' END                                               AS star_rating_label,
    m.mspb_ratio,
    CASE WHEN m.mspb_ratio IS NULL  THEN 'Not available'
         WHEN m.mspb_ratio < 0.95   THEN 'Below 0.95'
         WHEN m.mspb_ratio < 1.00   THEN '0.95-0.99'
         WHEN m.mspb_ratio < 1.05   THEN '1.00-1.04'
         ELSE '1.05 and above' END                                          AS mspb_band,
    h.n_conditions_with_err,
    h.n_conditions_above_threshold,
    h.eligible_discharges_3yr,
    h.imputed_discharges_3yr,
    h.excess_readmissions_annual_net,
    h.excess_readmissions_annual_pos,
    h.readmission_index,
    CASE WHEN h.n_conditions_with_err = 0          THEN 'No reported conditions'
         WHEN h.eligible_discharges_3yr < 400      THEN 'Low volume'
         WHEN h.eligible_discharges_3yr < 1000     THEN 'Mid volume'
         ELSE 'High volume' END                                             AS size_band,
    i.facility_id IS NOT NULL                                               AS in_hospital_info,
    m.facility_id IS NOT NULL                                               AS in_mspb_file,
    m.mspb_ratio IS NOT NULL                                                AS has_mspb_score,
    h.state = 'MD'                                                          AS is_maryland,
    h.is_payment_eligible
FROM hrrp h
LEFT JOIN stg_hospital_info i USING (facility_id)
LEFT JOIN stg_mspb m USING (facility_id);

SELECT size_band, count(*) AS n_hospitals,
       round(median(eligible_discharges_3yr)) AS median_discharges_3yr
FROM dim_hospital GROUP BY ALL ORDER BY n_hospitals DESC;
