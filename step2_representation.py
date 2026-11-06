"""Step 2 (Exp 1) - Which input works best for full-spectrum models?

Inputs : raw 6,000 bins | variance top-k (500/1,000/2,000) | PCA (50/100/200)
Models : LR, SVM-RBF, RF, XGBoost, LightGBM, MLP (class weights on where supported)
Protocol:
  1. 5-fold stratified CV inside 2015-2017 for every (input, model, hyper-parameter).
     Every transform (variance ranking, PCA, scaling) is fitted inside the training fold.
  2. Per (input, model) keep the hyper-parameter with the best mean CV AUPRC.
  3. Refit it on all 2015-2017 data and score the 2018 hold-out once.
     The decision threshold is Youden's J on the out-of-fold CV predictions (not 0.5).

Usage: python step2_representation.py <data_dir> <labels_csv> <out_dir> [antibiotic ...]
"""
import os, sys, time, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.base import BaseEstimator, TransformerMixin, clone
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import common as C

warnings.filterwarnings('ignore')


class TopVariance(BaseEstimator, TransformerMixin):
    def __init__(self, k=1000):
        self.k = k

    def fit(self, X, y=None):
        self.idx_ = np.sort(np.argsort(X.var(0))[::-1][:self.k])
        return self

    def transform(self, X):
        return X[:, self.idx_]


INPUTS = {
    'Raw-6000': lambda: [],
    'Var-500': lambda: [TopVariance(500)],
    'Var-1000': lambda: [TopVariance(1000)],
    'Var-2000': lambda: [TopVariance(2000)],
    'PCA-50': lambda: [PCA(50, random_state=0)],
    'PCA-100': lambda: [PCA(100, random_state=0)],
    'PCA-200': lambda: [PCA(200, random_state=0)],
}


def models(pos_weight):
    """name -> list of (config label, estimator, needs_scaling)."""
    return {
        'LR': [(f'C={c}', LogisticRegression(C=c, class_weight='balanced', max_iter=3000), True)
               for c in (0.01, 0.1, 1.0)],
        'SVM': [(f'C={c}', SVC(C=c, kernel='rbf', gamma='scale', class_weight='balanced'), True)
                for c in (0.1, 1.0, 10.0)],
        'RF': [('trees=300', RandomForestClassifier(300, max_features='sqrt',
                                                    class_weight='balanced_subsample',
                                                    n_jobs=1, random_state=0), False)],
        'XGBoost': [(f'depth={d}', XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=d,
                                                 subsample=0.8, colsample_bytree=0.3,
                                                 scale_pos_weight=pos_weight, tree_method='hist',
                                                 n_jobs=1, random_state=0, verbosity=0), False)
                    for d in (4, 6)],
        'LightGBM': [(f'leaves={n}', LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=n,
                                                    colsample_bytree=0.3, subsample=0.8,
                                                    subsample_freq=1, class_weight='balanced',
                                                    n_jobs=1, random_state=0, verbose=-1), False)
                     for n in (15, 31)],
        'MLP': [(f'alpha={a}', MLPClassifier((256,), alpha=a, early_stopping=True, max_iter=300,
                                             random_state=0), True)
                for a in (1e-3, 1e-1)],
    }


def build(inp, est, scale):
    steps = INPUTS[inp]() + ([StandardScaler()] if scale else []) + [clone(est)]
    return make_pipeline(*steps)


def predict_score(pipe, X):
    if hasattr(pipe, 'predict_proba'):
        try:
            return pipe.predict_proba(X)[:, 1]
        except AttributeError:
            pass
    return pipe.decision_function(X)


def run_fold(Xtr, ytr, tr_idx, va_idx, inp, est, scale):
    t = time.time()
    pipe = build(inp, est, scale).fit(Xtr[tr_idx], ytr[tr_idx])
    p = predict_score(pipe, Xtr[va_idx])
    return va_idx, p, time.time() - t


def run_test(Xtr, ytr, Xte, yte, inp, est, scale, thr):
    t = time.time()
    pipe = build(inp, est, scale).fit(Xtr, ytr)
    p = predict_score(pipe, Xte)
    return C.scores(yte, p, thr), time.time() - t


def main():
    data_dir, labels_csv, out_dir = sys.argv[1:4]
    abx_list = sys.argv[4:] or C.ANTIBIOTICS
    os.makedirs(out_dir, exist_ok=True)
    X, L = C.load_spectra(data_dir), C.load_labels(labels_csv)
    n_jobs = max(1, (os.cpu_count() or 2) - 1)
    for abx in abx_list:
        Xtr, ytr, Xte, yte = C.get_task(X, L, abx)
        folds = C.train_folds(ytr)
        M = models((ytr == 0).sum() / max((ytr == 1).sum(), 1))
        jobs = [(inp, m, cfg, est, sc) for inp in INPUTS for m, lst in M.items() for cfg, est, sc in lst]
        print(f'[{abx}] train {len(ytr)} ({ytr.sum()} R)  test {len(yte)} ({yte.sum()} R)  '
              f'{len(jobs)} configs x 5 folds', flush=True)
        t0 = time.time()
        res = Parallel(n_jobs=n_jobs)(delayed(run_fold)(Xtr, ytr, tr, va, inp, est, sc)
                                      for inp, m, cfg, est, sc in jobs for tr, va in folds)
        cv_rows, best = [], {}
        for j, (inp, m, cfg, est, sc) in enumerate(jobs):
            oof = np.zeros(len(ytr))
            fold_ap = []
            for f in range(5):
                va, p, sec = res[j * 5 + f]
                oof[va] = p
                s = C.scores(ytr[va], p)
                fold_ap.append(s['AUPRC'])
                cv_rows.append({'antibiotic': abx, 'input': inp, 'model': m, 'config': cfg, 'fold': f,
                                'AUROC': s['AUROC'], 'AUPRC': s['AUPRC'], 'fit_sec': sec})
            key = (inp, m)
            if key not in best or np.mean(fold_ap) > best[key][0]:
                best[key] = (np.mean(fold_ap), np.std(fold_ap), cfg, est, sc, C.youden_threshold(ytr, oof))
        pd.DataFrame(cv_rows).to_csv(f'{out_dir}/step2_cv_{abx}.csv', index=False)
        keys = list(best)
        tres = Parallel(n_jobs=n_jobs)(delayed(run_test)(Xtr, ytr, Xte, yte, inp, best[(inp, m)][3],
                                                         best[(inp, m)][4], best[(inp, m)][5])
                                       for inp, m in keys)
        rows = []
        for (inp, m), (s, sec) in zip(keys, tres):
            cvm, cvs, cfg = best[(inp, m)][:3]
            rows.append({'antibiotic': abx, 'input': inp, 'model': m, 'best_config': cfg,
                         'cv_AUPRC_mean': cvm, 'cv_AUPRC_sd': cvs,
                         **{f'test_{k}': v for k, v in s.items()}, 'refit_sec': sec})
        pd.DataFrame(rows).to_csv(f'{out_dir}/step2_test_{abx}.csv', index=False)
        print(f'[{abx}] done in {(time.time() - t0) / 60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
