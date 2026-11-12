"""Model registry: the only place where ATHAR learns which prediction models exist.

Each antibiotic has its own folder in athar_web/models/ (see models/README.md):

    models/<Antibiotic_name>/model.json     description, threshold, training metrics
    models/<Antibiotic_name>/model.joblib   fitted objects (scaler, PCA or columns, estimator)

The registry reproduces the inference path of experiment3_optimisers.evaluate():
StandardScaler fitted on the training years -> input columns (Raw-6000 / Var-2000) or PCA (PCA-200)
-> selected columns -> estimator. Scaled features go to LR, SVM and MLP; tree models get unscaled features.
Scores use decision_function for LR and SVM, predict_proba[:, 1] for the others, exactly as in training,
so the stored Youden threshold applies to the same scale.

model.joblib files are Python pickles. Only install files produced by the team's own export script.
"""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

log = logging.getLogger("athar.registry")

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = Path(os.environ.get("ATHAR_MODELS_DIR", BASE_DIR / "models"))

N_BINS = 6000
SCHEMA_VERSION = 1
INPUTS = ("Raw-6000", "Var-2000", "PCA-200")

# The 13 antibiotics of the project (same order as common.ANTIBIOTICS) and their drug class.
ANTIBIOTICS = {
    "Ciprofloxacin": "Fluoroquinolone",
    "Cefepime": "Fourth-generation cephalosporin",
    "Cotrimoxazole": "Folate pathway inhibitor",
    "Levofloxacin": "Fluoroquinolone",
    "Ceftazidime": "Third-generation cephalosporin",
    "Ceftriaxone": "Third-generation cephalosporin",
    "Tobramycin": "Aminoglycoside",
    "Amikacin": "Aminoglycoside",
    "Amoxicillin-Clavulanic acid": "Penicillin with beta-lactamase inhibitor",
    "Piperacillin-Tazobactam": "Penicillin with beta-lactamase inhibitor",
    "Ampicillin-Amoxicillin": "Aminopenicillin",
    "Cefpodoxime": "Third-generation cephalosporin",
    "Norfloxacin": "Fluoroquinolone",
}

REQUIRED_KEYS = ("schema_version", "antibiotic", "model_version", "input", "classifier",
                 "regions", "threshold", "score_type", "metrics")


def folder_name(antibiotic):
    """'Amoxicillin-Clavulanic acid' -> 'Amoxicillin-Clavulanic_acid' (same rule as the experiment outputs)."""
    return antibiotic.replace(" ", "_")


def mz_range(region):
    """m/z window of a region of 10 bins (common.mz_range)."""
    return 2000 + 30 * region, 2000 + 30 * (region + 1)


@dataclass
class Model:
    antibiotic: str
    meta: dict
    parts: dict = field(repr=False)

    @property
    def uses_mz_regions(self):
        return self.meta["input"] != "PCA-200"

    def score(self, spectrum):
        """Score one spectrum of 6,000 intensities on the same scale as the training threshold."""
        x = np.asarray(spectrum, dtype=np.float32).reshape(1, -1)
        z = self.parts["scaler"].transform(x).astype(np.float32)
        if self.parts.get("pca") is not None:
            features = self.parts["pca"].transform(z).astype(np.float32)
        else:
            cols = self.parts["columns"]
            features = z[:, cols] if self.parts["scaled"] else x[:, cols]
        features = features[:, self.parts["selected"]]
        estimator = self.parts["estimator"]
        if self.meta["score_type"] == "decision":
            return float(estimator.decision_function(features)[0])
        return float(estimator.predict_proba(features)[0, 1])

    def predict(self, spectrum):
        value = self.score(spectrum)
        threshold = float(self.meta["threshold"])
        band = self.meta.get("indeterminate_band")
        if band and band[0] <= value < band[1]:
            call = "I"
        else:
            call = "R" if value >= threshold else "S"
        return {
            "antibiotic": self.antibiotic,
            "call": call,
            "score": round(value, 6),
            "score_type": self.meta["score_type"],
            "threshold": threshold,
            "model_version": self.meta["model_version"],
        }

    def summary(self):
        m = self.meta
        return {
            "model_version": m["model_version"],
            "input": m["input"],
            "classifier": m["classifier"],
            "n_regions": len(m["regions"]),
            "metrics": m["metrics"],
            "training": m.get("training", {}),
        }


def _check_meta(meta, antibiotic):
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise ValueError(f"model.json is missing {missing}")
    if meta["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version {meta['schema_version']} is not supported (expected {SCHEMA_VERSION})")
    if meta["antibiotic"] != antibiotic:
        raise ValueError(f"model.json is for {meta['antibiotic']!r}, not {antibiotic!r}")
    if meta["input"] not in INPUTS:
        raise ValueError(f"unknown input {meta['input']!r}")
    if meta["score_type"] not in ("decision", "probability"):
        raise ValueError("score_type must be 'decision' or 'probability'")
    if not meta["regions"]:
        raise ValueError("regions is empty")
    limit = 200 if meta["input"] == "PCA-200" else N_BINS // 10
    if any(not (0 <= int(r) < limit) for r in meta["regions"]):
        raise ValueError("regions contains an index out of range")


def _check_parts(parts):
    for key in ("scaler", "selected", "scaled", "estimator"):
        if key not in parts:
            raise ValueError(f"model.joblib is missing {key!r}")
    if parts.get("pca") is None and "columns" not in parts:
        raise ValueError("model.joblib needs 'columns' (Raw-6000 / Var-2000) or 'pca' (PCA-200)")


def load_model(antibiotic, models_dir=None):
    import joblib

    folder = Path(models_dir or MODELS_DIR) / folder_name(antibiotic)
    meta_path, parts_path = folder / "model.json", folder / "model.joblib"
    if not meta_path.is_file() or not parts_path.is_file():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    _check_meta(meta, antibiotic)
    parts = joblib.load(parts_path)
    _check_parts(parts)
    model = Model(antibiotic, meta, parts)
    model.score(np.zeros(N_BINS, dtype=np.float32))          # fails now, not during an analysis
    return model


class Registry:
    def __init__(self, models_dir=None):
        self.models_dir = Path(models_dir or MODELS_DIR)
        self.models, self.errors = {}, {}
        self.reload()

    def reload(self):
        self.models, self.errors = {}, {}
        for antibiotic in ANTIBIOTICS:
            try:
                model = load_model(antibiotic, self.models_dir)
            except Exception as error:                     # a broken model must not stop the site
                self.errors[antibiotic] = str(error)
                log.error("Model for %s not loaded: %s", antibiotic, error)
                continue
            if model is not None:
                self.models[antibiotic] = model

    @property
    def installed(self):
        return [a for a in ANTIBIOTICS if a in self.models]

    def predict(self, spectrum):
        return [self.models[a].predict(spectrum) for a in self.installed]

    def catalogue(self):
        """All 13 antibiotics with their class and model status, for pages and the API."""
        rows = []
        for antibiotic, drug_class in ANTIBIOTICS.items():
            model = self.models.get(antibiotic)
            status = "installed" if model else ("error" if antibiotic in self.errors else "not_installed")
            rows.append({
                "antibiotic": antibiotic,
                "drug_class": drug_class,
                "status": status,
                "model": model.summary() if model else None,
            })
        return rows
