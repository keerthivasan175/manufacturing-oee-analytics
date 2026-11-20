"""
Synthetic LARGE dataset for `manufacturing_oee_db` (same star schema as the template database).

Schema (unchanged from template):
  dim_date, dim_plants, dim_parts, dim_machines, dim_shifts  ->  fact_production_runs

What this script does
  * keeps the 4 template dimensions exactly as they are
  * extends dim_date to cover 2024-01-01 .. 2025-12-31
  * generates a realistic, full-grid fact table (every plant x machine x shift x working day)
  * writes a MySQL dump  (database/Manufacturing_OEE_DB_Large.sql)  and CSV files (data/)

All data is SIMULATED. Re-run:   python scripts/generate_oee_dataset.py
"""
import os
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

SEED = 2024
rng = np.random.default_rng(SEED)
random.seed(SEED)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_DIR = os.path.join(ROOT, "data")
DB_DIR = os.path.join(ROOT, "database")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

START, END = date(2024, 1, 1), date(2025, 12, 31)
PLANNED_MIN = 480

# ----------------------------------------------------------------------------
# Template dimensions (copied unchanged from the template database)
# ----------------------------------------------------------------------------
PLANTS_COLS = ['plant_id', 'plant_name', 'city', 'state', 'facility_type', 'monthly_capacity_units']
PLANTS_ROWS = [
    ('PLANT_CHN_01', 'Chennai Heavy Engineering Plant', 'Chennai', 'Tamil Nadu', 'Automotive Assembly', 25000),
    ('PLANT_CHN_02', 'Sriperumbudur Stamping & Press Plant', 'Sriperumbudur', 'Tamil Nadu', 'Metal Fabrication', 40000),
    ('PLANT_PUN_01', 'Pune Powertrain & Engine Plant', 'Pune', 'Maharashtra', 'Engine & Transmission', 18000),
    ('PLANT_BLR_01', 'Bengaluru Precision Components Hub', 'Bengaluru', 'Karnataka', 'Electronics & Sensors', 35000),
    ('PLANT_MDU_01', 'Madurai Fasteners & Forgings Unit', 'Madurai', 'Tamil Nadu', 'Forging & Fasteners', 30000),
    ('PLANT_CBE_01', 'Coimbatore Precision Hydraulics Plant', 'Coimbatore', 'Tamil Nadu', 'Pumps & Hydraulics', 22000),
    ('PLANT_MAN_01', 'Manesar Vehicle Assembly Line', 'Manesar', 'Haryana', 'Final Assembly', 28000),
]

PARTS_COLS = ['part_id', 'part_name', 'category', 'material', 'standard_unit_cost']
PARTS_ROWS = [
    ('PRT_001', 'Forged Connecting Rod', 'Engine Components', 'Alloy Steel', 450),
    ('PRT_002', 'Cast Iron Cylinder Block', 'Engine Components', 'Cast Iron', 4200),
    ('PRT_003', 'Aluminium Cylinder Head', 'Engine Components', 'Aluminium Alloy', 3100),
    ('PRT_004', 'Automotive Crankshaft (4-Cylinder)', 'Powertrain', 'Forged Steel', 5400),
    ('PRT_005', 'High-Tensile Camshaft', 'Powertrain', 'Chilled Cast Iron', 1850),
    ('PRT_006', 'Precision Spur Gear (Transmission)', 'Transmission', 'Case-Hardened Steel', 820),
    ('PRT_007', 'Helical Pinion Shaft', 'Transmission', 'Alloy Steel', 1250),
    ('PRT_008', 'Heavy-Duty Clutch Pressure Plate', 'Transmission', 'Ductile Iron', 2100),
    ('PRT_009', 'Ventilated Brake Disc Rotor', 'Braking System', 'Grey Cast Iron', 950),
    ('PRT_010', 'Brake Caliper Housing Unit', 'Braking System', 'Aluminium Alloy', 1400),
    ('PRT_011', 'Front Suspension Lower Control Arm', 'Chassis & Suspension', 'Forged Steel', 1650),
    ('PRT_012', 'Rack and Pinion Steering Gearbox', 'Steering System', 'Cast Steel', 3800),
    ('PRT_013', 'High-Pressure Common Rail Injector', 'Fuel System', 'Special Alloy', 4900),
    ('PRT_014', 'Exhaust Manifold with Catalytic Flange', 'Exhaust System', 'Stainless Steel', 2300),
    ('PRT_015', 'Precision Hydraulic Valve Body', 'Hydraulics', 'Aluminium Alloy', 1750),
]

MACHINES_COLS = ['machine_id', 'machine_name', 'operation_type', 'line_allocation', 'installation_year', 'rated_availability_pct']
MACHINES_ROWS = [
    ('MCH_CNC_01', 'Makino 5-Axis VMC Milling Center', 'Milling', 'CNC Milling Line 1', 2019, 98.5),
    ('MCH_CNC_02', 'Doosan High-Torque CNC Lathe', 'Turning', 'CNC Lathe Line 1', 2021, 99.0),
    ('MCH_CNC_03', 'Mazak Precision Horizontal Machining Center', 'HMC', 'CNC Milling Line 2', 2022, 99.2),
    ('MCH_PRS_01', 'Schuler 1000T Mechanical Stamping Press', 'Stamping', 'Press Shop Line A', 2018, 97.0),
    ('MCH_PRS_02', 'Komatsu 600T Hydraulic Forming Press', 'Stamping', 'Press Shop Line B', 2020, 98.0),
    ('MCH_FRG_01', 'SMS 2500T Closed-Die Forging Hammer', 'Forging', 'Forging Cell 1', 2017, 96.5),
    ('MCH_CST_01', 'Buhler High-Pressure Die Casting 800T', 'Die Casting', 'Foundry Cell 1', 2021, 97.8),
    ('MCH_GRN_01', 'Studer Precision Cylindrical Grinder', 'Grinding', 'Finishing Line 1', 2022, 99.5),
    ('MCH_ROB_01', 'ABB 6-Axis Robotic Arc Welding Cell', 'Welding', 'Robotic Assembly Line', 2023, 99.1),
    ('MCH_HTR_01', 'Aichelin Continuous Induction Heat Treatment', 'Heat Treatment', 'Thermal Cell 1', 2019, 97.5),
]

SHIFTS_COLS = ['shift_id', 'shift_name', 'start_time', 'end_time', 'shift_duration_minutes', 'shift_lead']
SHIFTS_ROWS = [
    ('SHF_01', 'Shift 1 (Morning)', '06:00:00', '14:00:00', 480, 'Thirumalai / Supervisor A'),
    ('SHF_02', 'Shift 2 (Evening)', '14:00:00', '22:00:00', 480, 'Karthik / Supervisor B'),
    ('SHF_03', 'Shift 3 (Night)', '22:00:00', '06:00:00', 480, 'Selvaraj / Supervisor C'),
]


# ----------------------------------------------------------------------------
# Business rules used by the simulation
# ----------------------------------------------------------------------------
machines = {r[0]: dict(op=r[2], year=r[4], rated=float(r[5])) for r in MACHINES_ROWS}
parts = {r[0]: dict(cat=r[2], cost=int(r[4])) for r in PARTS_ROWS}
plant_ids = [r[0] for r in PLANTS_ROWS]
machine_ids = [r[0] for r in MACHINES_ROWS]

# which parts each machine type can realistically make
ALLOWED = {
    "MCH_CNC_01": ["PRT_002", "PRT_003", "PRT_010", "PRT_015"],
    "MCH_CNC_02": ["PRT_004", "PRT_005", "PRT_006", "PRT_007", "PRT_013"],
    "MCH_CNC_03": ["PRT_002", "PRT_003", "PRT_012", "PRT_015"],
    "MCH_PRS_01": ["PRT_008", "PRT_011", "PRT_014"],
    "MCH_PRS_02": ["PRT_008", "PRT_011", "PRT_014"],
    "MCH_FRG_01": ["PRT_001", "PRT_004", "PRT_007", "PRT_011"],
    "MCH_CST_01": ["PRT_002", "PRT_003", "PRT_009", "PRT_010", "PRT_015"],
    "MCH_GRN_01": ["PRT_004", "PRT_005", "PRT_006", "PRT_007", "PRT_009", "PRT_013"],
    "MCH_ROB_01": ["PRT_011", "PRT_012", "PRT_014"],
    "MCH_HTR_01": ["PRT_001", "PRT_004", "PRT_005", "PRT_006", "PRT_007"],
}
# planned output per minute by part (heavy parts are slow, small parts fast)
BASE_RATE = {"PRT_001": 1.15, "PRT_006": 1.16, "PRT_009": 1.11,
             "PRT_005": .49, "PRT_007": .49, "PRT_008": .48, "PRT_010": .49, "PRT_011": .50,
             "PRT_014": .50, "PRT_015": .49,
             "PRT_002": .22, "PRT_003": .22, "PRT_004": .22, "PRT_012": .22, "PRT_013": .22}
MFAC = {m: round(float(rng.uniform(.95, 1.07)), 3) for m in machine_ids}

# each plant leans towards the part families of its facility type
AFFINITY = {
    "PLANT_CHN_01": {},
    "PLANT_CHN_02": {"Chassis & Suspension": 2.0, "Transmission": 1.5, "Exhaust System": 2.0},
    "PLANT_PUN_01": {"Engine Components": 2.0, "Powertrain": 2.0, "Transmission": 2.0},
    "PLANT_BLR_01": {"Fuel System": 2.5, "Hydraulics": 2.5, "Steering System": 2.0},
    "PLANT_MDU_01": {"Powertrain": 2.0, "Chassis & Suspension": 2.0, "Engine Components": 1.5},
    "PLANT_CBE_01": {"Hydraulics": 2.5, "Steering System": 2.5, "Braking System": 2.0},
    "PLANT_MAN_01": {"Braking System": 1.8, "Steering System": 1.8, "Exhaust System": 1.8, "Chassis & Suspension": 1.8},
}
PART_CHOICES = {}
for p in plant_ids:
    for m in machine_ids:
        opts = ALLOWED[m]
        PART_CHOICES[(p, m)] = (opts, [AFFINITY[p].get(parts[x]["cat"], 1.0) for x in opts])

OP_TB = {"Milling": 1.6, "Turning": 1.5, "HMC": 1.4, "Grinding": 1.3, "Stamping": .6,
         "Forging": .8, "Die Casting": .7, "Welding": .5, "Heat Treatment": .4}
OP_HL = {"Stamping": 2.0, "Forging": 2.0, "Die Casting": 1.8, "Heat Treatment": .5, "Milling": .5,
         "Turning": .4, "HMC": .5, "Grinding": .4, "Welding": .3}
OP_SCRAP = {"Die Casting": .040, "Forging": .032, "Welding": .020, "Heat Treatment": .030,
            "Milling": .022, "Turning": .019, "HMC": .019, "Stamping": .026, "Grinding": .013}
SHIFT_DOWN = {1: .90, 2: 1.00, 3: 1.25}
SHIFT_SCRAP = {1: .90, 2: 1.00, 3: 1.30}
PART_DIFFICULTY = {"PRT_002": 1.15, "PRT_003": 1.20, "PRT_004": 1.20, "PRT_013": 1.40, "PRT_012": 1.10}
CONTINUOUS = {"MCH_HTR_01", "MCH_CST_01"}      # furnace / foundry cells that also run on Sundays

HOLIDAYS = {
    date(2024, 1, 15), date(2024, 1, 16), date(2024, 1, 26), date(2024, 4, 14), date(2024, 5, 1),
    date(2024, 8, 15), date(2024, 10, 2), date(2024, 10, 11), date(2024, 10, 12), date(2024, 10, 31),
    date(2024, 11, 1), date(2024, 12, 25),
    date(2025, 1, 14), date(2025, 1, 15), date(2025, 1, 16), date(2025, 1, 26), date(2025, 4, 14),
    date(2025, 5, 1), date(2025, 8, 15), date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 20),
    date(2025, 10, 21), date(2025, 12, 25),
}
MS_EVENTS = [  # supply-chain disruptions: (plant, from, to, multiplier on Material Shortage)
    ("PLANT_PUN_01", date(2024, 8, 12), date(2024, 9, 20), 4.0),
    ("PLANT_BLR_01", date(2025, 2, 3), date(2025, 3, 14), 3.0),
]
TOTAL_DAYS = (END - START).days


def plant_factor(plant, t):
    if plant == "PLANT_CHN_02":
        return .70                       # best-run plant
    if plant == "PLANT_MDU_01":
        return 1.30                      # old forging unit: struggles
    if plant == "PLANT_PUN_01":
        return 1.10
    if plant == "PLANT_MAN_01":
        return 1.90 - 1.00 * t           # new line: ramp-up, improves a lot over two years
    return 1.0


def plant_perf(plant, t):
    if plant == "PLANT_CHN_02":
        return .02
    if plant == "PLANT_MDU_01":
        return -.02
    if plant == "PLANT_MAN_01":
        return -.07 * (1 - t)
    return 0.0


# ----------------------------------------------------------------------------
# Simulate fact_production_runs
# ----------------------------------------------------------------------------
all_days = [START + timedelta(n) for n in range(TOTAL_DAYS + 1)]
next_pm = {(p, m): START + timedelta(int(rng.integers(3, 22))) for p in plant_ids for m in machine_ids}
pm_shift = {(p, m): int(rng.integers(1, 3)) for p in plant_ids for m in machine_ids}
last_part = {}
rows = []

for d in all_days:
    t = (d - START).days / TOTAL_DAYS
    is_sun, is_hol, is_sat = d.weekday() == 6, d in HOLIDAYS, d.weekday() == 5
    hot = 1.40 if d.month in (4, 5, 6) else 1.0
    gi = 1 - .08 * t                  # continuous-improvement programme
    for p in plant_ids:
        pf = plant_factor(p, t)
        pperf = plant_perf(p, t)
        ms_mult = 1.0
        for ep, a, b, mult in MS_EVENTS:
            if ep == p and a <= d <= b:
                ms_mult = mult
        for m in machine_ids:
            info = machines[m]
            op = info["op"]
            if is_sun or is_hol:
                if m not in CONTINUOUS:
                    continue
                run_shifts = [s for s in (1, 2) if rng.random() < (.30 if is_sun else .15)]
            else:
                probs = {1: .97, 2: .94, 3: .50 if is_sat else .80}
                run_shifts = [s for s in (1, 2, 3) if rng.random() < probs[s]]
            age = 2025 - info["year"]
            agef = 1 + .06 * (age - 4)
            drift = 1 + 1.2 * t if m == "MCH_PRS_01" else 1.0       # ageing press: wear builds up
            for s in run_shifts:
                # ---- part & changeover ----
                prev = last_part.get((p, m))
                if prev is None or rng.random() > .85:
                    opts, w = PART_CHOICES[(p, m)]
                    part = random.choices(opts, w)[0]
                else:
                    part = prev
                changed = prev is not None and part != prev
                last_part[(p, m)] = part

                # ---- downtime ----
                shf = SHIFT_DOWN[s]
                p_tb = .075 * gi * OP_TB[op] * agef * shf * pf * drift
                p_hl = .075 * gi * OP_HL[op] * agef * hot * pf * drift * (shf ** .5)
                p_ms = .075 * gi * pf * ms_mult * (1.2 if p == "PLANT_BLR_01" else 1.0)
                pm_due = d >= next_pm[(p, m)] and s == pm_shift[(p, m)]
                u = rng.random()
                if pm_due:
                    reason, dur = "Scheduled Maintenance", int(rng.integers(45, 121))
                    next_pm[(p, m)] = d + timedelta(int(rng.integers(18, 27)))
                elif u < p_tb:
                    reason = "Tool Breakage"
                    dur = int(rng.integers(120, 301)) if rng.random() < .004 else int(rng.integers(20, 121))
                elif u < p_tb + p_hl:
                    reason = "Hydraulic Leak"
                    dur = int(rng.integers(120, 301)) if rng.random() < .004 else int(rng.integers(20, 121))
                elif u < p_tb + p_hl + p_ms:
                    reason, dur = "Material Shortage", int(rng.integers(20, 111))
                elif not changed and rng.random() < .055 * (1.15 if age <= 3 else .9):
                    reason, dur = "None", 0
                else:
                    reason = "Operator Adjustment"
                    dur = int(np.clip(rng.lognormal(np.log(15) - .245, .7), 1, 75))
                    if changed:
                        dur += int(rng.integers(12, 35))
                down = min(dur, 400)
                run = PLANNED_MIN - down

                # ---- output ----
                planned_units = max(1, int(round(PLANNED_MIN * BASE_RATE[part] * MFAC[m] * rng.lognormal(0, .08))))
                perf = float(np.clip(rng.normal(.935 + pperf, .045), .78, 1.05))
                perf *= (.965 if s == 3 else 1.0) * (1 - .006 * (age - 4))
                actual = max(1, int(round(planned_units * run / PLANNED_MIN * perf)))

                # ---- quality ----
                rate = (OP_SCRAP[op] * SHIFT_SCRAP[s] * PART_DIFFICULTY.get(part, 1.0)
                        * (1.25 if changed else 1.0) * (agef ** .5) * (pf ** .6) * rng.lognormal(0, .35))
                scrap = int(rng.binomial(actual, min(rate, .12)))
                good = actual - scrap
                unit_cost = parts[part]["cost"]
                rows.append((d, p, m, f"SHF_0{s}", part, PLANNED_MIN, run, down, reason,
                             planned_units, actual, good, scrap, unit_cost,
                             int(scrap * unit_cost * .45)))

cols = ["date_id", "plant_id", "machine_id", "shift_id", "part_id", "planned_time_minutes",
        "actual_run_minutes", "downtime_minutes", "downtime_reason", "planned_units",
        "actual_units_produced", "good_units", "scrap_units", "unit_cost", "scrap_rework_cost"]
fact = pd.DataFrame(rows, columns=cols)
fact.insert(0, "run_id", [f"RUN{10001 + i:06d}" for i in range(len(fact))])
fact["date_id"] = fact["date_id"].astype(str)

# integrity checks
assert not fact.duplicated(["date_id", "plant_id", "machine_id", "shift_id"]).any()
assert (fact.actual_run_minutes == fact.planned_time_minutes - fact.downtime_minutes).all()
assert (fact.good_units + fact.scrap_units == fact.actual_units_produced).all()

# ----------------------------------------------------------------------------
# dim_date (extended)
# ----------------------------------------------------------------------------
date_rows = []
for d in all_days:
    date_rows.append((str(d), d.strftime("%A"), d.strftime("%B"), d.month, f"Q{(d.month - 1) // 3 + 1}",
                      d.year, 1 if d.weekday() >= 5 else 0))
dim_date = pd.DataFrame(date_rows, columns=["date_id", "day_name", "month_name", "month_no",
                                            "quarter", "year", "is_weekend"])

dims = {
    "dim_date": dim_date,
    "dim_plants": pd.DataFrame(PLANTS_ROWS, columns=PLANTS_COLS),
    "dim_parts": pd.DataFrame(PARTS_ROWS, columns=PARTS_COLS),
    "dim_machines": pd.DataFrame(MACHINES_ROWS, columns=MACHINES_COLS),
    "dim_shifts": pd.DataFrame(SHIFTS_ROWS, columns=SHIFTS_COLS),
}
for name, df in dims.items():
    df.to_csv(os.path.join(DATA_DIR, f"{name}.csv"), index=False)
fact.to_csv(os.path.join(DATA_DIR, "fact_production_runs.csv"), index=False)

# ----------------------------------------------------------------------------
# MySQL dump (same layout as the template)
# ----------------------------------------------------------------------------
HEADER = """-- MySQL dump 10.13  Distrib 8.0.33, for Win64 (x86_64)
-- Host: localhost    Database: manufacturing_oee_db
-- SYNTHETIC LARGE DATASET generated by scripts/generate_oee_dataset.py (same schema as the template)
-- ------------------------------------------------------
-- Server version	8.0.33

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

CREATE DATABASE IF NOT EXISTS `manufacturing_oee_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `manufacturing_oee_db`;

"""

FOOTER = """/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-01 18:35:00"""

DDL = {
    "dim_date": """CREATE TABLE `dim_date` (
  `date_id` date NOT NULL,
  `day_name` varchar(15) NOT NULL,
  `month_name` varchar(15) NOT NULL,
  `month_no` int NOT NULL,
  `quarter` varchar(5) NOT NULL,
  `year` int NOT NULL,
  `is_weekend` tinyint(1) NOT NULL,
  PRIMARY KEY (`date_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
    "dim_plants": """CREATE TABLE `dim_plants` (
  `plant_id` varchar(20) NOT NULL,
  `plant_name` varchar(100) NOT NULL,
  `city` varchar(50) NOT NULL,
  `state` varchar(50) NOT NULL,
  `facility_type` varchar(50) NOT NULL,
  `monthly_capacity_units` int NOT NULL,
  PRIMARY KEY (`plant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
    "dim_parts": """CREATE TABLE `dim_parts` (
  `part_id` varchar(15) NOT NULL,
  `part_name` varchar(150) NOT NULL,
  `category` varchar(50) NOT NULL,
  `material` varchar(50) NOT NULL,
  `standard_unit_cost` int NOT NULL,
  PRIMARY KEY (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
    "dim_machines": """CREATE TABLE `dim_machines` (
  `machine_id` varchar(20) NOT NULL,
  `machine_name` varchar(100) NOT NULL,
  `operation_type` varchar(50) NOT NULL,
  `line_allocation` varchar(50) NOT NULL,
  `installation_year` int NOT NULL,
  `rated_availability_pct` decimal(4,1) NOT NULL,
  PRIMARY KEY (`machine_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
    "dim_shifts": """CREATE TABLE `dim_shifts` (
  `shift_id` varchar(10) NOT NULL,
  `shift_name` varchar(50) NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `shift_duration_minutes` int NOT NULL,
  `shift_lead` varchar(100) NOT NULL,
  PRIMARY KEY (`shift_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
    "fact_production_runs": """CREATE TABLE `fact_production_runs` (
  `run_id` varchar(20) NOT NULL,
  `date_id` date NOT NULL,
  `plant_id` varchar(20) NOT NULL,
  `machine_id` varchar(20) NOT NULL,
  `shift_id` varchar(10) NOT NULL,
  `part_id` varchar(15) NOT NULL,
  `planned_time_minutes` int NOT NULL,
  `actual_run_minutes` int NOT NULL,
  `downtime_minutes` int NOT NULL,
  `downtime_reason` varchar(100) DEFAULT NULL,
  `planned_units` int NOT NULL,
  `actual_units_produced` int NOT NULL,
  `good_units` int NOT NULL,
  `scrap_units` int NOT NULL,
  `unit_cost` int NOT NULL,
  `scrap_rework_cost` int NOT NULL,
  PRIMARY KEY (`run_id`),
  KEY `fk_date` (`date_id`),
  KEY `fk_plant` (`plant_id`),
  KEY `fk_machine` (`machine_id`),
  KEY `fk_shift` (`shift_id`),
  KEY `fk_part` (`part_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;""",
}



def q(v):
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return str(int(v)) if float(v).is_integer() and not isinstance(v, float) else repr(v)


def inserts(table, records, chunk=1000):
    out = []
    for i in range(0, len(records), chunk):
        vals = ",".join("(" + ",".join(q(v) for v in r) + ")" for r in records[i:i + chunk])
        out.append(f"INSERT INTO `{table}` VALUES {vals};")
    return "\n".join(out)


def block(table, records):
    return f"""--
-- Table structure for table `{table}`
--

DROP TABLE IF EXISTS `{table}`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
{DDL[table]}
/*!40101 SET character_set_client = @saved_cs_client */;

LOCK TABLES `{table}` WRITE;
/*!40000 ALTER TABLE `{table}` DISABLE KEYS */;
{inserts(table, records)}
/*!40000 ALTER TABLE `{table}` ENABLE KEYS */;
UNLOCK TABLES;

"""


with open(os.path.join(DB_DIR, "Manufacturing_OEE_DB_Large.sql"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write(HEADER)
    for name in ["dim_date", "dim_plants", "dim_parts", "dim_machines", "dim_shifts"]:
        fh.write(block(name, [tuple(r) for r in dims[name].itertuples(index=False, name=None)]))
    fh.write(block("fact_production_runs", [tuple(r) for r in fact.itertuples(index=False, name=None)]))
    fh.write(FOOTER)

print(f"fact_production_runs: {len(fact):,} rows | dim_date: {len(dim_date)} rows")
print(f"date range: {fact.date_id.min()} to {fact.date_id.max()}")
