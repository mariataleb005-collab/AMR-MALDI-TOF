"""Step 3 (Exp 2) - Does the proposed region-aware PSO beat other selectors at the same budget?

ONE fitness function for every wrapper (and it is also reported for the filters):
    F(S) = mean AUPRC of a class-balanced logistic regression (C = 0.1) over 3 fixed
           stratified folds of the selection data, using the bins in S
           - LAMBDA * |S| / 6000                      (|S| = number of selected bins)
The penalty is what drives the search towards a small signature.

Selectors (all see only the 2015-2017 data; 2018 is used once, for scoring):
  wrappers, same budget of fitness calls, same fitness, same initial-density rule
    * RA-PSO (proposed)  regions of 10 bins, ANOVA-seeded particle, V-shaped transfer,
                         diversity-adaptive inertia, restarts, 3-run stability vote
    * BPSO-bins          standard binary PSO (sigmoid transfer) on 6,000 bins
    * BPSO-regions       standard binary PSO on 600 regions
    * GA-regions         binary genetic algorithm on 600 regions
    * GWO-regions        binary grey wolf optimiser on 600 regions
  filters / embedded, k matched to the RA-PSO size of the same seed
    * ANOVA-bins, ANOVA-regions, L1-LR, LightGBM-gain, mRMR
  reference: all 6,000 bins

Each seed uses a different stratified 90 % subsample of 2015-2017 for selection, so the
3 seeds measure stability (Nogueira index) under data perturbation.
Every selected set is then scored on 2018 with the same 6 models.

Outputs (per antibiotic): step3_selections_<abx>.csv, step3_test_<abx>.csv,
                          step3_regions_<abx>.csv (the important-region table)

Usage: python step3_feature_selection.py <data_dir> <labels_csv> <out_dir> [antibiotic ...]
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
os.environ.setdefault('PYTHONWARNINGS', 'ignore')     # also silences the joblib workers
import sys, time, json, warnings
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import common as C

warnings.filterwarnings('ignore')

LAMBDA = float(os.environ.get('FS_LAMBDA', 0.2))   # size penalty weight (sensitivity: 0.05 / 0.2 / 0.5)
BUDGET = int(os.environ.get('FS_BUDGET', 2000))    # fitness calls per selector run, identical for every wrapper
POP = 20
SEEDS = (0, 1, 2)
SEED_REGIONS = 30     # ANOVA seed size for RA-PSO
INIT_DENSITY = (0.01, 0.5)   # every random particle/individual draws its density from here
WRAPPERS = ['RA-PSO', 'BPSO-bins', 'BPSO-regions', 'GA-regions', 'GWO-regions']
FILTERS = ['ANOVA-bins', 'ANOVA-regions', 'L1-LR', 'LightGBM-gain', 'mRMR']


# ---------------------------------------------------------------- fitness
class Fitness:
    """The single fitness function. Counts every call; refuses calls beyond the budget."""

    def __init__(self, Z, y, budget, unit):
        self.Z, self.y, self.budget, self.unit = Z, y, budget, unit
        self.folds = list(StratifiedKFold(3, shuffle=True, random_state=0).split(Z, y))
        self.calls = 0

    def bins(self, mask):
        idx = np.flatnonzero(mask)
        return C.region_to_bins(idx) if self.unit == 'region' else idx

    def auprc(self, cols):
        ap = []
        for tr, va in self.folds:
            m = LogisticRegression(C=0.1, class_weight='balanced', max_iter=200, tol=1e-3)
            m.fit(self.Z[np.ix_(tr, cols)], self.y[tr])
            ap.append(average_precision_score(self.y[va], m.decision_function(self.Z[np.ix_(va, cols)])))
        return float(np.mean(ap))

    def __call__(self, mask, count=True):
        if count:
            self.calls += 1
        cols = self.bins(mask)
        if len(cols) == 0:
            return -1.0
        return self.auprc(cols) - LAMBDA * len(cols) / C.N_BINS

    @property
    def left(self):
        return self.budget - self.calls


def random_masks(rng, n, d):
    dens = rng.uniform(*INIT_DENSITY, size=(n, 1))
    m = rng.random((n, d)) < dens
    m[~m.any(1), 0] = True
    return m


# ---------------------------------------------------------------- wrappers
def pso(fit, d, rng, budget, proposed, seed_mask=None):
    """proposed=False: standard BPSO (sigmoid transfer, fixed inertia).
       proposed=True : V-shaped transfer, diversity-adaptive inertia, restarts, seeded particle."""
    stop = fit.calls + budget
    X = random_masks(rng, POP, d)
    if seed_mask is not None:
        X[0] = seed_mask
    V = rng.uniform(-1, 1, (POP, d))
    f = np.array([fit(x) for x in X])
    P, pf = X.copy(), f.copy()
    g = int(np.argmax(pf)); G, gf = P[g].copy(), pf[g]
    c1 = c2 = 1.49445; vmax = 4.0
    div0 = max((X != G).mean(), 1e-9)                          # initial swarm diversity
    stall = 0
    while fit.calls + POP <= stop:
        if proposed:
            div = (X != G).mean()                              # Hamming diversity around the best
            w = 0.4 + 0.5 * min(div / div0, 1.0)               # diverse swarm -> explore, converged -> exploit
        else:
            w = 0.729
        r1, r2 = rng.random((POP, d)), rng.random((POP, d))
        V = np.clip(w * V + c1 * r1 * (P.astype(float) - X) + c2 * r2 * (G.astype(float) - X), -vmax, vmax)
        if proposed:
            X = np.where(rng.random((POP, d)) < np.abs(np.tanh(V)), ~X, X)   # V-shaped: flip bits
        else:
            X = rng.random((POP, d)) < 1 / (1 + np.exp(-V))                  # S-shaped: set bits
        X[~X.any(1), rng.integers(d)] = True
        f = np.array([fit(x) for x in X])
        imp = f > pf
        P[imp], pf[imp] = X[imp], f[imp]
        g = int(np.argmax(pf))
        if pf[g] > gf + 1e-6:
            G, gf, stall = P[g].copy(), pf[g], 0
        else:
            stall += 1
        if proposed and stall >= 5:                            # restart the worse half near G
            worst = np.argsort(pf)[:POP // 2]
            X[worst] = np.where(rng.random((len(worst), d)) < 0.02, ~G, G)
            V[worst] = rng.uniform(-1, 1, (len(worst), d))
            stall = 0
    return G, gf


def ga(fit, d, rng, budget):
    stop = fit.calls + budget
    X = random_masks(rng, POP, d)
    f = np.array([fit(x) for x in X])
    while fit.calls + POP - 1 <= stop:
        elite = int(np.argmax(f))
        kids = [X[elite].copy()]
        while len(kids) < POP:
            a, b = (max(rng.choice(POP, 3, replace=False), key=lambda i: f[i]) for _ in range(2))
            child = np.where(rng.random(d) < 0.5, X[a], X[b]) if rng.random() < 0.9 else X[a].copy()
            child ^= rng.random(d) < 1.0 / d * 2
            if not child.any():
                child[rng.integers(d)] = True
            kids.append(child)
        X = np.array(kids)
        f = np.concatenate([[f[elite]], [fit(x) for x in X[1:]]])
    i = int(np.argmax(f))
    return X[i], f[i]


def gwo(fit, d, rng, budget):
    """Binary GWO (Emary et al. 2016, approach 2: sigmoid transfer of the continuous update)."""
    stop = fit.calls + budget
    X = random_masks(rng, POP, d)
    f = np.array([fit(x) for x in X])
    n_iter = max((budget - POP) // POP, 1); it = 0
    best, bf = X[np.argmax(f)].copy(), f.max()
    while fit.calls + POP <= stop:
        a = 2 - 2 * it / n_iter; it += 1
        lead = X[np.argsort(f)[::-1][:3]].astype(float)
        Y = np.zeros((POP, d))
        for L in lead:
            A = 2 * a * rng.random((POP, d)) - a
            Cc = 2 * rng.random((POP, d))
            Y += L - A * np.abs(Cc * L - X)
        Y /= 3
        X = rng.random((POP, d)) < 1 / (1 + np.exp(-10 * (Y - 0.5)))
        X[~X.any(1), rng.integers(d)] = True
        f = np.array([fit(x) for x in X])
        if f.max() > bf:
            best, bf = X[np.argmax(f)].copy(), f.max()
    return best, bf


def ra_pso(Zs, ys, rng, budget, F_region_rank):
    """Proposed: 3 sub-runs on 80 % resamples (budget/3 each), keep regions chosen in >= 2,
    safeguard: if the voted set scores worse on the full selection data, keep the best run."""
    full = Fitness(Zs, ys, budget, 'region')
    seed = np.zeros(C.N_REGIONS, bool); seed[F_region_rank[:SEED_REGIONS]] = True
    sss = StratifiedShuffleSplit(3, train_size=0.8, random_state=int(rng.integers(10**9)))
    runs = []
    per_run = (budget - 3) // 3          # 2 calls kept for the safeguard comparison
    for sub, _ in sss.split(Zs, ys):
        fit = Fitness(Zs[sub], ys[sub], per_run, 'region')
        G, _ = pso(fit, C.N_REGIONS, rng, per_run, proposed=True, seed_mask=seed)
        runs.append(G); full.calls += fit.calls
    votes = np.sum(runs, 0)
    voted = votes >= 2
    cand = [voted] + runs if voted.any() else runs
    fs = [full(m) for m in cand]
    best = cand[int(np.argmax(fs))]
    return best, max(fs), full.calls, votes


# ---------------------------------------------------------------- filters
def mrmr(Z, y, k, pre=1000):
    F, _ = f_classif(Z, y); F = np.nan_to_num(F)
    cand = np.argsort(F)[::-1][:pre]
    Fn = F[cand] / F[cand].max()
    Zc = (Z[:, cand] - Z[:, cand].mean(0)) / (Z[:, cand].std(0) + 1e-9)
    sel = [0]; red = np.zeros(len(cand))
    while len(sel) < min(k, pre):
        red += np.abs(Zc.T @ Zc[:, sel[-1]]) / len(Z)
        score = Fn - red / len(sel); score[sel] = -np.inf
        sel.append(int(np.argmax(score)))
    return cand[sel]


def l1_select(Z, y, k):
    best = None
    for c in np.logspace(-3, 0, 13):
        m = LogisticRegression(penalty='l1', C=c, solver='liblinear', class_weight='balanced',
                               max_iter=500).fit(Z, y)
        nz = np.flatnonzero(m.coef_[0])
        if best is None or abs(len(nz) - k) < abs(len(best) - k):
            best = nz
        if len(nz) > 1.5 * k:
            break
    return best


def filter_select(name, Z, y, k, F):
    if name == 'ANOVA-bins':
        return np.sort(np.argsort(F)[::-1][:k])
    if name == 'ANOVA-regions':
        rF = F.reshape(C.N_REGIONS, C.REGION).mean(1)
        return C.region_to_bins(np.sort(np.argsort(rF)[::-1][:max(k // C.REGION, 1)]))
    if name == 'L1-LR':
        return np.sort(l1_select(Z, y, k))
    if name == 'LightGBM-gain':
        m = LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=15, colsample_bytree=0.3,
                           class_weight='balanced', importance_type='gain', n_jobs=1,
                           random_state=0, verbose=-1).fit(Z, y)
        return np.sort(np.argsort(m.feature_importances_)[::-1][:k])
    if name == 'mRMR':
        return np.sort(mrmr(Z, y, k))
    raise ValueError(name)


# ---------------------------------------------------------------- one selection run
def run_selector(name, seed, Ztr, ytr):
    rng = np.random.default_rng(1000 + seed)
    sub = next(StratifiedShuffleSplit(1, train_size=0.9, random_state=seed).split(Ztr, ytr))[0]
    Zs, ys = Ztr[sub], ytr[sub]
    F, _ = f_classif(Zs, ys); F = np.nan_to_num(F)
    rF = F.reshape(C.N_REGIONS, C.REGION).mean(1)
    t = time.time(); extra = {}
    if name == 'RA-PSO':
        mask, fval, calls, votes = ra_pso(Zs, ys, rng, BUDGET, np.argsort(rF)[::-1])
        bins = C.region_to_bins(np.flatnonzero(mask)); extra['votes'] = votes.tolist()
    elif name in WRAPPERS:
        unit = 'bin' if name.endswith('bins') else 'region'
        d = C.N_BINS if unit == 'bin' else C.N_REGIONS
        fit = Fitness(Zs, ys, BUDGET, unit)
        if name.startswith('BPSO'):
            mask, fval = pso(fit, d, rng, BUDGET, proposed=False)
        elif name == 'GA-regions':
            mask, fval = ga(fit, d, rng, BUDGET)
        else:
            mask, fval = gwo(fit, d, rng, BUDGET)
        bins, calls = fit.bins(mask), fit.calls
    return {'selector': name, 'seed': seed, 'bins': np.asarray(bins).tolist(), 'fitness': fval,
            'calls': calls, 'sec': time.time() - t, **extra}


def run_filter(name, seed, Ztr, ytr, k):
    sub = next(StratifiedShuffleSplit(1, train_size=0.9, random_state=seed).split(Ztr, ytr))[0]
    Zs, ys = Ztr[sub], ytr[sub]
    F, _ = f_classif(Zs, ys); F = np.nan_to_num(F)
    t = time.time()
    bins = filter_select(name, Zs, ys, k, F)
    sec = time.time() - t
    fval = Fitness(Zs, ys, 1, 'bin')(np.isin(np.arange(C.N_BINS), bins))   # same F, reported only
    return {'selector': name, 'seed': seed, 'bins': np.asarray(bins).tolist(), 'fitness': fval,
            'calls': 0, 'sec': sec}


# ---------------------------------------------------------------- evaluation on 2018
def eval_models(pos_weight):
    return {
        'LR': (LogisticRegression(C=0.1, class_weight='balanced', max_iter=3000), True),
        'SVM': (SVC(C=1.0, gamma='scale', class_weight='balanced'), True),
        'RF': (RandomForestClassifier(300, class_weight='balanced_subsample', n_jobs=1, random_state=0), False),
        'XGBoost': (XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=4, subsample=0.8,
                                  colsample_bytree=0.5, scale_pos_weight=pos_weight, tree_method='hist',
                                  n_jobs=1, random_state=0, verbosity=0), False),
        'LightGBM': (LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=15, colsample_bytree=0.5,
                                    class_weight='balanced', n_jobs=1, random_state=0, verbose=-1), False),
        'MLP': (MLPClassifier((128,), alpha=1e-2, early_stopping=True, max_iter=300, random_state=0), True),
    }


def run_eval(Ztr, ytr, Zte, yte, bins, model, est, scaled, Xtr_raw, Xte_raw):
    A, B = (Ztr[:, bins], Zte[:, bins]) if scaled else (Xtr_raw[:, bins], Xte_raw[:, bins])
    est.fit(A, ytr)
    p = est.predict_proba(B)[:, 1] if hasattr(est, 'predict_proba') and model != 'SVM' else est.decision_function(B)
    return C.scores(yte, p)


# ---------------------------------------------------------------- important regions
def region_table(abx, sel, Ztr, ytr, F):
    """Final signature = regions picked by RA-PSO in >= 2 of 3 seeds.
    importance  = drop in 5-fold CV AUPRC (2015-2017 only) when the region is removed
    direction   = sign of the mean standardised LR coefficient of the region's bins
    consensus   = how many of the 10 selector x 3 seed runs touched the region"""
    reg = lambda b: np.unique(np.asarray(b) // C.REGION)
    pso_runs = [reg(r['bins']) for r in sel if r['selector'] == 'RA-PSO']
    cnt = np.zeros(C.N_REGIONS, int)
    for r in pso_runs:
        cnt[r] += 1
    all_cnt = np.zeros(C.N_REGIONS, int)
    for r in sel:
        if r['selector'] != 'All-bins':
            all_cnt[reg(r['bins'])] += 1
    sig = np.flatnonzero(cnt >= 2)
    if len(sig) == 0:
        sig = np.flatnonzero(cnt == cnt.max())
    folds = C.train_folds(ytr)

    def cv_ap(regions):
        cols = C.region_to_bins(regions); ap = []
        for tr, va in folds:
            m = LogisticRegression(C=0.1, class_weight='balanced', max_iter=2000).fit(Ztr[np.ix_(tr, cols)], ytr[tr])
            ap.append(average_precision_score(ytr[va], m.decision_function(Ztr[np.ix_(va, cols)])))
        return np.mean(ap)

    base = cv_ap(sig)
    m = LogisticRegression(C=0.1, class_weight='balanced', max_iter=3000).fit(Ztr[:, C.region_to_bins(sig)], ytr)
    coef = m.coef_[0].reshape(len(sig), C.REGION)
    rows = []
    for i, r in enumerate(sig):
        drop = base - cv_ap(np.delete(sig, i)) if len(sig) > 1 else base
        lo, hi = C.mz_range(r)
        b = r * C.REGION + int(np.argmax(F[r * C.REGION:(r + 1) * C.REGION]))
        rows.append({'antibiotic': abx, 'region': int(r), 'mz_from': lo, 'mz_to': hi,
                     'peak_bin': int(b), 'peak_mz': 2000 + 3 * b + 1.5,
                     'RA-PSO_seeds': int(cnt[r]), 'all_selector_runs': int(all_cnt[r]),
                     'ANOVA_F_region': float(F[r * C.REGION:(r + 1) * C.REGION].mean()),
                     'dAUPRC_if_removed': float(drop),
                     'direction': 'higher in R' if coef[i].mean() > 0 else 'higher in S',
                     'signature_cv_AUPRC': float(base)})
    return pd.DataFrame(rows).sort_values('dAUPRC_if_removed', ascending=False)


def main():
    data_dir, labels_csv, out_dir = sys.argv[1:4]
    abx_list = sys.argv[4:] or C.ANTIBIOTICS
    os.makedirs(out_dir, exist_ok=True)
    X, L = C.load_spectra(data_dir), C.load_labels(labels_csv)
    n_jobs = max(1, (os.cpu_count() or 2) - 1)
    for abx in abx_list:
        t0 = time.time()
        Xtr, ytr, Xte, yte = C.get_task(X, L, abx)
        sc = StandardScaler().fit(Xtr)
        Ztr, Zte = sc.transform(Xtr).astype(np.float32), sc.transform(Xte).astype(np.float32)
        print(f'[{abx}] train {len(ytr)} ({ytr.sum()} R)  test {len(yte)} ({yte.sum()} R)', flush=True)
        sel = Parallel(n_jobs=n_jobs)(delayed(run_selector)(w, s, Ztr, ytr) for w in WRAPPERS for s in SEEDS)
        k_of = {r['seed']: max(len(r['bins']), 10) for r in sel if r['selector'] == 'RA-PSO'}
        sel += Parallel(n_jobs=n_jobs)(delayed(run_filter)(f, s, Ztr, ytr, k_of[s]) for f in FILTERS for s in SEEDS)
        sel.append({'selector': 'All-bins', 'seed': 0, 'bins': list(range(C.N_BINS)), 'fitness': np.nan,
                    'calls': 0, 'sec': 0.0})
        print(f'[{abx}] selection done in {(time.time() - t0) / 60:.1f} min', flush=True)

        M = eval_models((ytr == 0).sum() / max((ytr == 1).sum(), 1))
        jobs = [(r, m, est, s) for r in sel for m, (est, s) in M.items()]
        res = Parallel(n_jobs=n_jobs)(delayed(run_eval)(Ztr, ytr, Zte, yte, np.asarray(r['bins']), m, est, s, Xtr, Xte)
                                      for r, m, est, s in jobs)
        rows = [{'antibiotic': abx, 'selector': r['selector'], 'seed': r['seed'], 'model': m,
                 'n_bins': len(r['bins']), 'n_regions': len(np.unique(np.asarray(r['bins']) // C.REGION)),
                 **{f'test_{k}': v for k, v in s.items()}} for (r, m, _, _), s in zip(jobs, res)]
        pd.DataFrame(rows).to_csv(f'{out_dir}/step3_test_{abx}.csv', index=False)

        srows = []
        for name in WRAPPERS + FILTERS:
            runs = [r for r in sel if r['selector'] == name]
            masks = [np.isin(np.arange(C.N_BINS), r['bins']) for r in runs]
            stab = C.nogueira_stability(masks)
            for r in runs:
                srows.append({'antibiotic': abx, 'selector': name, 'seed': r['seed'], 'n_bins': len(r['bins']),
                              'n_regions': len(np.unique(np.asarray(r['bins']) // C.REGION)),
                              'fitness': r['fitness'], 'fitness_calls': r['calls'], 'select_sec': r['sec'],
                              'nogueira_stability': stab, 'bins': json.dumps(r['bins'])})
        pd.DataFrame(srows).to_csv(f'{out_dir}/step3_selections_{abx}.csv', index=False)

        F, _ = f_classif(Ztr, ytr); F = np.nan_to_num(F)
        region_table(abx, sel, Ztr, ytr, F).to_csv(f'{out_dir}/step3_regions_{abx}.csv', index=False)
        print(f'[{abx}] done in {(time.time() - t0) / 60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
