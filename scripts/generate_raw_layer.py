"""
Creates a realistic MESSY raw export of fact_production_runs (what an MES / shift-report
system would hand to an analyst), starting from the clean fact table.

    python scripts/generate_raw_layer.py      ->  data/raw/fact_production_runs_raw.csv

The raw file is built so that every problem can be fixed from business rules
(or the row is clearly unusable and must be dropped), so the cleaned result can be
reconciled against data/fact_production_runs.csv.
"""
import os

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT_DIR = os.path.join(ROOT, "data", "raw")
os.makedirs(OUT_DIR, exist_ok=True)

src = pd.read_csv(os.path.join(ROOT, "data", "fact_production_runs.csv"))
n0 = len(src)

# ---------------------------------------------------------------- duplicates
dup = rng.choice(n0, int(.012 * n0), replace=False)
adjacent, tail = dup[: len(dup) // 2], dup[len(dup) // 2:]
df = pd.concat([src, src.iloc[adjacent]]).sort_index(kind="stable")   # copy sits next to original
df = pd.concat([df, src.iloc[tail]]).reset_index(drop=True)           # re-sent batch at the end
n = len(df)
dates = pd.to_datetime(df["date_id"])


def apply_variants(series, funcs, probs):
    idx = rng.choice(len(funcs), size=len(series), p=probs)
    return pd.Series([funcs[i](v) for i, v in zip(idx, series)], index=series.index)


ident = lambda x: x
lower = lambda x: x.lower()
pad = lambda x: f" {x} "
hyph = lambda x: x.replace("_", "-")
title = lambda x: x.title()

# ---------------------------------------------------------------- identifiers
run_id = apply_variants(df.run_id, [ident, lower, pad, lambda x: x[:3] + "-" + x[3:]], [.94, .02, .02, .02])
plant = apply_variants(df.plant_id, [ident, lower, pad, hyph, title], [.80, .05, .06, .05, .04])
machine = apply_variants(df.machine_id, [ident, lower, pad, hyph, title], [.80, .05, .06, .05, .04])
part = apply_variants(df.part_id, [ident, lower, lambda x: x.replace("_", ""), hyph, pad], [.78, .05, .06, .05, .06])

SHIFT_NAMES = {1: "Morning", 2: "Evening", 3: "Night"}
shift_no = df.shift_id.str[-1].astype(int)
shift_funcs = [lambda n: f"SHF_0{n}", lambda n: f"shf_0{n}", lambda n: f"Shift {n}", lambda n: f"S{n}",
               lambda n: str(n), lambda n: SHIFT_NAMES[n]]
shift = apply_variants(shift_no, shift_funcs, [.72, .04, .10, .05, .05, .04])

# keys that do not exist in the master data (must be dropped)
bad_plant = rng.random(n) < .001
bad_machine = rng.random(n) < .0005
plant = plant.where(~bad_plant, "PLANT_XYZ_09")
machine = machine.where(~bad_machine, "MCH_XXX_99")

# ---------------------------------------------------------------- dates
DATE_FMTS = ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d %b %Y", "%d-%b-%y"]
fmt_idx = rng.choice(len(DATE_FMTS), size=n, p=[.55, .28, .10, .04, .03])
date_str = pd.Series("", index=df.index, dtype=object)
for i, f in enumerate(DATE_FMTS):
    m = fmt_idx == i
    date_str[m] = dates[m].dt.strftime(f)
bad_dates = rng.choice(n, 30, replace=False)                      # impossible dates
date_str.iloc[bad_dates] = "31-02-2024"
far = rng.choice(np.setdiff1d(np.arange(n), bad_dates), 25, replace=False)   # year typos
date_str.iloc[far] = [f"{d.day:02d}-{d.month:02d}-{y}" for d, y in
                      zip(dates.iloc[far], rng.choice([2023, 2026, 2042], 25))]

# ---------------------------------------------------------------- downtime reason
REASONS = {
    "Operator Adjustment": ["Operator Adjustment", "operator adjustment", "Operator Adj.", "OP ADJUSTMENT", "Operator adjust"],
    "Tool Breakage": ["Tool Breakage", "tool breakage", "Tool Break", "TOOL BREAKAGE", "Tool Broken"],
    "Hydraulic Leak": ["Hydraulic Leak", "hydraulic leak", "Hyd Leak", "Hydraulic leakage", "HYDRAULIC LEAK"],
    "Material Shortage": ["Material Shortage", "material shortage", "Mat. Shortage", "No Material", "MATERIAL SHORTAGE"],
    "Scheduled Maintenance": ["Scheduled Maintenance", "scheduled maintenance", "Sched. Maint.", "PM", "SCHEDULED MAINTENANCE"],
    "None": ["None", "none", "NIL", "-", "", "N/A"],
}
REASON_P = {"None": [.55, .10, .10, .10, .10, .05]}
reason = df.downtime_reason.copy()
for canon, variants in REASONS.items():
    m = df.downtime_reason == canon
    p = REASON_P.get(canon, [.65] + [.35 / (len(variants) - 1)] * (len(variants) - 1))
    reason[m] = apply_variants(df.downtime_reason[m], [lambda x, v=v: v for v in variants], p)

# ---------------------------------------------------------------- numeric columns + injected errors
num = df[["planned_time_minutes", "actual_run_minutes", "downtime_minutes", "planned_units",
          "actual_units_produced", "good_units", "scrap_units", "unit_cost", "scrap_rework_cost"]].astype(float).copy()
cats = ["ok", "run_blank", "good_blank", "cost_blank", "unitcost_blank", "planned_blank",
        "scrap_neg", "actual_x10", "good_x10", "down_typo"]
p_issue = np.array([0, .008, .008, .008, .005, .004, .002, .0004, .0004, .002])
p_issue[0] = 1 - p_issue.sum()
issue = pd.Series(np.array(cats)[rng.choice(len(cats), size=n, p=p_issue)], index=df.index)
issue[(issue == "scrap_neg") & (num.scrap_units == 0)] = "ok"

num.loc[issue == "run_blank", "actual_run_minutes"] = np.nan
num.loc[issue == "good_blank", "good_units"] = np.nan
num.loc[issue == "cost_blank", "scrap_rework_cost"] = np.nan
num.loc[issue == "unitcost_blank", "unit_cost"] = np.nan
num.loc[issue == "planned_blank", "planned_time_minutes"] = np.nan
num.loc[issue == "scrap_neg", "scrap_units"] *= -1
num.loc[issue == "actual_x10", "actual_units_produced"] *= 10
num.loc[issue == "good_x10", "good_units"] *= 10
t = issue == "down_typo"
num.loc[t, "downtime_minutes"] = np.minimum(num.loc[t, "downtime_minutes"] + rng.integers(10, 200, t.sum()), 470)

PLACEHOLDERS = ["", "N/A", "NA", "null", "-"]
PH_P = [.40, .20, .15, .15, .10]


def fmt(col, kind):
    out = []
    for v in num[col]:
        if np.isnan(v):
            out.append(PLACEHOLDERS[rng.choice(5, p=PH_P)])
            continue
        r = rng.random()
        i = int(v)
        if kind == "minutes":
            out.append(str(i) if r < .93 else f"{i}.0" if r < .96 else f"{i} min")
        elif kind == "planned":
            out.append(str(i) if r < .90 else f"{i}.0" if r < .93 else f"{i} min" if r < .96
                       else "8 hrs" if r < .98 else str(i))
        elif kind == "units":
            out.append(str(i) if r < .95 else f"{i}.0")
        else:  # cost
            out.append(str(i) if r < .90 else f"{i:,}" if r < .94 else f"Rs. {i:,}" if r < .97 else f"{i}.0")
    return pd.Series(out, index=df.index)


# ---------------------------------------------------------------- junk columns
remarks = pd.Series("", index=df.index, dtype=object)
rm = rng.random(n) < .04
remarks[rm] = rng.choice(["tool changed", "power dip", "trial run", "audit day", "new operator", "wait for spares"], rm.sum())
operator = pd.Series([f"OP-{x}" for x in rng.integers(1001, 1181, n)], index=df.index)
operator[rng.random(n) < .06] = ""
iso = dates.dt.isocalendar()
batch = "MES-" + iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)

raw = pd.DataFrame({
    "Run ID": run_id, "Date": date_str, "Plant": plant, "Machine": machine, "Shift": shift, "Part": part,
    "Operator": operator,
    "Planned Time (min)": fmt("planned_time_minutes", "planned"),
    "Run Time (min)": fmt("actual_run_minutes", "minutes"),
    "Downtime (min)": fmt("downtime_minutes", "minutes"),
    "Downtime Reason": reason,
    "Planned Units": fmt("planned_units", "units"),
    "Actual Units": fmt("actual_units_produced", "units"),
    "Good Units": fmt("good_units", "units"),
    "Scrap Units": [str(int(v)) if not np.isnan(v) else "" for v in num.scrap_units],
    "Unit Cost (INR)": fmt("unit_cost", "cost"),
    "Scrap/Rework Cost (INR)": fmt("scrap_rework_cost", "cost"),
    "Remarks": remarks, "Export Batch": batch,
})
raw.to_csv(os.path.join(OUT_DIR, "fact_production_runs_raw.csv"), index=False, encoding="utf-8")
print(f"raw rows: {len(raw):,}  (clean source rows: {n0:,}, duplicated rows added: {n - n0:,})")
