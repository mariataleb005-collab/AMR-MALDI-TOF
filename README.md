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
## Run Experiment 3

### Setup
```
pip3 install -r requirements.txt
```
The spectra file `spectra_ecoli_A.npy` is not in the repository (too large). Each person keeps a copy on their own computer. The first argument of the command below is the **folder that contains it**. If the path has a space, put it in quotes.

### Who runs which antibiotics
`--runner` selects the antibiotics assigned to a person (set in `config/experiment3_settings.yaml`).

| Runner | Antibiotics |
|---|---|
| `joud` | Ciprofloxacin, Cefepime, Cotrimoxazole, Levofloxacin, Ceftazidime |
| `maria` | Ceftriaxone, Tobramycin, Amikacin, Amoxicillin-Clavulanic acid |
| `zainab` | Piperacillin-Tazobactam, Ampicillin-Amoxicillin, Cefpodoxime, Norfloxacin |

### Pilot (small test on one antibiotic, about 5 to 10 minutes)
```
python3 experiment3_optimisers.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp3_pilot/ --runner <name> --input Var-2000 --antibiotic <one of your antibiotics> --budget 200 --seeds 0
```
The pilot checks that the script works and how long a run takes. Do not commit pilot results.

### Full run (one input at a time)
```
python3 experiment3_optimisers.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp3/ --runner <name> --input Var-2000 --algorithms binary_pso,ga,gwo,woa
```
- Inputs are run separately, in this order: `Var-2000`, then `PCA-200`, then `Raw-6000` (`--input`).
- Budget (2,000 fitness calls), 3 seeds, folds and the KNN search classifier come from the settings file and are the same for everyone.
- Run all of your antibiotics in one command, or add `--antibiotic <name>` for one.
- Results are written to `results/exp3/<antibiotic>/`: `exp3_<input>_selections.csv`, `exp3_<input>_test.csv` and `exp3_<input>_log.txt`.

### Enhanced PSO
The four baselines are run first. The enhanced PSO is run afterwards with the tuned settings stored under `enhanced_pso: params` in the settings file. It runs into a **separate folder** so it does not overwrite the baselines:
```
python3 experiment3_optimisers.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp3_enhanced/ --runner <name> --input Var-2000 --algorithms enhanced_pso
```

### Re-scoring without searching again
`--rescore` reads the regions saved in `exp3_<input>_selections.csv` and repeats only the six-model scoring. Use the same command and output folder as the run being re-scored, with `--rescore` added.

### What to report
One row per algorithm and antibiotic, averaged over the 3 seeds and the three tree models (XGBoost, LightGBM, Random Forest):

| Antibiotic | Algorithm | Training AUROC | Training AUPRC | Test AUROC | Test AUPRC | Selected bins | Stability |
|---|---|---|---|---|---|---|---|

- Training = 5-fold cross-validation on 2015-2017. Test = 2018, used once.
- Selected bins = number of m/z bins kept. Stability = Nogueira index over the 3 seeds.

Each log starts with the commit and a fingerprint of the settings that were used. Check the first line of each antibiotic against `data/label_counts.csv` (for example Ciprofloxacin: train 3536, 1084 non-susceptible; test 1375, 382).

## Working together
- `main` holds the shared code and settings and is changed only by merging.
- Each person works on a branch (`run-<name>`), pulls `main` before a run, and commits results only inside `results/exp3/<antibiotic>/` for the antibiotics assigned to them. One person writes to each antibiotic folder, so merges do not conflict.
- Large files (spectra, `.npy`) are not committed.
