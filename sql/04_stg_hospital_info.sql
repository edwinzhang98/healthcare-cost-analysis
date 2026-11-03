-- =============================================================================
-- 04_stg_hospital_info.sql                                     layer: staging
-- -----------------------------------------------------------------------------
-- Purpose : Clean hospital attributes and add the groupings used for
--           benchmarking:
--             ownership_group  Non-profit / For-profit / Government
--                              (CMS has 12 detailed ownership values; small ones
--                              such as Tribal (n=9 in HRRP) are folded in so
--                              peer groups stay large enough to compare)
--             census_region    US Census Bureau regions (DC counted in South)
--             star_rating      CMS overall star rating 1-5, NULL if not rated
-- Grain   : one row per facility_id
-- Inputs  : raw_hospital_info (01_raw_load.sql)
-- Outputs : stg_hospital_info
-- Run     : python -m src.sql_runner sql/04_stg_hospital_info.sql
-- =============================================================================

CREATE OR REPLACE TABLE stg_hospital_info AS
SELECT
    facility_id,
    trim(facility_name)                                         AS facility_name,
    citytown                                                    AS city,
    state,
    countyparish                                                AS county,
    hospital_type,
    hospital_ownership,
    CASE
        WHEN hospital_ownership LIKE 'Voluntary non-profit%'        THEN 'Non-profit'
        WHEN hospital_ownership IN ('Proprietary', 'Physician')     THEN 'For-profit'
        WHEN hospital_ownership LIKE 'Government%'
          OR hospital_ownership IN ('Tribal', 'Veterans Health Administration',
                                    'Department of Defense')        THEN 'Government'
        ELSE 'Other'
    END                                                         AS ownership_group,
    emergency_services = 'Yes'                                  AS has_emergency_services,
    TRY_CAST(hospital_overall_rating AS INTEGER)                AS star_rating,
    NULLIF(trim(hospital_overall_rating_footnote), '')          AS star_rating_footnote,
    TRY_CAST(count_of_facility_readm_measures  AS INTEGER)      AS n_readm_measures,
    TRY_CAST(count_of_readm_measures_better    AS INTEGER)      AS n_readm_measures_better,
    TRY_CAST(count_of_readm_measures_worse     AS INTEGER)      AS n_readm_measures_worse,
    CASE
        WHEN state IN ('CT','ME','MA','NH','RI','VT','NJ','NY','PA')               THEN 'Northeast'
        WHEN state IN ('IL','IN','MI','OH','WI','IA','KS','MN','MO','NE','ND','SD') THEN 'Midwest'
        WHEN state IN ('DE','DC','FL','GA','MD','NC','SC','VA','WV','AL','KY','MS',
                       'TN','AR','LA','OK','TX')                                     THEN 'South'
        WHEN state IN ('AZ','CO','ID','MT','NV','NM','UT','WY','AK','CA','HI','OR',
                       'WA')                                                         THEN 'West'
        ELSE 'Territory'
    END                                                         AS census_region
FROM raw_hospital_info;

SELECT ownership_group, count(*) AS n_hospitals
FROM stg_hospital_info
GROUP BY ALL
ORDER BY n_hospitals DESC;
