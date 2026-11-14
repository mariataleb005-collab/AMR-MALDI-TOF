"""Automated tests for the ATHAR web system.

Run from the repository root:
    python -m pytest athar_web/tests -q

The tests build small dummy models from random data in a temporary folder and use a temporary history
database, so they never touch athar_web/models/ or athar_web/history.sqlite3.
"""
import json
import os
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

WORK = Path(tempfile.mkdtemp(prefix="athar_tests_"))
MODELS = WORK / "models"
os.environ["ATHAR_MODELS_DIR"] = str(MODELS)
os.environ["ATHAR_DB_PATH"] = str(WORK / "history.sqlite3")

RNG = np.random.default_rng(0)
X_TRAIN = RNG.gamma(2, 0.0004, (150, 6000)).astype(np.float32)
Y_TRAIN = RNG.integers(0, 2, 150)
X_NEW = RNG.gamma(2, 0.0004, (3, 6000)).astype(np.float32)
META = dict(schema_version=1, model_version="TEST", selector="test", seed=0,
            training={"years": "test", "n_spectra": 150, "n_resistant": int(Y_TRAIN.sum())},
            metrics={"cv_AUPRC": 0.5, "evaluation": "dummy"})
EXPECTED = {}          # antibiotic -> scores computed the way experiment3_optimisers.evaluate() does


def save(antibiotic, meta, parts):
    folder = MODELS / antibiotic.replace(" ", "_")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "model.json").write_text(json.dumps(dict(META, antibiotic=antibiotic, **meta)))
    joblib.dump(parts, folder / "model.joblib")


def build_models():
    scaler = StandardScaler().fit(X_TRAIN)
    z_train, z_new = scaler.transform(X_TRAIN).astype(np.float32), scaler.transform(X_NEW).astype(np.float32)

    # Raw-6000 with logistic regression (scaled features, decision function)
    regions = [3, 40, 41, 200]
    cols = np.arange(6000)
    selected = np.concatenate([np.arange(10 * r, 10 * r + 10) for r in regions])
    lr = LogisticRegression(C=0.1, class_weight="balanced", max_iter=3000).fit(z_train[:, selected], Y_TRAIN)
    save("Ceftriaxone", dict(input="Raw-6000", classifier="LR", regions=regions, threshold=0.0,
                             score_type="decision"),
         dict(scaler=scaler, columns=cols, pca=None, selected=selected, scaled=True, estimator=lr))
    EXPECTED["Ceftriaxone"] = lr.decision_function(z_new[:, selected])

    # Var-2000 with random forest (unscaled features, probability)
    cols = np.sort(np.argsort(X_TRAIN.var(0))[::-1][:2000])
    groups = [np.flatnonzero(cols // 10 == r) for r in range(600)]
    regions = [r for r in range(600) if len(groups[r])][:5]
    selected = np.concatenate([groups[r] for r in regions])
    rf = RandomForestClassifier(30, random_state=0).fit(X_TRAIN[:, cols][:, selected], Y_TRAIN)
    save("Amikacin", dict(input="Var-2000", classifier="RF", regions=regions, threshold=0.5,
                          score_type="probability"),
         dict(scaler=scaler, columns=cols, pca=None, selected=selected, scaled=False, estimator=rf))
    EXPECTED["Amikacin"] = rf.predict_proba(X_NEW[:, cols][:, selected])[:, 1]

    # PCA-200 with logistic regression
    pca = PCA(100, random_state=0).fit(z_train)
    selected = np.array([0, 1, 5])
    lr2 = LogisticRegression(C=0.1, class_weight="balanced", max_iter=3000).fit(
        pca.transform(z_train)[:, selected], Y_TRAIN)
    save("Tobramycin", dict(input="PCA-200", classifier="LR", regions=[0, 1, 5], threshold=0.0,
                            score_type="decision"),
         dict(scaler=scaler, pca=pca, selected=selected, scaled=True, estimator=lr2))
    EXPECTED["Tobramycin"] = lr2.decision_function(pca.transform(z_new).astype(np.float32)[:, selected])

    # A broken model: listed as an error, never loaded
    folder = MODELS / "Cefepime"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "model.json").write_text(json.dumps(dict(META, antibiotic="Cefepime")))
    joblib.dump({}, folder / "model.joblib")


build_models()

from fastapi.testclient import TestClient  # noqa: E402  (imported after the environment is set)

from athar_web import main  # noqa: E402
from athar_web.predict import parse_spectrum  # noqa: E402
from athar_web.registry import Registry  # noqa: E402

client = TestClient(main.app)


def csv_bytes(values):
    return "\n".join(f"{v:.8f}" for v in values).encode()


# ---------------------------------------------------------------- registry

@pytest.mark.parametrize("antibiotic", ["Ceftriaxone", "Amikacin", "Tobramycin"])
def test_registry_reproduces_training_scores(antibiotic):
    model = main.registry.models[antibiotic]
    got = np.array([model.score(x) for x in X_NEW])
    assert np.allclose(got, EXPECTED[antibiotic], atol=1e-5)


def test_broken_model_is_reported_not_loaded():
    assert "Cefepime" not in main.registry.models
    assert "Cefepime" in main.registry.errors
    statuses = {row["antibiotic"]: row["status"] for row in main.registry.catalogue()}
    assert statuses["Cefepime"] == "error"
    assert statuses["Ceftriaxone"] == "installed"
    assert statuses["Ciprofloxacin"] == "not_installed"
    assert len(statuses) == 13


def test_explanation_matches_masking_the_spectrum():
    model = main.registry.models["Ceftriaxone"]
    x = X_NEW[0]
    base, mean = model.score(x), model.parts["scaler"].mean_
    for item in model.explain(x):
        r = item["unit"]
        masked = x.copy()
        masked[10 * r:10 * r + 10] = mean[10 * r:10 * r + 10]
        assert abs((base - model.score(masked)) - item["effect"]) < 1e-5


def test_calls_follow_the_threshold():
    for x in X_NEW:
        for result in main.registry.predict(x):
            expected = "R" if result["score"] >= result["threshold"] else "S"
            assert result["call"] == expected


# ---------------------------------------------------------------- file checks

def test_parse_accepts_a_valid_spectrum():
    assert len(parse_spectrum(csv_bytes(X_NEW[0]), "s.csv")) == 6000


@pytest.mark.parametrize("content, name, message", [
    (b"1,2,3", "s.csv", "Expected 6000"),
    (csv_bytes([-1.0] * 6000), "s.csv", "non-negative"),
    (b"a,b,c", "s.csv", "numeric"),
    (csv_bytes(X_NEW[0]), "s.xlsx", "Only .csv and .txt"),
    (b"", "s.csv", "non-empty"),
])
def test_parse_rejects_bad_files(content, name, message):
    with pytest.raises(ValueError, match=message):
        parse_spectrum(content, name)


# ---------------------------------------------------------------- API and pages

def analyze(species="Escherichia coli", content=None, name="sample.csv"):
    return client.post("/api/predict", data={"sample_id": "LAB-TEST", "species": species},
                       files={"file": (name, content or csv_bytes(X_NEW[0]), "text/csv")})


def test_analysis_end_to_end():
    response = analyze()
    assert response.status_code == 200
    data = response.json()
    assert {r["antibiotic"] for r in data["results"]} == {"Ceftriaxone", "Amikacin", "Tobramycin"}
    assert all(r["explanation"] for r in data["results"])
    for path in (data["url"], data["url"] + "/report", f"/api/analysis/{data['analysis_id']}/spectrum"):
        assert client.get(path).status_code == 200
    record = client.get(f"/api/history/{data['analysis_id']}").json()
    assert record["sample_id"] == "LAB-TEST"
    assert "LAB-TEST" in client.get("/api/history/export").text


def test_other_species_is_refused():
    response = analyze(species="Other")
    assert response.status_code == 400
    assert "Escherichia coli only" in response.json()["detail"]


def test_invalid_file_is_refused():
    assert analyze(content=b"1,2,3").status_code == 400


def test_no_model_installed(monkeypatch):
    monkeypatch.setattr(main, "registry", Registry(WORK / "empty_models"))
    response = analyze()
    assert response.status_code == 503
    assert "no prediction model is installed" in response.json()["detail"]


@pytest.mark.parametrize("path", ["/", "/antibiotics", "/antibiotic/ceftriaxone", "/antibiotic/cefepime",
                                  "/antibiotic/amoxicillin-clavulanic-acid", "/history", "/about",
                                  "/api/antibiotics"])
def test_pages_open(path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/antibiotic/unknown", "/analysis/999999", "/analysis/999999/report"])
def test_unknown_pages_return_404(path):
    assert client.get(path).status_code == 404
