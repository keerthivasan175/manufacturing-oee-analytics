-- =====================================================================
-- 01_validation_checks.sql
-- Purpose : prove the data in manufacturing_oee_db is complete and consistent
--           BEFORE any analysis. Run each query separately (Ctrl+Enter in Workbench).
-- =====================================================================
USE manufacturing_oee_db;

-- 1. Row counts (expected: dim_date 731, dim_plants 7, dim_parts 15,
--    dim_machines 10, dim_shifts 3, fact_production_runs = your cleaned row count)
SELECT 'dim_date' AS table_name, COUNT(*) AS row_count FROM dim_date
UNION ALL SELECT 'dim_plants', COUNT(*) FROM dim_plants
UNION ALL SELECT 'dim_parts', COUNT(*) FROM dim_parts
UNION ALL SELECT 'dim_machines', COUNT(*) FROM dim_machines
UNION ALL SELECT 'dim_shifts', COUNT(*) FROM dim_shifts
UNION ALL SELECT 'fact_production_runs', COUNT(*) FROM fact_production_runs;

-- 2. Orphan keys: fact rows whose key is missing in the dimension (expected: 0 each)
SELECT 'date_id' AS key_checked, COUNT(*) AS orphan_rows
FROM fact_production_runs f LEFT JOIN dim_date d ON f.date_id = d.date_id
WHERE d.date_id IS NULL
UNION ALL
SELECT 'plant_id', COUNT(*)
FROM fact_production_runs f LEFT JOIN dim_plants p ON f.plant_id = p.plant_id
WHERE p.plant_id IS NULL
UNION ALL
SELECT 'machine_id', COUNT(*)
FROM fact_production_runs f LEFT JOIN dim_machines m ON f.machine_id = m.machine_id
WHERE m.machine_id IS NULL
UNION ALL
SELECT 'shift_id', COUNT(*)
FROM fact_production_runs f LEFT JOIN dim_shifts s ON f.shift_id = s.shift_id
WHERE s.shift_id IS NULL
UNION ALL
SELECT 'part_id', COUNT(*)
FROM fact_production_runs f LEFT JOIN dim_parts pt ON f.part_id = pt.part_id
WHERE pt.part_id IS NULL;

-- 3. Duplicate grain: one row per date + plant + machine + shift (expected: no rows returned)
SELECT date_id, plant_id, machine_id, shift_id, COUNT(*) AS duplicate_count
FROM fact_production_runs
GROUP BY date_id, plant_id, machine_id, shift_id
HAVING COUNT(*) > 1;

-- 4. NULL check on every column (expected: all zeros)
SELECT
  SUM(run_id IS NULL)                AS null_run_id,
  SUM(date_id IS NULL)               AS null_date,
  SUM(plant_id IS NULL)              AS null_plant,
  SUM(machine_id IS NULL)            AS null_machine,
  SUM(shift_id IS NULL)              AS null_shift,
  SUM(part_id IS NULL)               AS null_part,
  SUM(planned_time_minutes IS NULL)  AS null_planned_time,
  SUM(actual_run_minutes IS NULL)    AS null_run_time,
  SUM(downtime_minutes IS NULL)      AS null_downtime,
  SUM(downtime_reason IS NULL)       AS null_reason,
  SUM(planned_units IS NULL)         AS null_planned_units,
  SUM(actual_units_produced IS NULL) AS null_actual_units,
  SUM(good_units IS NULL)            AS null_good_units,
  SUM(scrap_units IS NULL)           AS null_scrap_units,
  SUM(unit_cost IS NULL)             AS null_unit_cost,
  SUM(scrap_rework_cost IS NULL)     AS null_scrap_cost
FROM fact_production_runs;

-- 5. Business-rule checks (expected: all zeros)
SELECT
  SUM(actual_run_minutes + downtime_minutes <> planned_time_minutes)        AS run_plus_downtime_mismatch,
  SUM(good_units + scrap_units <> actual_units_produced)                    AS good_plus_scrap_mismatch,
  SUM((downtime_reason = 'None') <> (downtime_minutes = 0))                 AS reason_vs_downtime_mismatch,
  SUM(ABS(scrap_rework_cost - scrap_units * unit_cost * 0.45) > 1)          AS scrap_cost_formula_mismatch,
  SUM(actual_units_produced > planned_units * 1.25)                         AS suspiciously_high_output,
  SUM(downtime_minutes < 0 OR scrap_units < 0 OR good_units < 0)            AS negative_values
FROM fact_production_runs;

-- 6. Unit cost must equal the part's standard cost (expected: 0)
SELECT COUNT(*) AS unit_cost_mismatch
FROM fact_production_runs f
JOIN dim_parts p ON f.part_id = p.part_id
WHERE f.unit_cost <> p.standard_unit_cost;

-- 7. Downtime reason categories (expected: exactly 6, including 'None')
SELECT downtime_reason, COUNT(*) AS runs, SUM(downtime_minutes) AS total_downtime_min
FROM fact_production_runs
GROUP BY downtime_reason
ORDER BY total_downtime_min DESC;

-- 8. Date coverage
SELECT MIN(date_id) AS first_day, MAX(date_id) AS last_day, COUNT(DISTINCT date_id) AS days_with_data
FROM fact_production_runs;

-- 9. Runs per month (look for months that are unusually low: holidays, shutdowns)
SELECT d.year AS year_no, d.month_no, d.month_name, COUNT(*) AS runs
FROM fact_production_runs f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.year, d.month_no, d.month_name
ORDER BY d.year, d.month_no;
