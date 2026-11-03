# AMR prediction from MALDI-TOF mass spectra

Senior project, Biomedical Informatics, University of Sharjah.

The project predicts antimicrobial resistance (resistant vs. susceptible) in *E. coli* from MALDI-TOF mass spectra (DRIAMS-A). It compares ways of representing and reducing the 6,000-bin spectra, combined with several classifiers, under one shared evaluation protocol. Methods tested so far:

- **Input representations:** raw spectra, linear and RBF kernels, variance filtering (top 500/1000/2000 bins)
- **Dimensionality reduction:** PCA, Kernel PCA, LASSO, grouped ANOVA
- **Wrapper feature selection:** particle swarm optimisation (Original PSO, a Baseline PSO, four single enhancements, and the full model with all four)
- **Classifiers:** logistic regression, SVM, XGBoost

The final method has not been chosen yet. All methods use the same data, folds and metrics, so they can be compared directly.

## Repository layout

```
data/                    raw DRIAMS files and shared data (not committed, see docs/DATA.md)
data_preparation/
  AMR_A_MLphase.ipynb    builds spectra_ecoli_A.npy + labels_ecoli_A.csv (labels, folds),
                         then baseline, Kernel PCA, LASSO and grouped ANOVA reducers
experiments/
  Starter_Members_1_2.ipynb       shared loader + run_cv template for team members
  reduction_kernel/               PCA, Kernel PCA (linear, RBF), PCA region maps
  ml_rf_ksshiba/                  Random Forest and KSSHIBA on the reduced inputs
  grouped_anova/                  grouped ANOVA window selection
  pso_development/                PSO development steps (region-aware, adaptive, stability, hybrid)
  final_exp1_exp2/                Exp. 1 representation benchmark + Exp. 2 region-aware PSO
results/                 one folder per experiment (see table below)
scripts/                 combine and style result tables into results/combined/
figures/                 figures for the report
docs/                    data description
```

### Which notebook produced which results

| Notebook | Results |
|---|---|
| `experiments/reduction_kernel/Kernel_Reduction.ipynb` | `results/reduction/` (baseline, PCA-50/200, Kernel PCA linear/RBF, PCA region top-100), `figures/fig_region_heatmap.png` |
| `experiments/ml_rf_ksshiba/Member1_ML_RF_KSSHIBA.ipynb` | `results/ml/`, `results/regions/ksshiba_weights/` |
| `experiments/grouped_anova/member2_optimization.ipynb` | `results/grouped_anova/` |
| `experiments/final_exp1_exp2/Final_Experiments_PSO_Step4.ipynb` | `results/exp1/`, `results/exp2_pso/pso_*`, `figures/fig_auprc.png`, `fig_convergence.png`, `fig_regions.png` |
| *not in this repository yet* | `results/regions/` (bins_rf, bins_ksshiba, regions_*_top5, consensus_regions*), `figures/fig_consensus_regions.png`, `results/exp2_pso/PSO_Original_*`, `PSO_Gradual_*` |

`*_preds_*.csv` hold per-isolate test predictions, which can be used for ROC/PR curves and significance tests. `pso_signature_*_fold*.npy` are the bins PSO selected in each fold.

## Setup

```bash
pip install -r requirements.txt
```

Download DRIAMS-A into `data/raw/`, then run `data_preparation/01_AMR_A_MLphase.ipynb` to create the two shared files in `data/processed/`. Details are in [docs/DATA.md](docs/DATA.md).

## Evaluation protocol

- 7,320 *E. coli* isolates, 6,000 bins each. Labels: R = 1, S = 0. Intermediate and untested results are excluded.
- Fixed stratified 5-fold CV per antibiotic (`random_state=42`). Every method uses the same folds.
- Feature selection or reduction is fitted on the training folds only.
- Metrics: AUROC, AUPRC, MCC, balanced accuracy. The data is imbalanced, so accuracy is not reported.

## Rebuilding the summary tables

Run these from the repository root. Each one reads `results/exp1/` and `results/exp2_pso/` and writes styled `.xlsx` and `.csv` tables to `results/combined/`:

```bash
python scripts/combine_exp1.py                     # Exp. 1, all antibiotics
python scripts/combine_pso.py --ref "Original PSO" # PSO variants vs Original PSO
python scripts/combine_cipro.py                    # Ciprofloxacin: Exp. 1 + all PSO variants
```

Close any open `.xlsx` output in Excel before running, or the script can't overwrite it.

## Team

- Maria Taleb Rooeintan
