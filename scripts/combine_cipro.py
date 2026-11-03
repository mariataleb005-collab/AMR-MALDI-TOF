"""
One comparison table for Ciprofloxacin: Experiment 1 (input representations)
+ PSO experiments (Original PSO, Baseline and component variants).
Each row = feature set x model, mean ± SD over 5 CV folds.

Usage:  python combine_cipro.py
        python combine_cipro.py --exp1 exp1_Ciprofloxacin.csv \
            --pso PSO_Original_experiment_results.csv PSO_Gradual_experiment_results.csv
Outputs (overwritten each run):
  cipro_combined.xlsx           styled workbook (Report table / Numeric)
  cipro_combined_report.csv
"""
import argparse
import os
import sys

import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]          # repository root
OUT_DIR = ROOT / "results" / "combined"             # where summary tables are saved
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ap = argparse.ArgumentParser()
ap.add_argument("--exp1", default=str(ROOT / "results" / "exp1" / "exp1_Ciprofloxacin.csv"))
ap.add_argument("--pso", nargs="*", default=[str(ROOT / "results" / "exp2_pso" / f) for f in
                                             ("PSO_Original_experiment_results.csv",
                                              "PSO_Gradual_experiment_results.csv",
                                              "pso_Ciprofloxacin.csv")])
ap.add_argument("--antibiotic", default="Ciprofloxacin")
ap.add_argument("--full-name", default="All 4 enhancements",
                help="variant name given to a PSO file without a 'variant' column")
args = ap.parse_args()

def load_pso(path, full_name):
    """Read a PSO result CSV in either format.
    New format: variant / search_seconds columns.
    Old (Exp.1-style) format: representation / prep_seconds -> renamed."""
    d = pd.read_csv(path)
    if "variant" not in d.columns:
        d["variant"] = full_name
        d["kind"] = "full"
        d = d.drop(columns=["representation"], errors="ignore")
    if "search_seconds" not in d.columns and "prep_seconds" in d.columns:
        d = d.rename(columns={"prep_seconds": "search_seconds"})
    return d


for p in [args.exp1] + args.pso:
    if not os.path.exists(p):
        sys.exit(f"File not found: {p}")

metrics = ["auroc", "auprc", "mcc", "bal_acc"]
METRIC_LABEL = {"auroc": "AUROC", "auprc": "AUPRC", "mcc": "MCC",
                "bal_acc": "Balanced Acc."}
MODEL_LABEL = {"lr": "LR", "svm": "SVM", "xgb": "XGBoost"}
REP_LABEL = {"raw": "Raw (all features)", "kernel_linear": "Kernel (linear)",
             "kernel_rbf": "Kernel (RBF)", "var500": "Variance top-500",
             "var1000": "Variance top-1000", "var2000": "Variance top-2000"}
EXP1_NAME = "Exp. 1: Input representation"
PSO_NAME = "PSO feature selection"

# ---------------------------------------------------------------- load
e1 = pd.read_csv(args.exp1)
e1 = e1[e1["antibiotic"] == args.antibiotic].copy()
e1["experiment"] = EXP1_NAME
e1["feature_set"] = e1["representation"].map(REP_LABEL).fillna(e1["representation"])
e1["select_seconds"] = e1["prep_seconds"]

pso = pd.concat([load_pso(p, args.full_name) for p in args.pso], ignore_index=True)
pso = pso[pso["antibiotic"] == args.antibiotic].copy()
pso["experiment"] = PSO_NAME
pso["feature_set"] = pso["variant"]
pso["select_seconds"] = pso["search_seconds"]

OUT_DIR.mkdir(parents=True, exist_ok=True)

cols = ["experiment", "feature_set", "model", "fold"] + metrics + \
       ["n_features", "fit_seconds", "select_seconds"]
df = pd.concat([e1[cols], pso[cols]], ignore_index=True)
os.chdir(OUT_DIR)                                   # outputs go to results/combined
if df.empty:
    sys.exit(f"No rows for {args.antibiotic}")
print(f"Rows: Exp. 1 = {len(e1)}, PSO = {len(pso)}")

order = list(dict.fromkeys(df["feature_set"]))
df["feature_set"] = pd.Categorical(df["feature_set"], order, ordered=True)
df["model"] = pd.Categorical(df["model"], ["lr", "svm", "xgb"], ordered=True)

# ---------------------------------------------------------------- summary
keys = ["experiment", "feature_set", "model"]
g = df.groupby(keys, observed=True, sort=False)
s = g[metrics].agg(["mean", "std"])
s.columns = [f"{m}_{k}" for m, k in s.columns]
nf = g["n_features"].agg(["mean", "std"]).set_axis(["n_features_mean", "n_features_std"], axis=1)
s = s.join(nf).join(g[["fit_seconds", "select_seconds"]].mean())
s["n_folds"] = g.size()
s = s.reset_index()
s["feature_set"] = s["feature_set"].astype(str)
s["model"] = s["model"].astype(str)
s = s.sort_values(["feature_set", "model"],
                  key=lambda c: c.map({v: i for i, v in enumerate(order)})
                  if c.name == "feature_set" else c.map({"lr": 0, "svm": 1, "xgb": 2})
                  ).reset_index(drop=True)

# duplicates: Kernel (RBF) + model identical to Raw + same model
s["duplicate"] = False
for i, r in s.iterrows():
    if r.feature_set == REP_LABEL["raw"]:
        continue
    raw = s[(s.feature_set == REP_LABEL["raw"]) & (s.model == r.model)]
    if len(raw) and all(abs(raw.iloc[0][f"{m}_mean"] - r[f"{m}_mean"]) < 1e-9
                        for m in ("mcc", "bal_acc")) \
            and abs(raw.iloc[0]["auroc_mean"] - r["auroc_mean"]) < 1e-4:
        s.at[i, "duplicate"] = True

valid = s[~s.duplicate]
best_row = valid["auprc_mean"].idxmax()
best_in_exp = {valid[valid.experiment == e]["auprc_mean"].idxmax()
               for e in valid.experiment.unique()} - {best_row}
best_cell = {(valid[f"{m}_mean"].idxmax(), m) for m in metrics}

# ---------------------------------------------------------------- tables
def pm(mean, sd, fmt="{:.3f}"):
    return mean.map(fmt.format) + " ± " + sd.fillna(0).map(fmt.format)

report = pd.DataFrame({"Experiment": s["experiment"],
                       "Feature set": s["feature_set"],
                       "Model": s["model"].map(MODEL_LABEL)})
for m in metrics:
    report[METRIC_LABEL[m]] = pm(s[f"{m}_mean"], s[f"{m}_std"])
report["Features"] = [f"{a:.0f}" if (pd.isna(b) or b < 0.5) else f"{a:.0f} ± {b:.0f}"
                      for a, b in zip(s["n_features_mean"], s["n_features_std"])]
report["Fit time (s)"] = s["fit_seconds"].round(1)
report["Selection time (s)"] = s["select_seconds"].round(1)

numeric = s.drop(columns="duplicate").round(4)
report.to_csv("cipro_combined_report.csv", index=False, encoding="utf-8-sig")

XLSX = "cipro_combined.xlsx"
try:
    with pd.ExcelWriter(XLSX) as xw:
        report.to_excel(xw, sheet_name="Report table", index=False)
        numeric.to_excel(xw, sheet_name="Numeric", index=False)
except PermissionError:
    sys.exit(f"\nCould not write {XLSX}: close it in Excel and run again.")

# ---------------------------------------------------------------- styling
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
SHADES = [PatternFill("solid", fgColor="F2F2F2"), PatternFill("solid", fgColor="FFFFFF")]
REF_FILL = PatternFill("solid", fgColor="DDEBF7")       # Original PSO
GOLD = PatternFill("solid", fgColor="FFE699")
LIGHT_GOLD = PatternFill("solid", fgColor="FFF2CC")
GREEN = PatternFill("solid", fgColor="C6EFCE")
DUP_FONT = Font(italic=True, color="8C8C8C")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
thin, med, thick = (Side(style="thin", color="BFBFBF"),
                    Side(style="thin", color="595959"),
                    Side(style="medium", color="000000"))

wb = load_workbook(XLSX)
ws = wb["Report table"]
n = report.shape[1]
for c in range(1, n + 1):
    cell = ws.cell(row=1, column=c)
    cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, CENTER
ws.freeze_panes = "B2"
ws.row_dimensions[1].height = 30

mcol = {m: list(report.columns).index(METRIC_LABEL[m]) + 1 for m in metrics}
prev_exp, prev_set, shade, exp_start = None, None, 0, 2
for i in range(len(s)):
    r = i + 2
    new_exp = s.at[i, "experiment"] != prev_exp
    new_set = s.at[i, "feature_set"] != prev_set
    if new_exp and prev_exp is not None:
        ws.merge_cells(start_row=exp_start, end_row=r - 1, start_column=1, end_column=1)
        exp_start = r
    if new_set:
        shade ^= 1
    if i == best_row:
        fill = GOLD
    elif i in best_in_exp:
        fill = LIGHT_GOLD
    elif s.at[i, "feature_set"] == "Original PSO":
        fill = REF_FILL
    else:
        fill = SHADES[shade]
    top = thick if (new_exp and i) else med if new_set and i else thin
    for c in range(1, n + 1):
        cell = ws.cell(row=r, column=c)
        cell.fill, cell.alignment = fill, CENTER
        cell.border = Border(top=top, bottom=thin, left=thin, right=thin)
        if s.at[i, "duplicate"] and c > 1:
            cell.font = DUP_FONT
    ws.cell(row=r, column=1).font = Font(bold=True)
    ws.cell(row=r, column=1).fill = PatternFill("solid", fgColor="FFFFFF")
    for m in metrics:
        if (i, m) in best_cell:
            cell = ws.cell(row=r, column=mcol[m])
            cell.font = Font(bold=True)
            if i != best_row:
                cell.fill = GREEN
    prev_exp, prev_set = s.at[i, "experiment"], s.at[i, "feature_set"]
ws.merge_cells(start_row=exp_start, end_row=len(s) + 1, start_column=1, end_column=1)
for c in range(1, n + 1):
    cell = ws.cell(row=len(s) + 1, column=c)
    cell.border = Border(top=cell.border.top, bottom=thick, left=thin, right=thin)

widths = {"A": 18, "B": 20, "C": 10, "D": 15, "E": 15, "F": 15, "G": 15,
          "H": 13, "I": 11, "J": 12}
for k, v in widths.items():
    ws.column_dimensions[k].width = v

legend = [
    (f"{args.antibiotic}. Values are mean ± SD over 5 cross-validation folds.", None, None),
    ("Gold row = best setup overall by mean AUPRC; light gold = best within the other experiment.",
     GOLD, None),
    ("Bold green = best value per metric across both experiments.", GREEN, None),
    ("Blue rows = Original PSO (reference for the PSO variants).", REF_FILL, None),
    ("Grey italic = identical to Raw with the same model "
     "(precomputed RBF kernel reproduces the RBF-SVM on raw features).", None, DUP_FONT),
    ("Selection time = representation preprocessing (Exp. 1) or PSO search time (PSO).",
     None, None),
]
for k, (text, f, font) in enumerate(legend):
    cell = ws.cell(row=len(s) + 3 + k, column=1, value=text)
    cell.font = font or Font(italic=True)
    if f:
        cell.fill = f

# Numeric sheet
ws = wb["Numeric"]
for c in range(1, numeric.shape[1] + 1):
    cell = ws.cell(row=1, column=c)
    cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, CENTER
ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions
nc = {name: i + 1 for i, name in enumerate(numeric.columns)}
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = CENTER
        if isinstance(cell.value, float):
            cell.number_format = "0.000"
last = len(numeric) + 1
for m in metrics:
    L = get_column_letter(nc[f"{m}_mean"])
    ws.conditional_formatting.add(f"{L}2:{L}{last}", ColorScaleRule(
        start_type="min", start_color="FFFFFF", end_type="max", end_color="63BE7B"))
for name, color in (("fit_seconds", "F4B183"), ("select_seconds", "9DC3E6"),
                    ("n_features_mean", "BDD7EE")):
    L = get_column_letter(nc[name])
    ws.conditional_formatting.add(f"{L}2:{L}{last}", DataBarRule(
        start_type="min", end_type="max", color=color))
for col in ws.columns:
    w = max(len(str(c.value)) if c.value is not None else 0 for c in col)
    ws.column_dimensions[get_column_letter(col[0].column)].width = w + 3

try:
    wb.save(XLSX)
except PermissionError:
    sys.exit(f"\nCould not write {XLSX}: close it in Excel and run again.")

print(f"Saved {XLSX} and cipro_combined_report.csv\n")
print(report.to_string(index=False))
