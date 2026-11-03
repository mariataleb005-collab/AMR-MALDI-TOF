# Data

## Source

DRIAMS-A (University Hospital Basel, 2015–2018), part of the public DRIAMS dataset:

- Weis et al., "Direct antimicrobial resistance prediction from clinical MALDI-TOF mass spectra using machine learning", *Nature Medicine*, 2022.
- Dataset: https://datadryad.org/dataset/doi:10.5061/dryad.bzkh1899q

We use the binned spectra: 6,000 bins of 3 Da covering 2,000–20,000 Da.

## How the shared files are built

Notebook: `data_preparation/01_AMR_A_MLphase.ipynb`

1. **Isolates.** All *E. coli* isolates from Hospital A: 7,320 isolates, each with exactly one 6,000-bin spectrum.
2. **Antibiotics.** Keep antibiotics with at least 30 resistant (R) and at least 30 susceptible (S) *E. coli* isolates. This gives 15 antibiotics.
3. **Labels.** R = 1, S = 0. Everything else is set to missing (NaN): intermediate (I), mixed results such as "R(1), S(1)", "−" and untested.
4. **Folds.** `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`, run separately for each antibiotic and only on its labelled isolates. Unlabelled isolates get fold `-1`.

## `labels_ecoli_A.csv` columns

| Column | Meaning |
|---|---|
| `code` | DRIAMS isolate ID; row *i* matches row *i* of `spectra_ecoli_A.npy` |
| `year` | Year of collection (2015–2018) |
| `<antibiotic>` | 1 = resistant, 0 = susceptible, empty = not used |
| `fold_<antibiotic>` | CV fold 0–4; `-1` = no label for this antibiotic (excluded) |

## Antibiotics

The labels file has 15 antibiotics. The models use 12 of them (`MODEL_ABX`). Amikacin, Fosfomycin-Trometamol and Ertapenem are left out because they have too few resistant isolates (30–35).

## Things to report

- Removing intermediate results matters most for Cefepime (504 I), Ceftazidime (365 I) and Amikacin (296 I). Weis et al. counted I as resistant, so results are not directly comparable with theirs.
- The `laboratory_species` column, which records subtypes such as ESBL or carbapenemase-producing, is not used.
