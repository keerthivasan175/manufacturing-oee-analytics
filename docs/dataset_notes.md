# Manufacturing OEE Database (Large, Simulated)

A star-schema database for analyzing **Overall Equipment Effectiveness (OEE)** across 7 plants, 10 machine types, 15 automotive parts and 3 shifts, from **1 Jan 2024 to 31 Dec 2025**.

> **Note:** The data is **simulated**. The schema and the 4 dimension tables (plants, parts, machines, shifts) come from the template database, and `dim_date` is extended to 2 years. The fact table is generated at business scale by `scripts/generate_oee_dataset.py` (seed 2024, so it is reproducible).

## Contents

| Path | What it is |
|---|---|
| `data/raw/fact_production_runs_raw.csv` | **Messy raw export** of the fact table (115,025 rows, 19 columns). Start here |
| `notebooks/01_data_cleaning.ipynb` | Step-by-step Python cleaning of the raw export |
| `data/cleaned/` | Output folder for your cleaned file and cleaning log |
| `sql/01_validation_checks.sql` | Data validation queries (row counts, orphan keys, business rules) |
| `sql/02_kpi_views.sql` | Reusable views with the OEE KPI definitions |
| `sql/03_analysis_queries.sql` | 14 business-question queries (joins, CTEs, window functions) |
| `database/Manufacturing_OEE_DB_Large.sql` | MySQL dump (creates `manufacturing_oee_db`, all tables and data) |
| `data/*.csv` | The clean tables as CSV: 5 dimensions and the fact table (reference / answer key) |
| `scripts/generate_oee_dataset.py` | Generates the clean database and CSVs |
| `scripts/generate_raw_layer.py` | Generates the messy raw export from the clean fact table |

## Project workflow

```
raw MES export (messy CSV)  ->  Python cleaning  ->  MySQL (star schema)  ->  SQL analysis  ->  Power BI  ->  insights
```

The five dimension tables come from master data and are already clean. Only the fact table arrives as a messy export.

## Data quality issues in the raw export

- Junk columns (operator, remarks, export batch) and column names that differ from the schema
- Duplicate runs (same `run_id` exported twice, in different formats)
- Five mixed date formats, impossible dates (31-02-2024) and year typos
- The same plant, machine, part, shift and downtime reason written many different ways (case, spaces, hyphens, abbreviations)
- Keys that do not exist in the master data
- Numbers stored as text (`"480 min"`, `"Rs. 1,400"`, `"8 hrs"`, `"12.0"`) and placeholders (`N/A`, `null`, `-`, blank)
- Missing derived values (run time, good units, unit cost, scrap cost)
- Typos (negative scrap, a value 10x too large, downtime that does not add up with run time)

All problems except invalid dates and unknown keys can be repaired with business rules (see the notebook). The notebook ends with a reconciliation against the clean source table.

**pandas tip:** `downtime_reason` contains the real text value `None`. Read these files with `pd.read_csv(..., keep_default_na=False)`, otherwise pandas turns it into a missing value.

## Tables

| Table | Rows | Grain |
|---|---|---|
| `dim_date` | 731 | one row per calendar day |
| `dim_plants` | 7 | plant (city, state, facility type, monthly capacity) |
| `dim_parts` | 15 | part (category, material, standard unit cost) |
| `dim_machines` | 10 | machine type (operation, line, install year, rated availability %) |
| `dim_shifts` | 3 | shift (start/end time, lead) |
| `fact_production_runs` | ~113,700 | **one machine, in one plant, in one shift, on one day** |

**Fact columns:** `run_id`, `date_id`, `plant_id`, `machine_id`, `shift_id`, `part_id`, `planned_time_minutes`, `actual_run_minutes`, `downtime_minutes`, `downtime_reason`, `planned_units`, `actual_units_produced`, `good_units`, `scrap_units`, `unit_cost`, `scrap_rework_cost`.

```
dim_date ─┐
dim_plants ─┤
dim_machines ─┼── fact_production_runs
dim_shifts ─┤
dim_parts ─┘
```

## Business rules built into the data

- `actual_run_minutes = planned_time_minutes - downtime_minutes`
- `good_units + scrap_units = actual_units_produced`
- `scrap_rework_cost = scrap_units x unit_cost x 0.45`
- `downtime_reason = 'None'` when `downtime_minutes = 0`
- Downtime reasons: Operator Adjustment (small stops and changeovers), Tool Breakage, Hydraulic Leak, Material Shortage, Scheduled Maintenance
- Plants are closed on Sundays and on public holidays (Pongal, Diwali, etc.), except the continuous furnace and foundry cells
- One row per plant + machine + shift + day (no duplicates)

## KPI formulas

- **Availability** = `SUM(actual_run_minutes) / SUM(planned_time_minutes)`
- **Performance** = `SUM(actual_units_produced) / SUM(planned_units x actual_run_minutes / planned_time_minutes)`
- **Quality** = `SUM(good_units) / SUM(actual_units_produced)`
- **OEE** = Availability x Performance x Quality, calculated on summed values: `SUM(run minutes) x SUM(good units) / (SUM(planned minutes) x SUM(ideal units))`
- **Scrap rate** = `SUM(scrap_units) / SUM(actual_units_produced)`
- **Cost of poor quality** = `SUM(scrap_rework_cost)`

## Load into MySQL

```bash
mysql -u root -p < database/Manufacturing_OEE_DB_Large.sql
```

Or in MySQL Workbench: *Server > Data Import > Import from Self-Contained File*. For Power BI, connect to the MySQL database or import the CSVs, then relate each `*_id` in the fact table to its dimension.

## Questions to answer in your analysis

1. Which plant, machine and shift has the lowest OEE, and which of Availability, Performance or Quality is the cause?
2. What are the top downtime reasons by total lost minutes? Do they differ by machine type?
3. How do OEE, downtime and scrap trend month by month and quarter by quarter? Are there spikes?
4. Is any machine getting worse over time (ageing)? How does machine age relate to downtime and scrap?
5. How much does poor quality cost per plant, per part and per shift?
6. Are there seasonal effects (summer months, festival periods)?
7. Which plant is improving or declining, and why?
