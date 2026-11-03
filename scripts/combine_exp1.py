"""
Combine Experiment 1 results (three antibiotics) into one styled summary.
Each row = antibiotic x representation x model, averaged over the CV folds
(mean and standard deviation).

Usage:  python combine_exp1.py [folder_with_csvs]
Outputs (written to results/combined/, overwritten on each run):
  exp1_summary.xlsx              styled workbook (Report table / Numeric / Best)
  exp1_summary_report.csv        "mean ± SD" table
  exp1_summary_numeric.csv       plain numbers
  exp1_best_per_antibiotic.csv   best setup per antibiotic (by AUPRC)
"""
import glob
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

# ---------------------------------------------------------------- load
in_dir = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "results" / "exp1")
files = sorted(
    f for f in glob.glob(os.path.join(in_dir, "exp1_*.csv"))
    if not any(k in os.path.basename(f) for k in ("preds", "summary", "best"))
)
if not files:
    sys.exit(f"No exp1_*.csv result files found in {in_dir}")
print("Combining:", [os.path.basename(f) for f in files])

df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
os.chdir(OUT_DIR)                                   # outputs go to results/combined

metrics = ["auroc", "auprc", "mcc", "bal_acc"]
cost = ["fit_seconds", "prep_seconds", "n_features"]
rep_order = ["raw", "kernel_linear", "kernel_rbf", "var500", "var1000", "var2000"]
model_order = ["lr", "svm", "xgb"]
df["representation"] = pd.Categorical(df["representation"], rep_order, ordered=True)
df["model"] = pd.Categorical(df["model"], model_order, ordered=True)

keys = ["antibiotic", "representation", "model"]
g = df.groupby(keys, observed=True)
summary = g[metrics].agg(["mean", "std"])
summary.columns = [f"{m}_{s}" for m, s in summary.columns]
summary = summary.join(g[cost].mean())
summary["n_folds"] = g.size()
summary = summary.reset_index()
summary["representation"] = summary["representation"].astype(str)
summary["model"] = summary["model"].astype(str)

# ------------------------------------------- flag duplicate rows
# A row is a duplicate if a row of the same antibiotic+model under "raw"
# has identical fold-mean metrics (e.g. kernel_rbf+SVM == raw+SVM).
summary["duplicate_of_raw"] = False
for i, r in summary.iterrows():
    if r["representation"] == "raw":
        continue
    raw = summary[(summary.antibiotic == r.antibiotic) &
                  (summary.model == r.model) &
                  (summary.representation == "raw")]
    # MCC and balanced accuracy come from hard predictions, so identical models
    # match exactly; AUROC/AUPRC can differ by rounding noise only.
    if len(raw) and all(abs(raw.iloc[0][f"{m}_mean"] - r[f"{m}_mean"]) < 1e-9
                        for m in ("mcc", "bal_acc")) \
            and abs(raw.iloc[0]["auroc_mean"] - r["auroc_mean"]) < 1e-4:
        summary.at[i, "duplicate_of_raw"] = True

# ------------------------------------------- best per antibiotic
best_idx = summary.groupby("antibiotic")["auprc_mean"].idxmax()
best = summary.loc[best_idx, keys + [f"{m}_mean" for m in metrics]].round(4)

# Best cell per metric within each antibiotic (duplicates excluded)
best_cell = {}  # (row_idx, metric) -> True
for ab, block in summary[~summary.duplicate_of_raw].groupby("antibiotic"):
    for m in metrics:
        best_cell[(block[f"{m}_mean"].idxmax(), m)] = True

# ------------------------------------------- report table (strings)
REP_LABEL = {"raw": "Raw", "kernel_linear": "Kernel (linear)",
             "kernel_rbf": "Kernel (RBF)", "var500": "Variance top-500",
             "var1000": "Variance top-1000", "var2000": "Variance top-2000"}
MODEL_LABEL = {"lr": "LR", "svm": "SVM", "xgb": "XGBoost"}
METRIC_LABEL = {"auroc": "AUROC", "auprc": "AUPRC", "mcc": "MCC",
                "bal_acc": "Balanced Acc."}

report = pd.DataFrame({
    "Antibiotic": summary["antibiotic"],
    "Representation": summary["representation"].map(REP_LABEL),
    "Model": summary["model"].map(MODEL_LABEL),
})
for m in metrics:
    report[METRIC_LABEL[m]] = (summary[f"{m}_mean"].map("{:.3f}".format) + " ± "
                               + summary[f"{m}_std"].map("{:.3f}".format))
report["Features"] = summary["n_features"].round().astype(int)
report["Fit time (s)"] = summary["fit_seconds"].round(1)

numeric = summary.drop(columns="duplicate_of_raw").round(4)

# ------------------------------------------- write CSVs + raw workbook
report.to_csv("exp1_summary_report.csv", index=False, encoding="utf-8-sig")
numeric.to_csv("exp1_summary_numeric.csv", index=False)
best.to_csv("exp1_best_per_antibiotic.csv", index=False)

XLSX = "exp1_summary.xlsx"
try:
    with pd.ExcelWriter(XLSX) as xw:
        report.to_excel(xw, sheet_name="Report table", index=False)
        numeric.to_excel(xw, sheet_name="Numeric", index=False)
        best.to_excel(xw, sheet_name="Best per antibiotic", index=False)
except PermissionError:
    sys.exit(f"\nCould not write {XLSX}: close it in Excel and run again.")

# ------------------------------------------- styling
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
HEADER_FONT = Font(bold=True, color="FFFFFF")
BLOCK_FILLS = [PatternFill("solid", fgColor="F2F2F2"),
               PatternFill("solid", fgColor="FFFFFF")]
BEST_CELL_FILL = PatternFill("solid", fgColor="C6EFCE")   # green
BEST_ROW_FILL = PatternFill("solid", fgColor="FFE699")    # gold
DUP_FONT = Font(italic=True, color="8C8C8C")
CENTER = Alignment(horizontal="center", vertical="center")
thin = Side(style="thin", color="BFBFBF")
thick = Side(style="medium", color="000000")


def style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font, cell.alignment = HEADER_FILL, HEADER_FONT, CENTER
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 22


def autowidth(ws, extra=3):
    for col in ws.columns:
        width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = width + extra


wb = load_workbook(XLSX)

# --- Report table
ws = wb["Report table"]
ncols = report.shape[1]
style_header(ws, ncols)
metric_cols = {m: list(report.columns).index(METRIC_LABEL[m]) + 1 for m in metrics}
best_rows = set(best_idx.values)

block_no, prev_ab, block_start = -1, None, None
for i in range(len(report)):
    r = i + 2  # excel row
    ab = summary.at[i, "antibiotic"]
    new_block = ab != prev_ab
    if new_block:
        block_no += 1
        if block_start is not None:
            ws.merge_cells(start_row=block_start, end_row=r - 1,
                           start_column=1, end_column=1)
        block_start = r
    fill = BEST_ROW_FILL if i in best_rows else BLOCK_FILLS[block_no % 2]
    for c in range(1, ncols + 1):
        cell = ws.cell(row=r, column=c)
        cell.fill = fill
        cell.alignment = CENTER
        cell.border = Border(top=thick if new_block else thin, bottom=thin,
                             left=thin, right=thin)
        if summary.at[i, "duplicate_of_raw"] and c > 1:
            cell.font = DUP_FONT
    for m, c in metric_cols.items():
        if (i, m) in best_cell:
            cell = ws.cell(row=r, column=c)
            cell.font = Font(bold=True)
            if i not in best_rows:
                cell.fill = BEST_CELL_FILL
    ws.cell(row=r, column=1).font = Font(bold=True)
    prev_ab = ab
ws.merge_cells(start_row=block_start, end_row=len(report) + 1,
               start_column=1, end_column=1)
autowidth(ws)
ws.column_dimensions["A"].width = 24
# bottom border of table
for c in range(1, ncols + 1):
    cell = ws.cell(row=len(report) + 1, column=c)
    cell.border = Border(top=cell.border.top, bottom=thick, left=thin, right=thin)

# legend
leg = len(report) + 3
notes = [
    ("Values are mean ± SD over 5 cross-validation folds.", None),
    ("Gold row = best setup per antibiotic by mean AUPRC.", BEST_ROW_FILL),
    ("Bold green = best value per metric within each antibiotic.", BEST_CELL_FILL),
    ("Grey italic = identical to the Raw row with the same model "
     "(precomputed RBF kernel reproduces the RBF-SVM on raw features).", None),
]
for k, (text, f) in enumerate(notes):
    cell = ws.cell(row=leg + k, column=1, value=text)
    cell.font = DUP_FONT if text.startswith("Grey") else Font(italic=True)
    if f:
        ws.cell(row=leg + k, column=1).fill = f

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
for i, _ in enumerate(numeric.itertuples()):
    if i > 0 and numeric.at[i, "antibiotic"] != numeric.at[i - 1, "antibiotic"]:
        for c in range(1, numeric.shape[1] + 1):
            ws.cell(row=i + 2, column=c).border = Border(top=thick)
# colour scales per antibiotic block (never across antibiotics)
for ab, block in numeric.groupby("antibiotic", sort=False):
    r0, r1 = block.index.min() + 2, block.index.max() + 2
    for m in metrics:
        L = get_column_letter(cols[f"{m}_mean"])
        ws.conditional_formatting.add(
            f"{L}{r0}:{L}{r1}",
            ColorScaleRule(start_type="min", start_color="FFFFFF",
                           end_type="max", end_color="63BE7B"))
# data bars on fit time (whole column, cost is comparable across antibiotics)
L = get_column_letter(cols["fit_seconds"])
ws.cell(row=1, column=cols["fit_seconds"])
ws.conditional_formatting.add(
    f"{L}2:{L}{len(numeric) + 1}",
    DataBarRule(start_type="min", end_type="max", color="F4B183"))
ws.column_dimensions[L].width = 16
autowidth(ws)
ws.column_dimensions[L].width = 18

# --- Best sheet
ws = wb["Best per antibiotic"]
style_header(ws, best.shape[1])
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = CENTER
        cell.fill = BEST_ROW_FILL
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        if isinstance(cell.value, float):
            cell.number_format = "0.000"
autowidth(ws)

try:
    wb.save(XLSX)
except PermissionError:
    sys.exit(f"\nCould not write {XLSX}: close it in Excel and run again.")

print(f"\nSaved {XLSX} and CSV files.")
print("\nBest per antibiotic (by AUPRC):")
print(best.to_string(index=False))
