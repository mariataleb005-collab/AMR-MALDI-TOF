"""Shared data protocol for all experiments (Exp 0).

Protocol (fixed for every step of the paper):
  * labels: S = 0, I or R = 1 (Weis et al. 2022; NCA 2026), NaN = not tested
  * split : train = 2015-2017, test = 2018 (never used for tuning or selection)
  * folds : 5 stratified folds inside the training years, fixed seed
  * m/z   : bin b covers [2000 + 3b, 2000 + 3(b+1)) Da; region r = bins 10r..10r+9
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (roc_auc_score, average_precision_score, matthews_corrcoef,
                             balanced_accuracy_score, roc_curve)

ANTIBIOTICS = ['Ciprofloxacin', 'Ceftriaxone', 'Cefepime', 'Piperacillin-Tazobactam',
               'Tobramycin', 'Ampicillin-Amoxicillin']
N_BINS, REGION = 6000, 10
N_REGIONS = N_BINS // REGION
TEST_YEAR = 2018
SEED = 0


def load_spectra(data_dir):
    return np.load(f'{data_dir}/spectra_ecoli_A.npy', mmap_mode='r')


def load_labels(labels_csv):
    return pd.read_csv(labels_csv)


def get_task(X, L, abx):
    """Return train/test arrays for one antibiotic (rows with a label only)."""
    lab = L[abx].notna().values
    tr = lab & (L['year'].values < TEST_YEAR)
    te = lab & (L['year'].values == TEST_YEAR)
    Xtr = np.asarray(X[tr], dtype=np.float32)
    Xte = np.asarray(X[te], dtype=np.float32)
    ytr = L.loc[tr, abx].values.astype(int)
    yte = L.loc[te, abx].values.astype(int)
    return Xtr, ytr, Xte, yte


def train_folds(y, n_splits=5, seed=SEED):
    return list(StratifiedKFold(n_splits, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))


def region_to_bins(regions):
    regions = np.asarray(regions, dtype=int)
    return (regions[:, None] * REGION + np.arange(REGION)[None, :]).ravel()


def mz_range(region):
    return 2000 + 3 * REGION * region, 2000 + 3 * REGION * (region + 1)


def youden_threshold(y, p):
    fpr, tpr, thr = roc_curve(y, p)
    return float(thr[np.argmax(tpr - fpr)])


def scores(y, p, thr=None):
    out = {'AUROC': roc_auc_score(y, p), 'AUPRC': average_precision_score(y, p)}
    if thr is not None:
        yh = (p >= thr).astype(int)
        tp = ((yh == 1) & (y == 1)).sum(); fn = ((yh == 0) & (y == 1)).sum()
        tn = ((yh == 0) & (y == 0)).sum(); fp = ((yh == 1) & (y == 0)).sum()
        out.update({'MCC': matthews_corrcoef(y, yh), 'BalAcc': balanced_accuracy_score(y, yh),
                    'Sens': tp / max(tp + fn, 1), 'Spec': tn / max(tn + fp, 1),
                    # very major error = resistant called susceptible; major = the reverse
                    'VME': fn / max(tp + fn, 1), 'ME': fp / max(tn + fp, 1)})
    return out


def nogueira_stability(masks):
    """Nogueira et al. (2018) stability of a set of binary selection masks (M x d)."""
    Z = np.asarray(masks, dtype=float)
    M, d = Z.shape
    if M < 2:
        return np.nan
    kbar = Z.sum(1).mean()
    if kbar in (0, d):
        return np.nan
    s2 = Z.var(0, ddof=1)
    return 1 - s2.mean() / ((kbar / d) * (1 - kbar / d))
