# ATHAR model registry

ATHAR predicts only with the models installed in this folder. An antibiotic with no folder here is
shown as "No model installed" and is skipped during analysis.

## Layout

```
models/
  Ceftriaxone/
    model.json
    model.joblib
  Amoxicillin-Clavulanic_acid/      spaces in the antibiotic name become underscores
    model.json
    model.joblib
```

The app reads this folder when it starts. After adding or replacing a model, restart the app.

## model.json

Example (the numbers are illustrative, not real results):

```json
{
  "schema_version": 1,
  "antibiotic": "Ceftriaxone",
  "model_version": "final-2026-11",
  "input": "Raw-6000",
  "selector": "emopso",
  "seed": 0,
  "classifier": "LR",
  "regions": [12, 57, 233],
  "threshold": -0.137,
  "score_type": "decision",
  "indeterminate_band": null,
  "training": {"years": "2015-2017", "n_spectra": 3575, "n_resistant": 830},
  "metrics": {"cv_AUPRC": 0.74, "cv_AUROC": 0.88, "evaluation": "5-fold CV on 2015-2017"}
}
```

| Key | Meaning |
| --- | --- |
| `input` | `Raw-6000`, `Var-2000` or `PCA-200` |
| `regions` | Region ids 0-599 (region r covers 2000 + 30r to 2000 + 30(r + 1) Da). For PCA-200, component ids |
| `threshold` | Youden threshold from out-of-fold predictions on 2015-2017 |
| `score_type` | `decision` for LR and SVM (decision_function), `probability` for RF, XGBoost, LightGBM, MLP |
| `indeterminate_band` | Optional `[low, high]` on the score scale. Scores inside it are reported as indeterminate |
| `metrics` | Cross-validation metrics. Add 2018 test metrics only after the final evaluation |

## model.joblib

A dictionary saved with `joblib.dump`, built exactly as `experiment3_optimisers.build_input` and
`evaluate` build the model:

| Key | Content |
| --- | --- |
| `scaler` | `StandardScaler` fitted on all 6,000 bins of the 2015-2017 spectra |
| `columns` | Input columns into the 6,000 bins (all bins for Raw-6000, top-variance bins for Var-2000). Omit for PCA-200 |
| `pca` | Fitted `PCA` for PCA-200, otherwise `None` |
| `selected` | Column positions inside the input that the chosen regions cover |
| `scaled` | `True` for LR, SVM and MLP; `False` for RF, XGBoost and LightGBM |
| `estimator` | The classifier fitted on all 2015-2017 spectra |

`model.joblib` is a Python pickle. Install only files made by the team's export script.
