# Experiment 4: Enhanced multi-objective PSO (EMOPSO) for region selection

## Why this experiment
Experiment 3 showed that a single score (AUPRC minus a size penalty) does not separate the optimisers:
final accuracy was within 0.02 AUPRC for all of them, and the search score did not predict final accuracy.
Experiment 4 treats accuracy and size as **two objectives** and returns a **Pareto front** (best accuracy for
every set size), so no penalty lambda has to be tuned. It also fixes the issues found in the review:

| Issue in Experiment 3 | What Experiment 4 does |
|---|---|
| KNN wrapper does not match the final tree models | Wrapper is L2 logistic regression (`fitness.wrapper_classifier`, can be KNN or LightGBM) |
| Empty regions on Var-2000 waste the search | Regions with no bin are removed from the search space for **all** algorithms |
| Same inner folds reused 2,000 times (optimistic scores) | Every returned front is re-scored on 3 fresh repetitions of 3-fold CV (same folds for every algorithm) |
| One set chosen with a tuned penalty | The smallest set within one standard error of the best AUPRC (1-SE rule) and the knee point |
| Only the proposed method used ANOVA | `mopso+init` = baseline with the same ANOVA start (fairness control) |
| Design and evaluation on the same antibiotics | Settings are frozen; the 9 antibiotics not used in Experiment 3 are the evaluation set |
| 3 seeds | 10 seeds |

## Algorithms
| Name | Role | Description |
|---|---|---|
| `emopso` | proposed | Enhanced region-aware MOPSO (7 components below) |
| `mopso` | baseline | Binary MOPSO, Coello Coello, Pulido and Lechuga (2004): adaptive-grid archive, sigmoid transfer, inertia 0.4, Coello mutation |
| `nsga2` | reference | Binary NSGA-II, Deb et al. (2002) |
| `mopso+init` | fairness control | Baseline MOPSO with the ANOVA start of the proposed method |

Components of `emopso` (remove one with `emopso-<name>`, for the ablation study):

| Component | What it does |
|---|---|
| `init` | ANOVA-guided, size-stratified start: particle sizes spread on a log scale, regions drawn with an ANOVA bias |
| `leader` | Crowding-distance archive (MOPSO-CD): leaders from sparse parts of the front |
| `vshape` | V-shaped transfer \|tanh(v)\| that flips bits, instead of sigmoid |
| `inertia` | Inertia decreasing linearly from 0.9 to 0.4 |
| `mutation` | Region-aware mutation: shift a region to its m/z neighbour, drop a weak one, add a strong one, or flip one bit |
| `restart` | After 5 iterations without an archive change, the worst half of the swarm restarts next to archive members (and is scored at once) |
| `local` | 10 % of the budget for a final local search on the archive (remove weakest / add strongest region) |

All algorithms share one fitness object, the same budget (2,000 calls), population (20), archive size (30),
inner folds, selection subsample per seed and final evaluation.

## Files
| File | Content |
|---|---|
| `mopso.py` | The algorithms, fitness, archive, hypervolume and IGD+ |
| `experiment4_mopso.py` | Runs the experiment and writes results |
| `config/experiment4_mopso.yaml` | All settings. **Do not change between runs.** |
| `summarise_exp4.py` | Tables, statistics, figures and an Excel workbook |
| `results/exp4_demo/`, `results/exp4_demo_summary/` | Demo on 30 % of the isolates (not for the paper) |

## Setup
```
pip3 install -r requirements.txt
```

## Step 1: pilot (about 5 minutes, one antibiotic)
```
python3 experiment4_mopso.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4_pilot/ --runner <name> --input Var-2000 --antibiotic <one of yours> --sample-frac 0.3 --budget 300 --seeds 0
```
Check that it finishes and that the log says `all budgets respected: True`. Do not commit pilot results.

## Step 2: main run (all your antibiotics, 10 seeds)
```
python3 experiment4_mopso.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4/ --runner <name> --input Var-2000
```
Then the same with `--input PCA-200` and `--input Raw-6000`. Runs `emopso`, `mopso` and `nsga2`.
Use `--n-jobs` to set the number of CPU cores (default: all but one). Each antibiotic writes to
`results/exp4/<antibiotic>/`.

## Step 3: ablation (Var-2000 only)
```
python3 experiment4_mopso.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4_ablation/ --runner <name> --input Var-2000 --algorithms ablation
```

## Step 4: summary and export (one person, after all branches are merged)
During development, never read 2018:
```
python3 summarise_exp4.py --results results/exp4,results/exp4_ablation --input Var-2000 --out results/exp4_summary --training-only
```
Final, once, for the paper:
```
python3 summarise_exp4.py --results results/exp4,results/exp4_ablation --input Var-2000 --out results/exp4_summary
```
Report the development antibiotics (Ceftriaxone, Tobramycin, Amikacin, Amoxicillin-Clavulanic acid) separately
from the 9 evaluation antibiotics: add `--results` folders that contain only one group, or filter the
`all_runs` sheet.

## What to report
- **Main table:** per antibiotic and algorithm, mean (sd) over 10 seeds of hypervolume (re-scored), IGD+,
  bins in the chosen set, stability (Nogueira), training CV AUPRC, 2018 AUROC and AUPRC (mean of RF, XGBoost, LightGBM).
- **Statistics:** Wilcoxon signed-rank of `emopso` against each algorithm, paired by antibiotic and seed,
  Holm-corrected (`wilcoxon` sheet); Friedman over antibiotics (`friedman` sheet).
- **Figures:** `fig_fronts.png` (Pareto fronts), `fig_hv_convergence.png`, `fig_hv_box.png`, `fig_ablation.png`.
- **Regions:** `chosen_regions` in `exp4_<input>_runs.csv` are region ids; m/z range of region r is
  2000 + 30 r to 2000 + 30 (r + 1) Da (`common.mz_range`).
- Report the result as it comes out, including if a baseline is as good.

## Rules
- Do not edit `config/experiment4_mopso.yaml` or `mopso.py` after the evaluation runs start. If something
  must change, re-run every algorithm.
- Commit before every run (the log records the commit and flags uncommitted changes).
- Never commit the spectra or results made with `--sample-frac`.
