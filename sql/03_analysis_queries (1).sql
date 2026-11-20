-- =====================================================================
-- 03_analysis_queries.sql
-- Purpose : answer the business questions about plant performance.
-- Run ONE query at a time (click inside it, press Ctrl+Enter), then write your
-- insight in the "Insight:" line. Requires the views from 02_kpi_views.sql.
-- Note: OEE = Availability x Performance x Quality, calculated on summed values (ratio of sums).
-- =====================================================================
USE manufacturing_oee_db;

-- Q1. What are the overall KPIs for the whole business?
SELECT
    COUNT(*)                                                                    AS runs,
    ROUND(100.0 * SUM(actual_run_minutes) / SUM(planned_time_minutes), 1)       AS availability_pct,
    ROUND(100.0 * SUM(actual_units_produced) / SUM(ideal_units_in_run_time), 1) AS performance_pct,
    ROUND(100.0 * SUM(good_units) / SUM(actual_units_produced), 1)              AS quality_pct,
    ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1)                      AS oee_pct,
    SUM(scrap_rework_cost)                                                      AS cost_of_poor_quality_inr
FROM vw_run_detail;
-- Insight:

-- Q2. Which plants perform best and worst? (ranked by OEE)
SELECT RANK() OVER (ORDER BY oee_pct DESC) AS oee_rank, v.*
FROM vw_oee_by_plant v
ORDER BY oee_rank;
-- Insight:

-- Q3. Which machines have the lowest OEE, and how far is their availability below the rated value?
SELECT machine_name, operation_type, installation_year, rated_availability_pct,
       availability_pct, availability_gap_pts, performance_pct, quality_pct, oee_pct
FROM vw_oee_by_machine
ORDER BY oee_pct;
-- Insight:

-- Q4. How do the three shifts compare?
SELECT * FROM vw_oee_by_shift ORDER BY shift_id;
-- Insight:

-- Q5. Downtime Pareto: which reasons cause most of the lost time?
SELECT * FROM vw_downtime_pareto ORDER BY lost_minutes DESC;
-- Insight:

-- Q6. Does the downtime reason differ by machine type? (minutes lost)
SELECT
    operation_type,
    SUM(CASE WHEN downtime_reason = 'Tool Breakage'         THEN downtime_minutes ELSE 0 END) AS tool_breakage_min,
    SUM(CASE WHEN downtime_reason = 'Hydraulic Leak'        THEN downtime_minutes ELSE 0 END) AS hydraulic_leak_min,
    SUM(CASE WHEN downtime_reason = 'Material Shortage'     THEN downtime_minutes ELSE 0 END) AS material_shortage_min,
    SUM(CASE WHEN downtime_reason = 'Scheduled Maintenance' THEN downtime_minutes ELSE 0 END) AS scheduled_maintenance_min,
    SUM(CASE WHEN downtime_reason = 'Operator Adjustment'   THEN downtime_minutes ELSE 0 END) AS operator_adjustment_min
FROM vw_run_detail
GROUP BY operation_type
ORDER BY operation_type;
-- Insight:

-- Q7. Monthly OEE trend with the change versus the previous month
SELECT year_no, month_no, month_name, oee_pct,
       ROUND(oee_pct - LAG(oee_pct) OVER (ORDER BY year_no, month_no), 1) AS change_vs_prev_month
FROM vw_oee_by_month
ORDER BY year_no, month_no;
-- Insight:

-- Q8. Which plants improved or declined? (first quarter vs last quarter)
WITH q AS (
    SELECT plant_name, year_no, quarter_name,
           ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1) AS oee_pct
    FROM vw_run_detail
    GROUP BY plant_name, year_no, quarter_name
),
ranked AS (
    SELECT plant_name, year_no, quarter_name, oee_pct,
           ROW_NUMBER() OVER (PARTITION BY plant_name ORDER BY year_no, quarter_name)           AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY plant_name ORDER BY year_no DESC, quarter_name DESC) AS rn_last
    FROM q
)
SELECT plant_name,
       MAX(CASE WHEN rn_first = 1 THEN oee_pct END) AS first_quarter_oee,
       MAX(CASE WHEN rn_last  = 1 THEN oee_pct END) AS last_quarter_oee,
       ROUND(MAX(CASE WHEN rn_last = 1 THEN oee_pct END)
           - MAX(CASE WHEN rn_first = 1 THEN oee_pct END), 1) AS change_pts
FROM ranked
GROUP BY plant_name
ORDER BY change_pts DESC;
-- Insight:

-- Q9. Which 10 parts cost the most in scrap and rework?
SELECT part_name, part_category,
       SUM(actual_units_produced)                                          AS units_produced,
       SUM(scrap_units)                                                    AS scrap_units,
       ROUND(100.0 * SUM(scrap_units) / SUM(actual_units_produced), 2)     AS scrap_rate_pct,
       SUM(scrap_rework_cost)                                              AS cost_of_poor_quality_inr
FROM vw_run_detail
GROUP BY part_name, part_category
ORDER BY cost_of_poor_quality_inr DESC
LIMIT 10;
-- Insight:

-- Q10. Which plant + machine combinations are the 10 worst performers? (at least 300 runs)
SELECT plant_name, machine_name,
       COUNT(*)                                          AS runs,
       ROUND(100.0 * SUM(actual_run_minutes) * SUM(good_units) / (SUM(planned_time_minutes) * SUM(ideal_units_in_run_time)), 1) AS oee_pct,
       ROUND(AVG(downtime_minutes), 1)                   AS avg_downtime_min_per_run
FROM vw_run_detail
GROUP BY plant_name, machine_name
HAVING COUNT(*) >= 300
ORDER BY oee_pct
LIMIT 10;
-- Insight:

-- Q11. Seasonality: does hydraulic-leak downtime change by month? (minutes lost per run)
SELECT month_no, month_name,
       ROUND(SUM(CASE WHEN downtime_reason = 'Hydraulic Leak' THEN downtime_minutes ELSE 0 END) * 1.0 / COUNT(*), 2)
           AS hydraulic_leak_min_per_run
FROM vw_run_detail
GROUP BY month_no, month_name
ORDER BY month_no;
-- Insight:

-- Q12. Spike detection: which plant-months had material-shortage downtime above 1.8x that plant's monthly average?
WITH m AS (
    SELECT plant_name, year_no, month_no,
           SUM(CASE WHEN downtime_reason = 'Material Shortage' THEN downtime_minutes ELSE 0 END) AS shortage_min
    FROM vw_run_detail
    GROUP BY plant_name, year_no, month_no
),
a AS (
    SELECT m.*, AVG(shortage_min) OVER (PARTITION BY plant_name) AS plant_avg_min
    FROM m
)
SELECT plant_name, year_no, month_no, shortage_min,
       ROUND(plant_avg_min, 0)            AS plant_monthly_avg_min,
       ROUND(shortage_min / plant_avg_min, 2) AS times_average
FROM a
WHERE shortage_min > 1.8 * plant_avg_min
ORDER BY times_average DESC;
-- Insight:

-- Q13. Machine ageing: average downtime per run by quarter
SELECT machine_name, installation_year, year_no, quarter_name,
       ROUND(AVG(downtime_minutes), 1) AS avg_downtime_min_per_run
FROM vw_run_detail
GROUP BY machine_name, installation_year, year_no, quarter_name
ORDER BY machine_name, year_no, quarter_name;
-- Insight:

-- Q14. Which machines are getting worse? (downtime per run, first quarter vs last quarter)
WITH q AS (
    SELECT machine_name, installation_year, year_no, quarter_name,
           AVG(downtime_minutes) AS avg_downtime
    FROM vw_run_detail
    GROUP BY machine_name, installation_year, year_no, quarter_name
),
ranked AS (
    SELECT q.*,
           ROW_NUMBER() OVER (PARTITION BY machine_name ORDER BY year_no, quarter_name)           AS rn_first,
           ROW_NUMBER() OVER (PARTITION BY machine_name ORDER BY year_no DESC, quarter_name DESC) AS rn_last
    FROM q
)
SELECT machine_name, installation_year,
       ROUND(MAX(CASE WHEN rn_first = 1 THEN avg_downtime END), 1) AS first_quarter_downtime,
       ROUND(MAX(CASE WHEN rn_last  = 1 THEN avg_downtime END), 1) AS last_quarter_downtime,
       ROUND(MAX(CASE WHEN rn_last = 1 THEN avg_downtime END)
           - MAX(CASE WHEN rn_first = 1 THEN avg_downtime END), 1) AS change_min_per_run
FROM ranked
GROUP BY machine_name, installation_year
ORDER BY change_min_per_run DESC;
-- Insight:
