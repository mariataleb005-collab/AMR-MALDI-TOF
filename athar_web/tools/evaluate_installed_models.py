"""Score ATHAR's installed models once on the held-out 2018 spectra.

Run once from the repository root, after install_models.py:

    python -m athar_web.tools.evaluate_installed_models "<spectra folder>" data/labels_ecoli_A_corrected.csv

For each installed model it scores the 2018 spectra labelled for that antibiotic, with the threshold fixed
on 2015-2017, and:
  1. adds the 2018 metrics to athar_web/models/<Antibiotic>/model.json (shown on the Antibiotics pages);
  2. writes results/athar_test_eval/test_metrics.csv (one row per antibiotic, for the report);
  3. writes results/athar_test_eval/test_predictions.csv (one row per 2018 spectrum and antibiotic: row in
     the spectra file, true label, score, call, correct or not). Use it to choose the demo spectrum.

Nothing is refitted and no threshold changes: the 2018 data are only scored.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, f1_score, matthews_corrcoef,
                             roc_auc_score)

from athar_web.registry import MODELS_DIR, Registry, folder_name

TEST_YEAR = 2018


def metrics(y, p, threshold):
    """Same definitions as common.scores() in the experiments."""
    yh = (p >= threshold).astype(int)
    tp = int(((yh == 1) & (y == 1)).sum()); fn = int(((yh == 0) & (y == 1)).sum())
    tn = int(((yh == 0) & (y == 0)).sum()); fp = int(((yh == 1) & (y == 0)).sum())
    return {
        "test_AUROC": float(roc_auc_score(y, p)),
        "test_AUPRC": float(average_precision_score(y, p)),
        "test_BalAcc": float(balanced_accuracy_score(y, yh)),
        "test_MCC": float(matthews_corrcoef(y, yh)),
        "test_F1": float(f1_score(y, yh, zero_division=0)),
        "test_Sens": tp / max(tp + fn, 1),
        "test_Spec": tn / max(tn + fp, 1),
        "test_VME": fn / max(tp + fn, 1),          # resistant called susceptible
        "test_ME": fp / max(tn + fp, 1),           # susceptible called resistant
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data_dir", help="folder that holds spectra_ecoli_A.npy")
    parser.add_argument("labels_csv", help="data/labels_ecoli_A_corrected.csv")
    parser.add_argument("--out", default="results/athar_test_eval", help="folder for the two CSV files")
    args = parser.parse_args()

    spectra = np.load(Path(args.data_dir) / "spectra_ecoli_A.npy", mmap_mode="r")
    labels = pd.read_csv(args.labels_csv)
    registry = Registry(MODELS_DIR)
    if not registry.installed:
        raise SystemExit("No models are installed. Run install_models.py first.")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    table, rows = [], []
    for antibiotic in registry.installed:
        model = registry.models[antibiotic]
        test = np.flatnonzero((labels[antibiotic].notna() & (labels["year"] == TEST_YEAR)).to_numpy())
        y = labels.loc[test, antibiotic].to_numpy().astype(int)
        p = np.array([model.score(np.asarray(spectra[i], dtype=np.float32)) for i in test])
        threshold = float(model.meta["threshold"])
        m = metrics(y, p, threshold)

        meta_path = MODELS_DIR / folder_name(antibiotic) / "model.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["metrics"].update({k: round(v, 4) for k, v in m.items()})
        meta["metrics"]["test_evaluation"] = f"2018, {len(test)} spectra ({int(y.sum())} resistant), scored once"
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        table.append({"antibiotic": antibiotic, "classifier": meta["classifier"], "n_test": len(test),
                      "n_test_resistant": int(y.sum()), "threshold": threshold,
                      "cv_AUPRC": meta["metrics"]["cv_AUPRC"], **m})
        for i, label, score in zip(test, y, p):
            call = int(score >= threshold)
            rows.append({"antibiotic": antibiotic, "spectrum_row": int(i), "code": labels.at[i, "code"]
                         if "code" in labels.columns else "", "true": "R" if label else "S",
                         "score": round(float(score), 4), "call": "R" if call else "S",
                         "correct": bool(call == label)})
        print(f"[{antibiotic}] n={len(test)} ({int(y.sum())} R)  AUROC {m['test_AUROC']:.3f}  "
              f"AUPRC {m['test_AUPRC']:.3f}  Sens {m['test_Sens']:.3f}  Spec {m['test_Spec']:.3f}  "
              f"VME {m['test_VME']:.3f}", flush=True)

    pd.DataFrame(table).round(4).to_csv(out / "test_metrics.csv", index=False)
    pd.DataFrame(rows).to_csv(out / "test_predictions.csv", index=False)
    print(f"Written {out / 'test_metrics.csv'} and {out / 'test_predictions.csv'}; "
          f"model.json files updated. Restart ATHAR to show the 2018 metrics.")


if __name__ == "__main__":
    main()
