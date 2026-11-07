# AMR-MALDI-TOF: region selection with metaheuristic optimisers for antibiotic-resistance prediction

E. coli MALDI-TOF spectra (DRIAMS-A, 7,320 spectra x 6,000 bins, 3 Da per bin) and 13 antibiotics.
The project predicts whether an isolate is susceptible (0) or non-susceptible (1, intermediate or resistant)
and identifies the m/z regions that carry the resistance signal.

## Protocol
- Labels: S = 0, I or R = 1. Cells with two different results (e.g. "R(1), S(1)") are treated as missing.
- Train on 2015-2017 with 5 stratified folds (fixed seed); test once on 2018. The test year is never used for tuning or selection.
- Antibiotics are kept if they are tested, have more than one label, have both classes in the training and test years, and have at least 30 isolates of the smaller class in each. 13 antibiotics pass:
  Ceftriaxone, Ciprofloxacin, Cefepime, Cotrimoxazole, Tobramycin, Ampicillin-Amoxicillin, Amikacin, Levofloxacin,
  Amoxicillin-Clavulanic acid, Ceftazidime, Piperacillin-Tazobactam, Cefpodoxime, Norfloxacin.
- Metrics: AUROC, AUPRC, F1, MCC, balanced accuracy, VME, ME; Friedman and Nemenyi tests for comparisons.

## Experiments
| Experiment | Question | Script |
|---|---|---|
| Labels | Rebuild labels and folds with the literature definition | `step1_build_labels.py` |
| Inputs and models | 7 inputs (raw 6,000 bins, variance top-k, PCA) x 6 models, six antibiotics | `step2_representation.py` |
| Earlier selector comparison | Region-aware PSO against filter and wrapper selectors, six antibiotics | `step3_feature_selection.py` |
| Experiment 3 | Five wrapper optimisers (enhanced PSO, binary PSO, GA, GWO, WOA) with the same fitness, budget and folds, on three inputs, 13 antibiotics | `experiment3_optimisers.py` |

All Experiment 3 settings are in `config/experiment3_settings.yaml`, and every run reads that file.
In Experiment 3 each optimiser searches for a set of regions; an KNN inside the search scores each candidate set on the
training years. The final set is then used to train the models of the input comparison on 2015-2017 and to score them once on 2018.

## Files
| File / folder | Content |
|---|---|
| `common.py` | Shared code: data loading, split, folds, metrics |
| `config/experiment3_settings.yaml` | Settings of Experiment 3 |
| `experiment3_optimisers.py` | Experiment 3 |
| `report.py` | Combines results into summary tables and figures |
| `data/` | `labels_ecoli_A_corrected.csv`, `label_counts.csv` (the spectra are not stored here) |
| `results/` | Summary tables and figures; Experiment 3 writes to `results/exp3/<antibiotic>/` |
| `docs/` | Progress updates |

The spectra file `data/spectra_ecoli_A.npy` is too large for GitHub and is not included.

## Run
```
pip3 install -r requirements.txt
python3 experiment3_optimisers.py data/ data/labels_ecoli_A_corrected.csv results/exp3/ --runner <name> --input Var-2000
```
`--runner` takes `joud`, `maria` or `zainab` and runs the antibiotics listed for that name in the settings file.
`--antibiotic <name>` runs a single antibiotic (used for a pilot run). Each log starts with the commit and the settings that were used.
Check the first log line of an antibiotic against `data/label_counts.csv` (for example Ciprofloxacin: train 3536, 1084 non-susceptible; test 1375, 382).

## Working together
- `main` holds the shared code and settings and is changed only by merging.
- Each person works on a branch (`run-<name>`), pulls `main` before a run, and commits results only inside `results/exp3/<antibiotic>/` for the antibiotics assigned to them. One person writes to each antibiotic folder, so merges do not conflict.
- Large files (spectra, `.npy`) are not committed.
