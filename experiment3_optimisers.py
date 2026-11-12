"""Experiment 3: five wrapper optimisers select m/z regions, then six models are scored on 2018.

Optimisers (all read the same settings file, so every run uses identical settings):
    enhanced_pso  the proposed method (regions, ANOVA-seeded particle, V-shaped transfer,
                  diversity-adaptive inertia, restarts, 3-run vote with a safeguard)
    binary_pso    standard binary PSO, sigmoid transfer, fixed inertia
    ga            binary genetic algorithm (tournament, uniform crossover, elitism)
    gwo           binary grey wolf optimiser (sigmoid transfer)
    woa           binary whale optimisation algorithm (sigmoid transfer)

All five use ONE fitness function and ONE budget of fitness calls:
    F(S) = mean AUPRC of the wrapper classifier over the inner folds of the selection data
           - lambda * (number of selected columns) / n_penalty
Only the 2015-2017 data are used for the search. 2018 is used once, for the final scores.

Inputs: Raw-6000, Var-2000 (top-variance bins), PCA-200 (components). Each input is built from the
training years only. For Raw-6000 and Var-2000 the search unit is a region of 10 bins; for PCA-200
the search unit is one component (components have no m/z position).

Usage:
    python experiment3_optimisers.py <data_dir> <labels_csv> <out_dir> --runner joud --input Var-2000
    python experiment3_optimisers.py data/ data/labels_ecoli_A_corrected.csv results/exp3/ \\
           --runner joud --input Var-2000 --antibiotic Ciprofloxacin --budget 200 --seeds 0   (pilot)

Outputs, in <out_dir>/<antibiotic>/ :
    exp3_<input>_selections.csv   one row per optimiser x seed (regions, fitness, calls, stability, checks)
    exp3_<input>_test.csv         one row per optimiser x seed x model (CV score, 2018 scores)
    exp3_<input>_log.txt          code version, settings fingerprint, timings

Re-score only (no search), from the saved regions:  add --rescore to the same command.
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
os.environ.setdefault('PYTHONWARNINGS', 'ignore')
import argparse, hashlib, json, platform, subprocess, sys, time, warnings
import numpy as np, pandas as pd, yaml
from joblib import Parallel, delayed
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import common as C

warnings.filterwarnings('ignore')
ALGORITHMS = ['enhanced_pso', 'binary_pso', 'ga', 'gwo', 'woa']

# Defaults of the enhanced PSO. Keys can be overridden in the settings file under
# algorithms: enhanced_pso: params: {...}   (this is where the tuning result is stored).
ENHANCED_DEFAULTS = dict(inertia=[0.4, 0.9], c1=1.49445, c2=1.49445, vmax=4.0, seed_regions=30,
                         stall=5, subruns=3, restart_fraction=0.5, restart_flip=0.02, subrun_train_fraction=0.8)


# ---------------------------------------------------------------- settings
def load_settings(path):
    raw = open(path, 'rb').read()
    S = yaml.safe_load(raw)
    S['_sha'] = hashlib.sha256(raw).hexdigest()[:12]
    return S


def make_cfg(S, args):
    se, fi = S['search'], S['fitness']
    return dict(
        budget=args.budget or se['budget_fitness_calls'], pop=se['population'],
        init_density=tuple(se['init_density']), lam=se['size_penalty_lambda'],
        subsample=se['subsample_fraction'], classifier=args.classifier or fi['wrapper_classifier'],
        svm=fi['svm'], inner_folds=fi['inner_folds'], inner_seed=fi['inner_seed'])


def enhanced_params(S):
    p = S['algorithms']['enhanced_pso']['params']
    q = dict(ENHANCED_DEFAULTS)
    if isinstance(p, dict):
        q.update(p)
    return q


# ---------------------------------------------------------------- inputs
class Input:
    """What the optimisers and the final models see for one input type."""
    def __init__(self, name, Z, Zte, R, Rte, groups, n_pen, bin_of_col):
        self.name, self.Z, self.Zte, self.R, self.Rte = name, Z, Zte, R, Rte
        self.groups, self.n_pen, self.bin_of_col = groups, n_pen, bin_of_col
        # Z / Zte: scaled (for LR, SVM, MLP and the search); R / Rte: unscaled (for tree models)


def build_input(name, S, Xtr, Xte):
    spec = S['inputs'][name]
    sc = StandardScaler().fit(Xtr)
    Ztr, Zte = sc.transform(Xtr).astype(np.float32), sc.transform(Xte).astype(np.float32)
    if spec['type'] in ('raw', 'top_variance'):
        if spec['type'] == 'raw':
            cols = np.arange(C.N_BINS)
        else:                                            # variance ranking fitted on training data only
            cols = np.sort(np.argsort(Xtr.var(0))[::-1][:spec['k']])
        region_of_col = cols // C.REGION
        groups = [np.flatnonzero(region_of_col == r) for r in range(C.N_REGIONS)]   # regions keep their position
        return Input(name, Ztr[:, cols], Zte[:, cols], Xtr[:, cols], Xte[:, cols], groups, C.N_BINS, cols)
    if spec['type'] == 'pca':
        p = PCA(spec['n_components'], random_state=spec['random_state']).fit(Ztr)
        Ptr, Pte = p.transform(Ztr).astype(np.float32), p.transform(Zte).astype(np.float32)
        groups = [np.array([i]) for i in range(Ptr.shape[1])]
        return Input(name, Ptr, Pte, Ptr, Pte, groups, Ptr.shape[1], np.full(Ptr.shape[1], -1))
    raise ValueError(spec)


# ---------------------------------------------------------------- fitness (identical for all five)
def wrapper_estimator(cfg):
    if cfg['classifier'] == 'SVM':
        s = cfg['svm']
        return SVC(kernel=s['kernel'], C=s['C'], gamma=s['gamma'], class_weight=s['class_weight'], cache_size=500)
    return KNeighborsClassifier(n_neighbors=5, weights='distance')


def wrapper_score(est, A):
    return est.decision_function(A) if cfg_is_svm(est) else est.predict_proba(A)[:, 1]


def cfg_is_svm(est):
    return isinstance(est, SVC)


class Fitness:
    """The single fitness function. Counts every call and refuses calls beyond the budget."""

    def __init__(self, Z, y, groups, budget, cfg, n_pen):
        self.Z, self.y, self.groups, self.budget, self.cfg, self.n_pen = Z, y, groups, budget, cfg, n_pen
        self.folds = list(StratifiedKFold(cfg['inner_folds'], shuffle=True,
                                          random_state=cfg['inner_seed']).split(Z, y))
        self.calls, self.best, self.hist = 0, -np.inf, []

    def cols(self, mask):
        idx = np.flatnonzero(mask)
        return np.concatenate([self.groups[i] for i in idx]) if len(idx) else np.array([], dtype=int)

    def auprc(self, cols):
        ap = []
        for tr, va in self.folds:
            m = wrapper_estimator(self.cfg).fit(self.Z[np.ix_(tr, cols)], self.y[tr])
            ap.append(average_precision_score(self.y[va], wrapper_score(m, self.Z[np.ix_(va, cols)])))
        return float(np.mean(ap))

    def __call__(self, mask, count=True):
        if count:
            if self.calls >= self.budget:
                raise RuntimeError('fitness budget exceeded')
            self.calls += 1
        cols = self.cols(mask)
        val = -1.0 if len(cols) == 0 else self.auprc(cols) - self.cfg['lam'] * len(cols) / self.n_pen
        if count:
            self.best = max(self.best, val)
            self.hist.append(self.best)
        return val


def random_masks(rng, n, d, density):
    dens = rng.uniform(*density, size=(n, 1))
    m = rng.random((n, d)) < dens
    m[~m.any(1), 0] = True
    return m


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -50, 50)))


# ---------------------------------------------------------------- the five optimisers
def pso(fit, d, rng, budget, cfg, q, proposed, seed_mask=None):
    """proposed=False: standard binary PSO (sigmoid transfer, fixed inertia).
       proposed=True : V-shaped transfer, diversity-adaptive inertia, restarts, seeded particle."""
    POP = cfg['pop']
    stop = fit.calls + budget
    X = random_masks(rng, POP, d, cfg['init_density'])
    if seed_mask is not None:
        X[0] = seed_mask
    V = rng.uniform(-1, 1, (POP, d))
    f = np.array([fit(x) for x in X])
    P, pf = X.copy(), f.copy()
    g = int(np.argmax(pf)); G, gf = P[g].copy(), pf[g]
    c1, c2, vmax = q['c1'], q['c2'], q['vmax']
    div0 = max((X != G).mean(), 1e-9)
    stall = 0
    while fit.calls + POP <= stop:
        if proposed:
            div = (X != G).mean()
            lo, hi = q['inertia']
            w = lo + (hi - lo) * min(div / div0, 1.0)
        else:
            w = q['inertia']
        r1, r2 = rng.random((POP, d)), rng.random((POP, d))
        V = np.clip(w * V + c1 * r1 * (P.astype(float) - X) + c2 * r2 * (G.astype(float) - X), -vmax, vmax)
        if proposed:
            X = np.where(rng.random((POP, d)) < np.abs(np.tanh(V)), ~X, X)
        else:
            X = rng.random((POP, d)) < sigmoid(V)
        X[~X.any(1), rng.integers(d)] = True
        f = np.array([fit(x) for x in X])
        imp = f > pf
        P[imp], pf[imp] = X[imp], f[imp]
        g = int(np.argmax(pf))
        if pf[g] > gf + 1e-6:
            G, gf, stall = P[g].copy(), pf[g], 0
        else:
            stall += 1
        if proposed and stall >= q['stall']:
            worst = np.argsort(pf)[:max(int(POP * q['restart_fraction']), 1)]
            X[worst] = np.where(rng.random((len(worst), d)) < q['restart_flip'], ~G, G)
            V[worst] = rng.uniform(-1, 1, (len(worst), d))
            stall = 0
    return G, gf


def ga(fit, d, rng, budget, cfg, q):
    POP = cfg['pop']
    stop = fit.calls + budget
    X = random_masks(rng, POP, d, cfg['init_density'])
    f = np.array([fit(x) for x in X])
    while fit.calls + POP - 1 <= stop:
        elite = int(np.argmax(f))
        kids = [X[elite].copy()]
        while len(kids) < POP:
            a, b = (max(rng.choice(POP, 3, replace=False), key=lambda i: f[i]) for _ in range(2))
            child = np.where(rng.random(d) < 0.5, X[a], X[b]) if rng.random() < 0.9 else X[a].copy()
            child ^= rng.random(d) < 2.0 / d
            if not child.any():
                child[rng.integers(d)] = True
            kids.append(child)
        X = np.array(kids)
        f = np.concatenate([[f[elite]], [fit(x) for x in X[1:]]])
    i = int(np.argmax(f))
    return X[i], f[i]


def gwo(fit, d, rng, budget, cfg, q):
    """Binary GWO (Emary et al. 2016, approach 2: sigmoid transfer of the continuous update)."""
    POP = cfg['pop']
    stop = fit.calls + budget
    X = random_masks(rng, POP, d, cfg['init_density'])
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
        X = rng.random((POP, d)) < sigmoid(q['slope'] * (Y - q['threshold']))
        X[~X.any(1), rng.integers(d)] = True
        f = np.array([fit(x) for x in X])
        if f.max() > bf:
            best, bf = X[np.argmax(f)].copy(), f.max()
    return best, bf


def woa(fit, d, rng, budget, cfg, q):
    """Binary WOA (Mirjalili and Lewis 2016). A, C, p and l are drawn once per whale, as in the original
    code. The continuous position is turned into bits with the same sigmoid(10 (Y - 0.5)) used for GWO."""
    POP = cfg['pop']
    stop = fit.calls + budget
    X = random_masks(rng, POP, d, cfg['init_density'])
    f = np.array([fit(x) for x in X])
    n_iter = max((budget - POP) // POP, 1); it = 0
    best, bf = X[np.argmax(f)].copy(), f.max()
    while fit.calls + POP <= stop:
        a = 2 - 2 * it / n_iter; it += 1
        Xf, B = X.astype(float), best.astype(float)
        Y = np.empty_like(Xf)
        for i in range(POP):
            A = 2 * a * rng.random() - a
            Cc = 2 * rng.random()
            if rng.random() < q['p_spiral']:                     # spiral update around the best whale
                l = rng.uniform(-1, 1)
                Y[i] = np.abs(B - Xf[i]) * np.exp(q['b'] * l) * np.cos(2 * np.pi * l) + B
            elif abs(A) < 1:                                     # encircle the best whale
                Y[i] = B - A * np.abs(Cc * B - Xf[i])
            else:                                                # search around a random whale
                R = Xf[rng.integers(POP)]
                Y[i] = R - A * np.abs(Cc * R - Xf[i])
        X = rng.random((POP, d)) < sigmoid(10 * (Y - 0.5))
        X[~X.any(1), rng.integers(d)] = True
        f = np.array([fit(x) for x in X])
        if f.max() > bf:
            best, bf = X[np.argmax(f)].copy(), f.max()
    return best, bf


def enhanced_pso(Zs, ys, groups, rng, budget, cfg, q, n_pen, unit_rank):
    """Proposed: k sub-runs on resamples (budget/k each), keep units chosen in a majority of sub-runs;
    safeguard: if the voted set scores worse on the full selection data, keep the best sub-run."""
    k = int(q['subruns'])
    d = len(groups)
    full = Fitness(Zs, ys, groups, budget, cfg, n_pen)
    seed_k = max(1, round(q['seed_regions'] * d / C.N_REGIONS))
    seed = np.zeros(d, bool); seed[unit_rank[:seed_k]] = True
    sss = StratifiedShuffleSplit(k, train_size=q['subrun_train_fraction'], random_state=int(rng.integers(10**9)))
    per_run = (budget - (k + 1)) // k                # keeps k + 1 calls for the safeguard comparison
    runs, hist = [], []
    for sub, _ in sss.split(Zs, ys):
        fit = Fitness(Zs[sub], ys[sub], groups, per_run, cfg, n_pen)
        G, _ = pso(fit, d, rng, per_run, cfg, q, proposed=True, seed_mask=seed)
        runs.append(G); full.calls += fit.calls; hist += fit.hist
    votes = np.sum(runs, 0)
    voted = votes >= (k // 2 + 1)
    cand = [voted] + runs if voted.any() else runs
    fs = [full(m) for m in cand]
    best = cand[int(np.argmax(fs))]
    return best, max(fs), full.calls, votes, hist


# ---------------------------------------------------------------- one search run
def run_search(algo, seed, inp, ytr, cfg, S, enh):
    rng = np.random.default_rng(1000 + seed)
    sub = next(StratifiedShuffleSplit(1, train_size=cfg['subsample'], random_state=seed).split(inp.Z, ytr))[0]
    Zs, ys = inp.Z[sub], ytr[sub]
    d = len(inp.groups)
    budget = cfg['budget']
    t = time.time(); extra = {}
    if algo == 'enhanced_pso':
        F, _ = f_classif(Zs, ys); F = np.nan_to_num(F)
        unit_f = np.array([F[g].mean() if len(g) else 0.0 for g in inp.groups])
        mask, fval, calls, votes, hist = enhanced_pso(Zs, ys, inp.groups, rng, budget, cfg, enh, inp.n_pen,
                                                      np.argsort(unit_f)[::-1])
        extra['votes'] = votes.tolist()
    else:
        fit = Fitness(Zs, ys, inp.groups, budget, cfg, inp.n_pen)
        p = S['algorithms'][algo]['params']
        if algo == 'binary_pso':
            mask, fval = pso(fit, d, rng, budget, cfg, p, proposed=False)
        elif algo == 'ga':
            mask, fval = ga(fit, d, rng, budget, cfg, p)
        elif algo == 'gwo':
            mask, fval = gwo(fit, d, rng, budget, cfg, p)
        else:
            mask, fval = woa(fit, d, rng, budget, cfg, p)
        calls, hist = fit.calls, fit.hist
    sec = time.time() - t
    # sanity reference: 20 random masks scored with the same fitness on the same data (not counted)
    ref = Fitness(Zs, ys, inp.groups, 10**9, cfg, inp.n_pen)
    rnd = float(np.mean([ref(m, count=False) for m in
                         random_masks(np.random.default_rng(seed + 77), 20, d, cfg['init_density'])]))
    return dict(algorithm=algo, seed=seed, mask=np.asarray(mask, bool), fitness=float(fval), calls=int(calls),
                budget=budget, sec=sec, random_mean=rnd, history=[float(h) for h in hist[::max(len(hist) // 100, 1)]],
                **extra)


# ---------------------------------------------------------------- final scoring with the six models
def final_models(pos_weight, c_svm):
    return {
        'LR': (LogisticRegression(C=0.1, class_weight='balanced', max_iter=3000), True),
        'SVM': (SVC(C=c_svm, gamma='scale', class_weight='balanced'), True),
        'RF': (RandomForestClassifier(300, class_weight='balanced_subsample', n_jobs=1, random_state=0), False),
        'XGBoost': (XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=4, subsample=0.8,
                                  colsample_bytree=0.5, scale_pos_weight=pos_weight, tree_method='hist',
                                  n_jobs=1, random_state=0, verbosity=0), False),
        'LightGBM': (LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=15, colsample_bytree=0.5,
                                    class_weight='balanced', n_jobs=1, random_state=0, verbose=-1), False),
        'MLP': (MLPClassifier((128,), alpha=1e-2, early_stopping=True, max_iter=300, random_state=0), True),
    }


def score_vec(est, A):
    return est.decision_function(A) if isinstance(est, (SVC, LogisticRegression)) else est.predict_proba(A)[:, 1]


def evaluate(run, inp, ytr, yte, folds, cfg_svm_c, model, which):
    """5-fold CV on the training years (AUPRC, out-of-fold predictions for the Youden threshold),
    then fit on all training years and score 2018 once."""
    from sklearn.base import clone
    cols = np.concatenate([inp.groups[i] for i in np.flatnonzero(run['mask'])])
    est0, scaled = final_models((ytr == 0).sum() / max((ytr == 1).sum(), 1), cfg_svm_c)[model]
    A, B = (inp.Z[:, cols], inp.Zte[:, cols]) if scaled else (inp.R[:, cols], inp.Rte[:, cols])
    oof, aps, aucs = np.zeros(len(ytr)), [], []
    for tr, va in folds:
        m = clone(est0).fit(A[tr], ytr[tr])
        oof[va] = score_vec(m, A[va])
        aps.append(average_precision_score(ytr[va], oof[va]))
        aucs.append(roc_auc_score(ytr[va], oof[va]))
    m = clone(est0).fit(A, ytr)
    thr = C.youden_threshold(ytr, oof)
    sc = C.scores(yte, score_vec(m, B), thr)
    return dict(algorithm=run['algorithm'], seed=run['seed'], model=model, n_columns=len(cols),
                cv_AUROC=float(np.mean(aucs)), cv_AUPRC=float(np.mean(aps)),
                **{f'test_{k}': v for k, v in sc.items()})


# ---------------------------------------------------------------- helpers
def git_commit():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        c = subprocess.run(['git', '-C', here, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(['git', '-C', here, 'status', '--porcelain'], capture_output=True, text=True).stdout.strip()
        return (c or 'unknown') + (' (uncommitted changes)' if dirty else '')
    except Exception:
        return 'unknown'


def regions_of(run, inp):
    """Original region ids selected (Raw-6000, Var-2000); component ids for PCA-200."""
    return np.flatnonzero(run['mask']).tolist()


def rescore(args, abx, out, inp, ytr, yte, S, cfg, algos, n_jobs, t0):
    """No search. Reads the regions saved by an earlier run and redoes only the six-model scoring."""
    path = f'{out}/exp3_{args.input}_selections.csv'
    if not os.path.exists(path):
        print(f'[{abx}] no saved selections at {path}, skipped', flush=True)
        return
    old = pd.read_csv(path)
    old = old[old.algorithm.isin(algos)]
    runs = []
    for _, r in old.iterrows():
        mask = np.zeros(len(inp.groups), bool)
        mask[json.loads(r['regions'])] = True
        runs.append(dict(algorithm=r['algorithm'], seed=int(r['seed']), mask=mask))
    folds = C.train_folds(ytr)
    res = Parallel(n_jobs=n_jobs)(delayed(evaluate)(r, inp, ytr, yte, folds, cfg['svm']['C'], m, None)
                                  for r in runs for m in S['final_evaluation']['models'])
    T = pd.DataFrame(res)
    T.insert(0, 'input', args.input); T.insert(0, 'antibiotic', abx)
    T['best_by_cv'] = T.groupby(['algorithm', 'seed'])['cv_AUPRC'].transform('max') == T['cv_AUPRC']
    T.to_csv(f'{out}/exp3_{args.input}_test.csv', index=False)
    with open(f'{out}/exp3_{args.input}_log.txt', 'a') as fh:
        fh.write(f'\nRESCORE {time.strftime("%Y-%m-%d %H:%M")}: six-model scoring redone from the saved regions '
                 f'(commit {git_commit()}, settings_sha {S["_sha"]}); no search was repeated. '
                 f'Adds cv_AUROC. Took {(time.time() - t0) / 60:.1f} min.\n')
    print(f'[{abx}] rescored {len(runs)} saved selections in {(time.time() - t0) / 60:.1f} min', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir'); ap.add_argument('labels_csv'); ap.add_argument('out_dir')
    ap.add_argument('--runner', required=True, choices=['joud', 'maria', 'zainab'])
    ap.add_argument('--input', required=True, choices=['Raw-6000', 'Var-2000', 'PCA-200'])
    ap.add_argument('--antibiotic', default=None, help='one antibiotic only (pilot)')
    ap.add_argument('--budget', type=int, default=None, help='override the budget (pilot only; same for all five)')
    ap.add_argument('--seeds', default=None, help='e.g. 0 or 0,1 (pilot only)')
    ap.add_argument('--algorithms', default=','.join(ALGORITHMS))
    ap.add_argument('--classifier', default=None, choices=['SVM', 'KNN'])
    ap.add_argument('--settings', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                       'config', 'experiment3_settings.yaml'))
    ap.add_argument('--n-jobs', type=int, default=None)
    ap.add_argument('--skip-final', action='store_true', help='search only, skip the six-model scoring')
    ap.add_argument('--rescore', action='store_true',
                    help='no search: read the saved regions from exp3_<input>_selections.csv in <out_dir> and '
                         'redo only the six-model scoring (rewrites exp3_<input>_test.csv)')
    args = ap.parse_args()

    S = load_settings(args.settings)
    cfg, enh = make_cfg(S, args), enhanced_params(S)
    seeds = [int(s) for s in args.seeds.split(',')] if args.seeds else S['search']['seeds']
    algos = args.algorithms.split(',')
    abx_list = [args.antibiotic] if args.antibiotic else S['antibiotics'][args.runner]
    if args.antibiotic and args.antibiotic not in C.ANTIBIOTICS:
        sys.exit(f'unknown antibiotic: {args.antibiotic}')
    n_jobs = args.n_jobs or max(1, (os.cpu_count() or 2) - 1)
    X, L = C.load_spectra(args.data_dir), C.load_labels(args.labels_csv)

    for abx in abx_list:
        t0 = time.time()
        out = os.path.join(args.out_dir, abx.replace(' ', '_'))
        os.makedirs(out, exist_ok=True)
        Xtr, ytr, Xte, yte = C.get_task(X, L, abx)
        inp = build_input(args.input, S, Xtr, Xte)
        print(f'[{abx} | {args.input}] train {len(ytr)} ({ytr.sum()} non-S)  test {len(yte)} ({yte.sum()} non-S)  '
              f'units {len(inp.groups)}  budget {cfg["budget"]}  classifier {cfg["classifier"]}', flush=True)
        if args.rescore:
            rescore(args, abx, out, inp, ytr, yte, S, cfg, algos, n_jobs, t0)
            continue
        runs = Parallel(n_jobs=n_jobs)(delayed(run_search)(a, s, inp, ytr, cfg, S, enh) for a in algos for s in seeds)
        t_search = time.time() - t0
        print(f'[{abx}] search done in {t_search / 60:.1f} min', flush=True)

        rows = []
        for a in algos:
            rs = [r for r in runs if r['algorithm'] == a]
            stab = C.nogueira_stability([r['mask'] for r in rs])
            for r in rs:
                rows.append(dict(antibiotic=abx, input=args.input, algorithm=a, seed=r['seed'],
                                 n_units=int(r['mask'].sum()), n_columns=int(sum(len(inp.groups[i]) for i in np.flatnonzero(r['mask']))),
                                 fitness=r['fitness'], random_mean=r['random_mean'],
                                 beats_random=bool(r['fitness'] > r['random_mean']),
                                 fitness_calls=r['calls'], budget=r['budget'], budget_ok=bool(r['calls'] <= r['budget']),
                                 search_sec=round(r['sec'], 1), nogueira_stability=stab,
                                 regions=json.dumps(regions_of(r, inp)), history=json.dumps(r['history']),
                                 votes=json.dumps(r.get('votes'))))
        pd.DataFrame(rows).to_csv(f'{out}/exp3_{args.input}_selections.csv', index=False)

        if not args.skip_final:
            folds = C.train_folds(ytr)
            c_svm = cfg['svm']['C']
            res = Parallel(n_jobs=n_jobs)(delayed(evaluate)(r, inp, ytr, yte, folds, c_svm, m, None)
                                          for r in runs for m in S['final_evaluation']['models'])
            T = pd.DataFrame(res)
            T.insert(0, 'input', args.input); T.insert(0, 'antibiotic', abx)
            T['best_by_cv'] = T.groupby(['algorithm', 'seed'])['cv_AUPRC'].transform('max') == T['cv_AUPRC']
            T.to_csv(f'{out}/exp3_{args.input}_test.csv', index=False)

        sel = pd.DataFrame(rows)
        with open(f'{out}/exp3_{args.input}_log.txt', 'w') as fh:
            fh.write(f'commit: {git_commit()}\nsettings_sha: {S["_sha"]}\ndate: {time.strftime("%Y-%m-%d %H:%M")}\n')
            fh.write(f'args: {vars(args)}\ncfg: {cfg}\nenhanced_pso params: {enh}'
                     f'{" (defaults, not tuned yet)" if not isinstance(S["algorithms"]["enhanced_pso"]["params"], dict) else ""}\n')
            fh.write(f'python {platform.python_version()}  numpy {np.__version__}  pandas {pd.__version__}\n')
            fh.write(f'search minutes: {t_search / 60:.1f}   total minutes: {(time.time() - t0) / 60:.1f}\n')
            fh.write(sel.groupby('algorithm')[['fitness', 'n_columns', 'fitness_calls', 'search_sec']].mean().round(3).to_string())
            fh.write(f'\nall budgets respected: {bool(sel.budget_ok.all())}   '
                     f'all beat random: {bool(sel.beats_random.all())}\n')
        print(sel.groupby('algorithm')[['fitness', 'n_columns', 'fitness_calls', 'search_sec']].mean().round(3).to_string())
        print(f'[{abx}] budgets respected: {bool(sel.budget_ok.all())}; beat random: {bool(sel.beats_random.all())}; '
              f'done in {(time.time() - t0) / 60:.1f} min', flush=True)


if __name__ == '__main__':
    main()
