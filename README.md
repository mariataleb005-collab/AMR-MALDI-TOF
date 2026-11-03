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
data/
  raw/                 original DRIAMS files (not committed)
  processed/           spectra_ecoli_A.npy, labels_ecoli_A.csv (not committed)
data_preparation/      notebooks that build the shared data (labels + folds)
experiments/           one folder per experiment (code + notes)
  exp1_representations/  raw, kernel (linear/RBF), variance top-k x LR/SVM/XGB
  exp2_pso/              Original PSO, Baseline, single enhancements, full PSO
results/
  exp1/                per-fold results of Exp. 1
  exp2_pso/            per-fold results of the PSO experiments
  combined/            summary tables made by scripts/
scripts/               scripts that combine and style the result tables
figures/               figures for the report
docs/                  data description and notes
```

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
