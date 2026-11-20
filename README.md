# Manufacturing OEE Analytics: Python, SQL and Power BI

An end-to-end analysis of production performance across **7 plants, 10 machine types and 3 shifts** (Jan 2024 - Dec 2025). The project takes a messy production export, cleans it in Python, loads it into a MySQL star schema, analyses it with SQL, and presents the results in a 3-page Power BI dashboard.

> **Data note:** the dataset is **simulated**. The schema (a star schema) and the master data come from a template database, and the production records were generated at business scale (113,000+ production runs) using `scripts/generate_oee_dataset.py`. The raw export was then deliberately made messy with `scripts/generate_raw_layer.py` to practise real data cleaning.

**Author:** Keerthivasan DS | [LinkedIn](https://www.linkedin.com/in/keerthivasan-ds?utm_source=share_via&utm_content=profile&utm_medium=member_android) | vasankeerthi005@gmail.com

---

## Business problem

A multi-plant automotive-component manufacturer wants to know **where it loses production time and quality**, and which plants, machines, shifts and parts should be fixed first. The main KPI is **OEE (Overall Equipment Effectiveness)**.

## Dashboard

| Executive Overview | Downtime Analysis | Quality & Cost 
|---|---|---|
| ![Executive Overview](dashboard/screenshots/01_executive_overview.png) | ![Downtime Analysis](dashboard/screenshots/02_downtime_analysis.png) | ![Quality and Cost](dashboard/screenshots/03_quality_and_cost.png) |

A PDF copy of the report is in [`dashboard/`](dashboard/).

## Key findings

1. **Overall OEE is 82.8%**, about 2.2 points below the 85% target. Availability is 93.4%, Performance 91.5% and Quality 96.9%. **Speed loss (Performance) is the biggest loss**, larger than downtime.
2. **Plant performance varies by 7.7 points.** Sriperumbudur (86.7%) is the only plant above target. Manesar (79.0%) and Madurai (80.5%) are the weakest. Manesar improved from 74.9% (Q1 2024) to 83.3% (Q4 2025), while Madurai stayed flat at about 80.6%.
3. **Shift 3 (night) underperforms:** OEE 80.0% against 84.0% for Shift 1. The gap comes from **Performance (89.2% vs 92.4%) and Quality (96.1% vs 97.3%)**, not from availability (93.3% vs 93.4%). Its scrap rate is 3.9% versus 2.7%.
4. **Three reasons cause 78% of lost minutes:** Operator Adjustment (36%), Hydraulic Leak (24%) and Tool Breakage (18%).
5. **Hydraulic leaks are concentrated and seasonal.** Stamping accounts for 44% of hydraulic-leak minutes, and leaks peak in **April-June** (about 1,500-1,650 hours a month against about 1,050 in other months).
6. **One ageing machine is getting worse.** The Schuler stamping press (installed 2018) went from 36.9 to 47.4 minutes of downtime per run between Q1 2024 and Q4 2025, while most other machines improved.
7. **Supply disruptions:** material-shortage downtime at Pune was about 2.6x its normal level in Aug-Sep 2024, and at Bengaluru about 2.2x in Feb 2025.
8. **Cost of poor quality is ₹58.5 crore.** Die Casting (4.8%) and Forging (4.3%) have the highest scrap rates. Transmission, Powertrain and Engine parts make up about 51% of the cost. The Forged Connecting Rod has the highest scrap rate (4.0%) but the lowest cost (₹1.9 Cr), while the Crankshaft costs the most (₹7.4 Cr), so priorities should follow **cost**, not scrap rate alone.

## Recommendations

- Run a **speed-loss and training review on Shift 3**, since its problem is performance and quality, not downtime.
- Plan an **overhaul or predictive-maintenance programme for the Schuler press**, and start **hydraulic-system checks before April** on stamping, forging and die-casting machines.
- Add **safety stock or a second supplier** for the materials behind the Pune and Bengaluru shortages.
- Launch **scrap-reduction projects** on high-cost parts first (Crankshaft, Front Suspension Control Arm, Exhaust Manifold).
- Set an improvement plan for **Madurai and Manesar**, starting with their Forging and Die Casting lines.

*(These recommendations are based on simulated data and are for demonstration.)*

## Workflow

```
Messy raw export (CSV)  ->  Python cleaning (pandas)  ->  MySQL star schema  ->  SQL analysis  ->  Power BI dashboard  ->  Insights
```

### 1. Data cleaning (`notebooks/01_data_cleaning.ipynb`)

The raw export has 115,025 rows with duplicates, five date formats, inconsistent labels, text inside number columns, placeholders and typos. After cleaning, **113,434 rows remain**, and the result was reconciled against the source table with zero mismatching values.

| Issue found | Rows affected | Fix |
|---|---|---|
| Duplicate runs | 1,363 | Standardised `run_id`, kept the first record |
| Impossible or out-of-range dates | 55 | Dropped (cannot be trusted) |
| Unknown plant / machine keys | 173 | Dropped (no matching master record) |
| Planned time blank | 430 | Set to 480 (the shift length) |
| Negative scrap units | 220 | Sign corrected |
| Run time blank | 871 | Rebuilt as planned time minus downtime |
| Downtime inconsistent with run time | 214 | Recalculated from run time |
| Actual units 10x typo | 44 | Rebuilt as good plus scrap units |
| Good units blank or wrong | 910 | Rebuilt as actual minus scrap units |
| Unit cost blank | 572 | Looked up from the part master |
| Scrap/rework cost blank | 928 | Recalculated (scrap x unit cost x 0.45) |

Mixed text labels (plants, machines, parts, shifts, downtime reasons) and numbers stored as text (`"480 min"`, `"Rs. 1,400"`) were also standardised.

### 2. Database (`database/`)

A MySQL star schema: `fact_production_runs` (one row per machine, plant, shift and day) joined to `dim_date`, `dim_plants`, `dim_machines`, `dim_shifts` and `dim_parts`. Load it with `mysql -u root -p < database/Manufacturing_OEE_DB_Large.sql`.

### 3. SQL analysis (`sql/`)

- `01_validation_checks.sql`: row counts, orphan keys, duplicate grain, NULL checks and business-rule checks
- `02_kpi_views.sql`: reusable views with one consistent definition of each KPI
- `03_analysis_queries.sql`: 14 business questions using joins, CTEs and window functions (`RANK`, `LAG`, `ROW_NUMBER`)

### 4. Power BI (`dashboard/`)

A star-schema data model with DAX measures, three pages and synchronised slicers. The SQL and Power BI results were cross-checked and match.

## KPI definitions

- **Availability** = run minutes / planned minutes
- **Performance** = actual units / (planned units x run minutes / planned minutes)
- **Quality** = good units / actual units
- **OEE** = Availability x Performance x Quality (all calculated on summed values)
- **Cost of poor quality** = scrap and rework cost (scrap units x unit cost x 0.45)

## Repository structure

```
manufacturing-oee-analytics/
├── data/
│   ├── raw/                    messy production export
│   ├── cleaned/                cleaned output of the notebook
│   └── dim_*.csv, fact_production_runs.csv   master data and source table
├── database/                   MySQL dump
├── notebooks/                  cleaning and database-load notebooks
├── sql/                        validation, KPI views, analysis queries
├── scripts/                    dataset generators
├── dashboard/                  Power BI file, screenshots, PDF
└── docs/                       data dictionary
```

## How to reproduce

1. `pip install -r requirements.txt`
2. Run `notebooks/01_data_cleaning.ipynb` to clean the raw file.
3. Import `database/Manufacturing_OEE_DB_Large.sql` into MySQL 8, then load the cleaned file with `notebooks/02_load_to_mysql.ipynb` (add your own MySQL password).
4. Run the files in `sql/` in order.
5. Open `dashboard/manufacturing_oee_dashboard.pbix` in Power BI Desktop and point it at your MySQL server.

## Tools

Python (pandas, SQLAlchemy), MySQL 8, SQL (CTEs, window functions, views), Power BI (DAX, data modelling), Git and GitHub.
