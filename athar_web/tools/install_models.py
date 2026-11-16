"""Install the team's exported models (export_athar_models.py output) into ATHAR's model registry.

Run once from the repository root, after export_athar_models.py, with the same spectra and labels:

    python -m athar_web.tools.install_models "<spectra folder>" data/labels_ecoli_A_corrected.csv models/athar

For each antibiotic in models/athar/manifest.json it:
  1. loads <Antibiotic>.joblib (classifier, bins, regions, threshold, CV metrics);
  2. computes the average intensity of each of the model's bins over the 2015-2017 spectra labelled for that
     antibiotic (the same rows the model was trained on). ATHAR uses these averages for the explanations;
  3. writes athar_web/models/<Antibiotic>/model.json and model.joblib;
  4. checks that ATHAR's score equals export_athar_models.predict() on 20 training spectra.

The 2018 spectra are never used. Existing folders in athar_web/models/ are replaced.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from athar_web.registry import ANTIBIOTICS, MODELS_DIR, folder_name, load_model

N_BINS, TEST_YEAR = 6000, 2018


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data_dir", help="folder that holds spectra_ecoli_A.npy")
    parser.add_argument("labels_csv", help="data/labels_ecoli_A_corrected.csv")
    parser.add_argument("bundles", help="output folder of export_athar_models.py, e.g. models/athar")
    parser.add_argument("--target", default=str(MODELS_DIR), help="ATHAR models folder (default athar_web/models)")
    args = parser.parse_args()

    bundles, target = Path(args.bundles), Path(args.target)
    manifest = json.loads((bundles / "manifest.json").read_text(encoding="utf-8"))
    spectra = np.load(Path(args.data_dir) / "spectra_ecoli_A.npy", mmap_mode="r")
    labels = pd.read_csv(args.labels_csv)
    if spectra.shape != (len(labels), N_BINS):
        sys.exit(f"spectra {spectra.shape} do not match the labels ({len(labels)} rows, {N_BINS} bins)")

    installed = []
    for antibiotic, entry in manifest["antibiotics"].items():
        if antibiotic not in ANTIBIOTICS:
            sys.exit(f"{antibiotic} is not one of ATHAR's antibiotics")
        bundle = joblib.load(bundles / entry["file"])
        bins = np.asarray(bundle["bins"], dtype=int)

        # training rows only (same rule as export_athar_models.py); 2018 is never read
        train = np.flatnonzero((labels[antibiotic].notna() & (labels["year"] < TEST_YEAR)).to_numpy())
        if len(train) != bundle["n_train"]:
            sys.exit(f"[{antibiotic}] {len(train)} training spectra, but the model was trained on {bundle['n_train']}")
        bin_means = np.asarray(spectra[train][:, bins], dtype=np.float64).mean(0).astype(np.float32)

        cv = bundle["cv"][bundle["classifier"]]
        meta = {
            "schema_version": 1,
            "antibiotic": antibiotic,
            "model_version": f"{bundle['algorithm']}-{bundle['input']}-{bundle['created'][:10]}",
            "input": bundle["input"],
            "selector": bundle["algorithm"],
            "classifier": bundle["classifier"],
            "regions": [int(r) for r in bundle["regions"]],
            "region_votes": {str(i["region"]): i["votes"] for i in bundle["region_info"]},
            "region_rule": bundle["region_rule"],
            "threshold": float(bundle["threshold"]),
            "threshold_rule": bundle["threshold_rule"],
            "score_type": "probability",
            "indeterminate_band": None,
            "training": {"years": bundle["train_years"], "n_spectra": bundle["n_train"],
                         "n_resistant": bundle["n_train_nonS"]},
            "metrics": {"cv_AUPRC": cv["cv_AUPRC"], "cv_AUROC": cv["cv_AUROC"],
                        "evaluation": "5-fold CV on 2015-2017"},
            "source": {"file": entry["file"], "commit": bundle["commit"], "created": bundle["created"],
                       "versions": bundle["versions"]},
        }
        parts = {"bins": bins, "bin_means": bin_means, "estimator": bundle["model"]}

        folder = target / folder_name(antibiotic)
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        (folder / "model.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        joblib.dump(parts, folder / "model.joblib", compress=3)

        # check: ATHAR's score equals the export script's predict() on 20 training spectra
        model = load_model(antibiotic, target)
        for i in train[:20]:
            x = np.asarray(spectra[i], dtype=np.float32)
            expected = float(bundle["model"].predict_proba(x[bins][None, :])[0, 1])
            if abs(model.score(x) - expected) > 1e-6:
                sys.exit(f"[{antibiotic}] check failed: ATHAR does not reproduce the exported model's score")
        installed.append(antibiotic)
        print(f"[{antibiotic}] {bundle['classifier']}, {len(bundle['regions'])} regions, "
              f"threshold {bundle['threshold']:.3f}, CV AUPRC {cv['cv_AUPRC']:.3f}  check OK", flush=True)

    print(f"Installed {len(installed)} models into {target}. Restart ATHAR to load them.")


if __name__ == "__main__":
    main()
