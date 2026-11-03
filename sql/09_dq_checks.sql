-- =============================================================================
-- 09_dq_checks.sql                                         layer: data quality
-- -----------------------------------------------------------------------------
-- Purpose : Sanity checks run on every build: row-count reconciliation to the
--           published file sizes, primary-key uniqueness, missing-value
--           patterns, value ranges, internal consistency, time ranges and the
--           join between the three CMS tables. Results feed
--           docs/03_data_quality_checks.md and the "Data & Sanity Checks" page.
--           status: PASS = as expected; WARN = expected limitation, documented;
--                   FAIL = needs investigation before results are used.
-- Inputs  : raw_hrrp, raw_mspb, raw_hospital_info, stg_hrrp_readmissions,
--           stg_mspb, stg_hospital_info, fct_hospital_condition, dim_hospital
-- Outputs : dq_check_results
-- Run     : python -m src.sql_runner sql/09_dq_checks.sql
-- =============================================================================

CREATE OR REPLACE TABLE dq_check_results AS
WITH
hrrp_hosp AS (SELECT DISTINCT facility_id, state FROM stg_hrrp_readmissions),
checks AS (
    -- ---------------- Row-count reconciliation ----------------
    SELECT 'R1' AS check_id, 'Row counts' AS category,
           'HRRP rows match published file (18,330)' AS check_name,
           '18330' AS expected, count(*)::VARCHAR AS actual,
           CASE WHEN count(*) = 18330 THEN 'PASS' ELSE 'FAIL' END AS status,
           '' AS detail
    FROM raw_hrrp
    UNION ALL
    SELECT 'R2', 'Row counts', 'MSPB rows match published file (4,626)', '4626',
           count(*)::VARCHAR, CASE WHEN count(*) = 4626 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM raw_mspb
    UNION ALL
    SELECT 'R3', 'Row counts', 'Hospital General Information rows match published file (5,419)',
           '5419', count(*)::VARCHAR, CASE WHEN count(*) = 5419 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM raw_hospital_info
    UNION ALL
    SELECT 'R4', 'Row counts', 'HRRP is a complete hospital x 6-condition grid',
           (count(DISTINCT facility_id) * 6)::VARCHAR, count(*)::VARCHAR,
           CASE WHEN count(*) = count(DISTINCT facility_id) * 6 THEN 'PASS' ELSE 'FAIL' END,
           count(DISTINCT facility_id)::VARCHAR || ' hospitals x 6 conditions'
    FROM stg_hrrp_readmissions
    -- ---------------- Primary keys ----------------
    UNION ALL
    SELECT 'K1', 'Primary key', 'HRRP (facility_id, condition) is unique', '0 duplicates',
           (count(*) - count(DISTINCT (facility_id, condition_code)))::VARCHAR || ' duplicates',
           CASE WHEN count(*) = count(DISTINCT (facility_id, condition_code)) THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'K2', 'Primary key', 'MSPB facility_id is unique', '0 duplicates',
           (count(*) - count(DISTINCT facility_id))::VARCHAR || ' duplicates',
           CASE WHEN count(*) = count(DISTINCT facility_id) THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_mspb
    UNION ALL
    SELECT 'K3', 'Primary key', 'Hospital General Information facility_id is unique', '0 duplicates',
           (count(*) - count(DISTINCT facility_id))::VARCHAR || ' duplicates',
           CASE WHEN count(*) = count(DISTINCT facility_id) THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hospital_info
    UNION ALL
    SELECT 'K4', 'Primary key', 'Every HRRP measure maps to one of the 6 conditions', '0 unmapped',
           count(*) FILTER (WHERE condition_label IS NULL)::VARCHAR || ' unmapped',
           CASE WHEN count(*) FILTER (WHERE condition_label IS NULL) = 0 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM fct_hospital_condition
    -- ---------------- Missing values / suppression ----------------
    UNION ALL
    SELECT 'N1', 'Missing values', 'Every blank HRRP value has a known reason (footnote / suppression)',
           '0 unexplained', count(*) FILTER (WHERE reporting_status = 'other')::VARCHAR || ' unexplained',
           CASE WHEN count(*) FILTER (WHERE reporting_status = 'other') = 0 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'N2', 'Missing values', 'Share of hospital x condition rows with a published ERR', 'info',
           round(100.0 * avg(has_err::INT), 1)::VARCHAR || '%', 'WARN',
           count(*) FILTER (WHERE reporting_status = 'too_few_cases')::VARCHAR || ' too few cases (<25), '
           || count(*) FILTER (WHERE reporting_status = 'not_available')::VARCHAR || ' not available, '
           || count(*) FILTER (WHERE reporting_status = 'no_cases')::VARCHAR || ' no cases'
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'N3', 'Missing values', 'Rows with ERR but suppressed counts (discharges imputed)', 'info',
           count(*) FILTER (WHERE reporting_status = 'counts_suppressed')::VARCHAR || ' rows', 'WARN',
           'imputed discharges = '
           || round(100.0 * sum(discharges_est) FILTER (WHERE discharges_imputed)
                    / sum(discharges_est) FILTER (WHERE has_err), 1)::VARCHAR
           || '% of eligible discharges (hip/knee and CABG most affected)'
    FROM fct_hospital_condition
    UNION ALL
    SELECT 'N4', 'Missing values', 'MSPB score available for HRRP hospitals', 'info',
           count(*) FILTER (WHERE has_mspb_score)::VARCHAR || ' of ' || count(*)::VARCHAR, 'WARN',
           'missing scores carry CMS footnotes (e.g., too few cases, not available)'
    FROM dim_hospital
    -- ---------------- Value ranges / consistency ----------------
    UNION ALL
    SELECT 'V1', 'Value range', 'ERR within plausible range [0.3, 2.0]', '0 outside',
           count(*) FILTER (WHERE err NOT BETWEEN 0.3 AND 2.0)::VARCHAR || ' outside',
           CASE WHEN count(*) FILTER (WHERE err NOT BETWEEN 0.3 AND 2.0) = 0 THEN 'PASS' ELSE 'FAIL' END,
           'min ' || round(min(err), 4)::VARCHAR || ', max ' || round(max(err), 4)::VARCHAR
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'V2', 'Value range', 'Predicted and expected rates between 0% and 100%', '0 outside',
           count(*) FILTER (WHERE has_err AND NOT (predicted_rate_pct BETWEEN 0 AND 100
                                              AND expected_rate_pct BETWEEN 0 AND 100))::VARCHAR || ' outside',
           CASE WHEN count(*) FILTER (WHERE has_err AND NOT (predicted_rate_pct BETWEEN 0 AND 100
                                              AND expected_rate_pct BETWEEN 0 AND 100)) = 0
                THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'V3', 'Consistency', 'ERR equals predicted / expected rate (rounding only)', 'max diff < 0.001',
           'max diff ' || round(max(abs(err - predicted_rate_pct / expected_rate_pct)), 6)::VARCHAR,
           CASE WHEN max(abs(err - predicted_rate_pct / expected_rate_pct)) < 0.001 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hrrp_readmissions WHERE has_err
    UNION ALL
    SELECT 'V4', 'Consistency', 'Published discharges are at least 25 wherever an ERR is shown', 'min >= 25',
           'min ' || min(discharges)::VARCHAR,
           CASE WHEN min(discharges) >= 25 THEN 'PASS' ELSE 'FAIL' END, 'CMS publishes an ERR only with 25+ cases'
    FROM stg_hrrp_readmissions WHERE has_err AND discharges IS NOT NULL
    UNION ALL
    SELECT 'V5', 'Consistency', 'Published readmission counts are 11 or more (small cells hidden)', 'min >= 11',
           'min ' || min(readmissions)::VARCHAR,
           CASE WHEN min(readmissions) >= 11 THEN 'PASS' ELSE 'FAIL' END,
           'confirms counts of 1-10 are suppressed'
    FROM stg_hrrp_readmissions WHERE readmissions IS NOT NULL
    UNION ALL
    SELECT 'V6', 'Consistency', 'Readmissions never exceed discharges', '0 rows',
           count(*) FILTER (WHERE readmissions > discharges)::VARCHAR || ' rows',
           CASE WHEN count(*) FILTER (WHERE readmissions > discharges) = 0 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'V7', 'Consistency', 'Observed rate tracks CMS predicted rate (correlation)', '>= 0.80',
           round(corr(observed_rate_pct, predicted_rate_pct), 3)::VARCHAR,
           CASE WHEN corr(observed_rate_pct, predicted_rate_pct) >= 0.8 THEN 'PASS' ELSE 'FAIL' END,
           'predicted rates are shrunk toward the average, so the match is not exact'
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'V8', 'Known numbers', 'National median ERR per condition is close to 1.00', 'all within 0.98-1.02',
           'range ' || round(min(penalty_threshold_err), 4)::VARCHAR || '-' || round(max(penalty_threshold_err), 4)::VARCHAR,
           CASE WHEN min(penalty_threshold_err) >= 0.98 AND max(penalty_threshold_err) <= 1.02 THEN 'PASS' ELSE 'FAIL' END,
           'ERR is built so that an average hospital scores about 1.00'
    FROM fct_hospital_condition
    -- ---------------- Time ranges ----------------
    UNION ALL
    SELECT 'T1', 'Time range', 'HRRP performance period is 2021-07-01 to 2024-06-30 on every row',
           '1 period', count(DISTINCT (period_start, period_end))::VARCHAR || ' period(s): '
           || min(period_start)::VARCHAR || ' to ' || max(period_end)::VARCHAR,
           CASE WHEN count(DISTINCT (period_start, period_end)) = 1
                 AND min(period_start) = DATE '2021-07-01' AND max(period_end) = DATE '2024-06-30'
                THEN 'PASS' ELSE 'FAIL' END, ''
    FROM stg_hrrp_readmissions
    UNION ALL
    SELECT 'T2', 'Time range', 'MSPB period is calendar 2024 on every row',
           '1 period', count(DISTINCT (mspb_period_start, mspb_period_end))::VARCHAR || ' period(s): '
           || min(mspb_period_start)::VARCHAR || ' to ' || max(mspb_period_end)::VARCHAR,
           CASE WHEN count(DISTINCT (mspb_period_start, mspb_period_end)) = 1
                 AND min(mspb_period_start) = DATE '2024-01-01' AND max(mspb_period_end) = DATE '2024-12-31'
                THEN 'PASS' ELSE 'FAIL' END,
           'note: MSPB year does not line up with the HRRP window (documented limitation)'
    FROM stg_mspb
    -- ---------------- Joins ----------------
    UNION ALL
    SELECT 'J1', 'Join', 'HRRP hospitals found in Hospital General Information',
           count(*)::VARCHAR, count(i.facility_id)::VARCHAR,
           CASE WHEN count(i.facility_id) = count(*) THEN 'PASS' ELSE 'WARN' END,
           (count(*) - count(i.facility_id))::VARCHAR
           || ' not found: closed, merged or converted since the period (e.g., to critical access)'
    FROM hrrp_hosp h LEFT JOIN stg_hospital_info i USING (facility_id)
    UNION ALL
    SELECT 'J2', 'Join', 'HRRP hospitals found in MSPB file', count(*)::VARCHAR,
           count(m.facility_id)::VARCHAR,
           CASE WHEN count(m.facility_id) = count(*) THEN 'PASS' ELSE 'WARN' END,
           'same ' || (count(*) - count(m.facility_id))::VARCHAR || ' hospitals as J1'
    FROM hrrp_hosp h LEFT JOIN stg_mspb m USING (facility_id)
    UNION ALL
    SELECT 'J3', 'Join', 'Matched HRRP hospitals are all Acute Care Hospitals', '100%',
           round(100.0 * avg((hospital_type = 'Acute Care Hospitals')::INT), 1)::VARCHAR || '%',
           CASE WHEN avg((hospital_type = 'Acute Care Hospitals')::INT) = 1 THEN 'PASS' ELSE 'FAIL' END,
           'HRRP applies to short-term acute care (IPPS) hospitals only'
    FROM dim_hospital WHERE in_hospital_info
    UNION ALL
    SELECT 'J4', 'Join', 'State agrees between HRRP and Hospital General Information', '0 mismatches',
           count(*) FILTER (WHERE h.state <> i.state)::VARCHAR || ' mismatches',
           CASE WHEN count(*) FILTER (WHERE h.state <> i.state) = 0 THEN 'PASS' ELSE 'FAIL' END, ''
    FROM hrrp_hosp h JOIN stg_hospital_info i USING (facility_id)
    UNION ALL
    SELECT 'J5', 'Join', 'Hospital name differs between files (renamed since the period)', 'info',
           count(*) FILTER (WHERE upper(facility_name_hrrp) <> upper(facility_name))::VARCHAR || ' hospitals',
           'WARN', 'IDs match, so names are informational only; current name is shown'
    FROM dim_hospital WHERE in_hospital_info
    UNION ALL
    SELECT 'F1', 'Format', 'HRRP facility IDs are 6-digit CMS Certification Numbers', '0 malformed',
           count(*) FILTER (WHERE NOT regexp_full_match(facility_id, '[0-9]{6}'))::VARCHAR || ' malformed',
           CASE WHEN count(*) FILTER (WHERE NOT regexp_full_match(facility_id, '[0-9]{6}')) = 0
                THEN 'PASS' ELSE 'FAIL' END, 'IDs are read as text to keep leading zeros'
    FROM hrrp_hosp
    UNION ALL
    SELECT 'F2', 'Format', 'HRRP IDs fall in the IPPS hospital range (last 4 digits 0001-0879 short-term, 0880-0899 demonstration)',
           '0 outside', count(*) FILTER (WHERE substr(facility_id, 3, 4)::INT NOT BETWEEN 1 AND 899)::VARCHAR || ' outside',
           CASE WHEN count(*) FILTER (WHERE substr(facility_id, 3, 4)::INT NOT BETWEEN 1 AND 899) = 0
                THEN 'PASS' ELSE 'FAIL' END, ''
    FROM hrrp_hosp
    UNION ALL
    SELECT 'S1', 'Scope', 'Maryland hospitals (exempt from HRRP payment cuts) flagged', 'info',
           count(*) FILTER (WHERE is_maryland)::VARCHAR || ' hospitals', 'WARN',
           'kept for benchmarking, excluded from penalty totals'
    FROM dim_hospital
    UNION ALL
    SELECT 'S2', 'Scope', 'Payment-eligible hospitals in the analysis', 'info',
           count(*) FILTER (WHERE is_payment_eligible)::VARCHAR || ' hospitals ('
           || count(*) FILTER (WHERE is_payment_eligible AND n_conditions_with_err > 0)::VARCHAR
           || ' with at least one ERR)', 'PASS', ''
    FROM dim_hospital
)
SELECT * FROM checks ORDER BY check_id;

SELECT check_id, status, check_name, actual FROM dq_check_results ORDER BY check_id;
