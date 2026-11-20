-- =====================================================================
-- 02_kpi_views.sql
-- Purpose : reusable views so every analysis query uses the SAME KPI definitions.
--   Availability = SUM(actual_run_minutes) / SUM(planned_time_minutes)
--   Performance  = SUM(actual_units_produced) / SUM(planned_units * actual_run_minutes / planned_time_minutes)
--   Quality      = SUM(good_units) / SUM(actual_units_produced)
--   OEE          = Availability x Performance x Quality
-- KPIs are always "ratio of sums" (never an average of row-level percentages).
-- Run the whole file once (lightning-bolt button in Workbench).
-- =====================================================================
USE manufacturing_oee_db;

-- ---------------------------------------------------------------------
-- Base view: fact table joined to every dimension (one row per production run)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_run_detail AS
SELECT
    f.run_id,
    f.date_id,
    d.year          AS year_no,
    d.quarter       AS quarter_name,
    d.month_no,
    d.month_name,
    d.day_name,
    d.is_weekend,
    f.plant_id,
    p.plant_name,
    p.city,
    p.facility_type,
    f.machine_id,
    m.machine_name,
    m.operation_type,
    m.installation_year,
    m.rated_availability_pct,
    f.shift_id,
    s.shift_name,
    f.part_id,
    pt.part_name,
    pt.category     AS part_category,
    f.planned_time_minutes,
    f.actual_run_minutes,
    f.downtime_minutes,
    f.downtime_reason,
    f.planned_units,
    f.actual_units_produced,
    f.good_units,
    f.scrap_units,
    f.unit_cost,
    f.scrap_rework_cost,
    f.planned_units * f.actual_run_minutes * 1.0 / f.planned_time_minutes AS ideal_units_in_run_time
FROM fact_production_runs f
JOIN dim_date     d  ON f.date_id    = d.date_id
JOIN dim_plants   p  ON f.plant_id   = p.plant_id
JOIN dim_machines m  ON f.machine_id = m.machine_id
JOIN dim_shifts   s  ON f.shift_id   = s.shift_id
JOIN dim_parts    pt ON f.part_id    = pt.part_id;

-- ---------------------------------------------------------------------
-- OEE by plant
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_oee_by_plant AS
SELECT
    plant_id,
    plant_name,
    COUNT(*)                                                                   AS runs,
    ROUND(100.0 * SUM(actual_run_minutes) / SUM(planned_time_minutes), 1)      AS availability_pct,
    ROUND(100.0 * SUM(actual_units_produced) / SUM(ideal_units_in_run_time), 1) AS performance_pct,
    ROUND(100.0 * SUM(good_units) / SUM(actual_units_produced), 1)             AS quality_pct,
    ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1)                     AS oee_pct,
    ROUND(100.0 * SUM(scrap_units) / SUM(actual_units_produced), 2)            AS scrap_rate_pct,
    ROUND(SUM(downtime_minutes) / 60.0, 0)                                     AS downtime_hours,
    SUM(scrap_rework_cost)                                                     AS cost_of_poor_quality_inr
FROM vw_run_detail
GROUP BY plant_id, plant_name;

-- ---------------------------------------------------------------------
-- OEE by machine (includes machine age and the gap to rated availability)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_oee_by_machine AS
SELECT
    machine_id,
    machine_name,
    operation_type,
    installation_year,
    rated_availability_pct,
    COUNT(*)                                                                   AS runs,
    ROUND(100.0 * SUM(actual_run_minutes) / SUM(planned_time_minutes), 1)      AS availability_pct,
    ROUND(rated_availability_pct - 100.0 * SUM(actual_run_minutes) / SUM(planned_time_minutes), 1) AS availability_gap_pts,
    ROUND(100.0 * SUM(actual_units_produced) / SUM(ideal_units_in_run_time), 1) AS performance_pct,
    ROUND(100.0 * SUM(good_units) / SUM(actual_units_produced), 1)             AS quality_pct,
    ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1)                     AS oee_pct,
    ROUND(100.0 * SUM(scrap_units) / SUM(actual_units_produced), 2)            AS scrap_rate_pct,
    SUM(scrap_rework_cost)                                                     AS cost_of_poor_quality_inr
FROM vw_run_detail
GROUP BY machine_id, machine_name, operation_type, installation_year, rated_availability_pct;

-- ---------------------------------------------------------------------
-- OEE by shift
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_oee_by_shift AS
SELECT
    shift_id,
    shift_name,
    COUNT(*)                                                                   AS runs,
    ROUND(100.0 * SUM(actual_run_minutes) / SUM(planned_time_minutes), 1)      AS availability_pct,
    ROUND(100.0 * SUM(actual_units_produced) / SUM(ideal_units_in_run_time), 1) AS performance_pct,
    ROUND(100.0 * SUM(good_units) / SUM(actual_units_produced), 1)             AS quality_pct,
    ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1)                     AS oee_pct,
    ROUND(100.0 * SUM(scrap_units) / SUM(actual_units_produced), 2)            AS scrap_rate_pct,
    ROUND(AVG(downtime_minutes), 1)                                            AS avg_downtime_min_per_run
FROM vw_run_detail
GROUP BY shift_id, shift_name;

-- ---------------------------------------------------------------------
-- OEE by month
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_oee_by_month AS
SELECT
    year_no,
    month_no,
    month_name,
    COUNT(*)                                                                   AS runs,
    ROUND(100.0 * SUM(actual_run_minutes) / SUM(planned_time_minutes), 1)      AS availability_pct,
    ROUND(100.0 * SUM(actual_units_produced) / SUM(ideal_units_in_run_time), 1) AS performance_pct,
    ROUND(100.0 * SUM(good_units) / SUM(actual_units_produced), 1)             AS quality_pct,
    ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1)                     AS oee_pct,
    ROUND(100.0 * SUM(scrap_units) / SUM(actual_units_produced), 2)            AS scrap_rate_pct
FROM vw_run_detail
GROUP BY year_no, month_no, month_name;

-- ---------------------------------------------------------------------
-- Downtime Pareto (excludes runs with no downtime)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_downtime_pareto AS
SELECT
    downtime_reason,
    COUNT(*)                                                                    AS events,
    SUM(downtime_minutes)                                                       AS lost_minutes,
    ROUND(100.0 * SUM(downtime_minutes) / SUM(SUM(downtime_minutes)) OVER (), 1) AS pct_of_total,
    ROUND(100.0 * SUM(SUM(downtime_minutes)) OVER (ORDER BY SUM(downtime_minutes) DESC)
          / SUM(SUM(downtime_minutes)) OVER (), 1)                              AS cumulative_pct
FROM vw_run_detail
WHERE downtime_reason <> 'None'
GROUP BY downtime_reason;

-- Quick test: every view should return rows
SELECT * FROM vw_oee_by_plant ORDER BY oee_pct DESC;
