"""
Summarise the PSO gradual (ablation) experiment.
Each row = antibiotic x variant x model, averaged over CV folds (mean ± SD),
plus the paired change versus Baseline (same fold, same model).

Usage:  python combine_pso.py                      (Original + Gradual, ref = Baseline)
        python combine_pso.py --ref "Original PSO"
        python combine_pso.py file1.csv file2.csv --ref "Baseline"
Outputs (overwritten each run):
  pso_summary.xlsx            styled workbook (Report table / Delta vs baseline / Numeric)
  pso_summary_report.csv
  pso_delta_vs_baseline.csv
"""
import os
import sys

import pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]          # repository root
OUT_DIR = ROOT / "results" / "combined"             # where summary tables are saved
from openpyxl import load_workbook
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import argparse

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="*",
                default=[str(ROOT / "results" / "exp2_pso" / f) for f in
                         ("PSO_Original_experiment_results.csv",
                          "PSO_Gradual_experiment_results.csv",
                          "pso_Ciprofloxacin.csv")],
                help="one or more PSO result CSVs (rows are stacked in this order)")
ap.add_argument("--ref", default="Baseline",
                help='variant used as reference for the delta sheet, e.g. "Original PSO"')
ap.add_argument("--full-name", default="All 4 enhancements",
                help="variant name given to a file without a 'variant' column")
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

paths = [p for p in args.files if os.path.exists(p)]
missing = [p for p in args.files if not os.path.exists(p)]
if missing:
    print("Skipping missing file(s):", missing)
if not paths:
    sys.exit("No input files found.")
print("Combining:", [os.path.basename(p) for p in paths])
df = pd.concat([load_pso(p, args.full_name) for p in paths], ignore_index=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
os.chdir(OUT_DIR)                                   # outputs go to results/combined
REF = args.ref

metrics = ["auroc", "auprc", "mcc", "bal_acc"]
METRIC_LABEL = {"auroc": "AUROC", "auprc": "AUPRC", "mcc": "MCC",
                "bal_acc": "Balanced Acc."}
MODEL_LABEL = {"lr": "LR", "svm": "SVM", "xgb": "XGBoost"}

# Keep variant order as it appears in the file (Baseline first)
variant_order = list(dict.fromkeys(df["variant"]))
df["variant"] = pd.Categorical(df["variant"], variant_order, ordered=True)
df["model"] = pd.Categorical(df["model"], ["lr", "svm", "xgb"], ordered=True)
keys = ["antibiotic", "variant", "model"]

# ---------------------------------------- flag identical runs (same fold)
dup_notes = []
for (ab, fold, model), grp in df.groupby(["antibiotic", "fold", "model"], observed=True):
    sig = grp[metrics + ["n_features"]].round(9).astype(str).agg("|".join, axis=1)
    for s, sub in grp.groupby(sig):
        if len(sub) > 1:
            dup_notes.append(f"{ab}, fold {fold}, {MODEL_LABEL[model]}: "
                             + " = ".join(sub["variant"].astype(str)))
# collapse per fold for the legend
dup_folds = sorted({n.split(":")[0].rsplit(",", 1)[0] + ": "
                    + n.split(": ", 1)[1] for n in dup_notes})

# ---------------------------------------- mean ± SD
g = df.groupby(keys, observed=True)
summary = g[metrics].agg(["mean", "std"])
summary.columns = [f"{m}_{s}" for m, s in summary.columns]
summary = summary.join(g[["n_features"]].agg(["mean", "std"]).set_axis(
    ["n_features_mean", "n_features_std"], axis=1))
summary = summary.join(g[["fit_seconds", "search_seconds"]].mean())
summary["n_folds"] = g.size()
summary = summary.reset_index()
summary["variant"] = summary["variant"].astype(str)
summary["model"] = summary["model"].astype(str)

# ---------------------------------------- paired delta vs Baseline
if REF not in set(df["variant"]):
    sys.exit(f'Reference variant "{REF}" not found. Available: {list(dict.fromkeys(df["variant"]))}')
base = df[df["variant"] == REF].set_index(["antibiotic", "fold", "model"])[metrics]
rows = []
for (ab, var, model), grp in df[df["variant"] != REF].groupby(keys, observed=True):
    d = grp.set_index(["antibiotic", "fold", "model"])[metrics] - base.loc[
        grp.set_index(["antibiotic", "fold", "model"]).index]
    row = {"antibiotic": ab, "variant": str(var), "model": str(model)}
    for m in metrics:
        row[f"d_{m}_mean"] = d[m].mean()
        row[f"d_{m}_std"] = d[m].std()
        row[f"{m}_folds_improved"] = int((d[m] > 0).sum())
    row["n_folds"] = len(d)
    rows.append(row)
delta = pd.DataFrame(rows)

# ---------------------------------------- best rows / cells
best_idx = set(summary.groupby("antibiotic")["auprc_mean"].idxmax())
best_cell = {(summary.groupby("antibiotic")[f"{m}_mean"].idxmax()[ab], m)
             for m in metrics for ab in summary["antibiotic"].unique()}

# ---------------------------------------- report tables
def pm(mean, sd, fmt="{:.3f}"):
    return mean.map(fmt.format) + " ± " + sd.map(fmt.format)

report = pd.DataFrame({"Antibiotic": summary["antibiotic"],
                       "Variant": summary["variant"],
                       "Model": summary["model"].map(MODEL_LABEL)})
for m in metrics:
    report[METRIC_LABEL[m]] = pm(summary[f"{m}_mean"], summary[f"{m}_std"])
report["Features"] = pm(summary["n_features_mean"], summary["n_features_std"], "{:.0f}")
report["Fit time (s)"] = summary["fit_seconds"].round(1)
report["PSO search (s)"] = summary["search_seconds"].round(0).astype(int)

delta_rep = pd.DataFrame({"Antibiotic": delta["antibiotic"],
                          "Variant": delta["variant"],
                          "Model": delta["model"].map(MODEL_LABEL)})
for m in metrics:
    delta_rep[f"Δ {METRIC_LABEL[m]}"] = (
        delta[f"d_{m}_mean"].map("{:+.3f}".format) + " ± "
        + delta[f"d_{m}_std"].map("{:.3f}".format)
        + "  (" + delta[f"{m}_folds_improved"].astype(str) + "/"
        + delta["n_folds"].astype(str) + ")")

numeric = summary.round(4)

report.to_csv("pso_summary_report.csv", index=False, encoding="utf-8-sig")
delta.round(4).to_csv("pso_delta_vs_baseline.csv", index=False)

XLSX = "pso_summary.xlsx"
try:
    with pd.ExcelWriter(XLSX) as xw:
        report.to_excel(xw, sheet_name="Report table", index=False)
        delta_rep.to_excel(xw, sheet_name="Delta vs reference", index=False)
        numeric.to_excel(xw, sheet_name="Numeric", index=False)
except PermissionError:
    sys.exit(f"\nCould not write {XLSX}: close it in Excel and run again.")

# ---------------------------------------- styling
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
BASE_FILL = PatternFill("solid", fgColor="DDEBF7")       # light blue = baseline
WHITE = PatternFill("solid", fgColor="FFFFFF")
GREY = PatternFill("solid", fgColor="F2F2F2")
BEST_CELL_FILL = PatternFill("solid", fgColor="C6EFCE")
BEST_ROW_FILL = PatternFill("solid", fgColor="FFE699")
UP_FILL = PatternFill("solid", fgColor="C6EFCE")
DOWN_FILL = PatternFill("solid", fgColor="F8CBAD")
CENTER = Alignment(horizontal="center", vertical="center")
thin, thick = Side(style="thin", color="BFBFBF"), Side(style="medium", color="000000")


def style_header(ws, n):
    for c in range(1, n + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, CENTER
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22


def autowidth(ws, extra=3):
    for col in ws.columns:
        w = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(w + extra, 60)


def style_blocks(ws, frame, var_col, fill_for_row, merge_col=1):
    """Thick line between variants, merged antibiotic column, row fills."""
    n = frame.shape[1]
    prev_var, ab_start = None, 2
    for i in range(len(frame)):
        r = i + 2
        new_var = frame.iloc[i][var_col] != prev_var
        for c in range(1, n + 1):
            cell = ws.cell(row=r, column=c)
            cell.fill = fill_for_row(i)
            cell.alignment = CENTER
            cell.border = Border(top=thick if new_var and i else thin,
                                 bottom=thin, left=thin, right=thin)
        ws.cell(row=r, column=1).font = Font(bold=True)
        prev_var = frame.iloc[i][var_col]
    ws.merge_cells(start_row=2, end_row=len(frame) + 1,
                   start_column=merge_col, end_column=merge_col)


wb = load_workbook(XLSX)

# --- Report table
ws = wb["Report table"]
style_header(ws, report.shape[1])
style_blocks(ws, report, "Variant",
             lambda i: BEST_ROW_FILL if i in best_idx
             else BASE_FILL if summary.at[i, "variant"] == REF
             else (WHITE if variant_order.index(summary.at[i, "variant"]) % 2 else GREY))
mcol = {m: list(report.columns).index(METRIC_LABEL[m]) + 1 for m in metrics}
for (i, m) in best_cell:
    cell = ws.cell(row=i + 2, column=mcol[m])
    cell.font = Font(bold=True)
    if i not in best_idx:
        cell.fill = BEST_CELL_FILL
autowidth(ws)
ws.column_dimensions["A"].width = 16
legend = ["Values are mean ± SD over 5 cross-validation folds. "
          "Features = PSO-selected subset size (varies by fold).",
          f"Blue rows = {REF} (reference).",
          "Gold row = best setup by mean AUPRC.",
          "Bold green = best value per metric (outside the gold row)."]
if dup_folds:
    legend.append("Identical results (same subset selected): " + "; ".join(dup_folds) + ".")
fills = [None, BASE_FILL, BEST_ROW_FILL, BEST_CELL_FILL, None]
for k, text in enumerate(legend):
    c = ws.cell(row=len(report) + 3 + k, column=1, value=text)
    c.font = Font(italic=True)
    if fills[k]:
        c.fill = fills[k]

# --- Delta sheet
ws = wb["Delta vs reference"]
style_header(ws, delta_rep.shape[1])
style_blocks(ws, delta_rep, "Variant",
             lambda i: WHITE if variant_order.index(delta.at[i, "variant"]) % 2 else GREY)
dcol = {m: list(delta_rep.columns).index(f"Δ {METRIC_LABEL[m]}") + 1 for m in metrics}
for i in range(len(delta)):
    for m in metrics:
        d, k, n = delta.at[i, f"d_{m}_mean"], delta.at[i, f"{m}_folds_improved"], delta.at[i, "n_folds"]
        cell = ws.cell(row=i + 2, column=dcol[m])
        if abs(d) < 0.0005:          # rounds to ±0.000: no change
            cell.fill = WHITE
        elif d > 0:
            cell.fill = UP_FILL
        else:
            cell.fill = DOWN_FILL
        if (d > 0 and k == n) or (d < 0 and k == 0):   # consistent in every fold
            cell.font = Font(bold=True)
autowidth(ws)
ws.column_dimensions["A"].width = 16
legend = [f"Δ = variant minus {REF}, paired by fold and model (mean ± SD).",
          f"(k/5) = number of folds where the variant beat {REF}.",
          f"Green = higher than {REF} on average; red = lower; white = no change (|Δ| < 0.0005).",
          "Bold = same direction in every fold."]
for k, text in enumerate(legend):
    c = ws.cell(row=len(delta_rep) + 3 + k, column=1, value=text)
    c.font = Font(italic=True)
    if k == 2:
        c.fill = UP_FILL

# --- Numeric sheet
ws = wb["Numeric"]
style_header(ws, numeric.shape[1])
ws.auto_filter.ref = ws.dimensions
cols = {name: i + 1 for i, name in enumerate(numeric.columns)}
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = CENTER
        if isinstance(cell.value, float):
            cell.number_format = "0.000"
n = len(numeric) + 1
for m in metrics:
    L = get_column_letter(cols[f"{m}_mean"])
    ws.conditional_formatting.add(f"{L}2:{L}{n}", ColorScaleRule(
        start_type="min", start_color="FFFFFF", end_type="max", end_color="63BE7B"))
for name, color in (("fit_seconds", "F4B183"), ("search_seconds", "9DC3E6")):
    L = get_column_letter(cols[name])
    ws.conditional_formatting.add(f"{L}2:{L}{n}", DataBarRule(
        start_type="min", end_type="max", color=color))
autowidth(ws)

try:
    wb.save(XLSX)
except PermissionError:
    sys.exit(f"\nCould not write {XLSX}: close it in Excel and run again.")

print(f"Saved {XLSX} and CSV files.\n")
print(delta_rep.to_string(index=False))
if dup_notes:
    print("\nIdentical runs:", *dup_notes, sep="\n  ")
