# AMR-MALDI-TOF: region-aware PSO for antibiotic-resistance prediction

E. coli MALDI-TOF spectra (DRIAMS-A, 7,320 spectra x 6,000 bins, 3 Da per bin) and six antibiotics:
Ciprofloxacin, Ceftriaxone, Cefepime, Piperacillin-Tazobactam, Tobramycin, Ampicillin-Amoxicillin.

## Protocol
- Labels: S = 0, I or R = 1. Cells with two different results (e.g. "R(1), S(1)") are treated as missing.
- Train on 2015-2017 with 5 stratified folds, test once on 2018.
- Metrics: AUPRC, AUROC, MCC, balanced accuracy, VME, ME. Friedman + Nemenyi for comparisons.

## Files
| File | What it does |
|---|---|
| `step1_build_labels.py` | Builds the corrected labels and the label counts |
| `common.py` | Shared code: data loading, split, folds, metrics |
| `step2_representation.py` | Step 2: 7 inputs x 6 models benchmark |
| `step3_feature_selection.py` | Step 3: RA-PSO vs other selectors (same fitness, same budget) |
| `report.py` | Combines results into summary tables and figures |
| `data/` | `labels_ecoli_A_corrected.csv`, `label_counts.csv` (spectra are not stored here) |
| `results/` | Summary tables and figures |
| `docs/` | Progress updates |

The spectra file `data/spectra_ecoli_A.npy` is too large for GitHub and is not included.

## Run
```
pip3 install -r requirements.txt
python3 step2_representation.py data/ data/labels_ecoli_A_corrected.csv results/ Ciprofloxacin
```
Step 3 (`step3_feature_selection.py`) and `report.py` are run the same way; see the top of each script for its arguments.
Antibiotic names: `Ciprofloxacin` `Ceftriaxone` `Cefepime` `Piperacillin-Tazobactam` `Tobramycin` `Ampicillin-Amoxicillin`.
Check the first log line against `data/label_counts.csv` (for example Ciprofloxacin: train 3536, 1084 R; test 1375, 382 R).

## Status
Steps 1 to 3 done for all six antibiotics. See `docs/` for the progress update.
