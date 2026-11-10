"""Multi-objective optimisers for m/z region selection (Experiment 4).

Problem (both objectives are minimised, both lie in [0, 1]):
    f1(S) = 1 - mean AUPRC of the wrapper classifier over the inner folds of the selection data
    f2(S) = (number of selected columns) / (number of columns in the input)
A run returns a Pareto front (an archive of non-dominated region sets) instead of one set,
so no size penalty lambda has to be tuned.

Optimisers (all share ONE fitness object, ONE budget of fitness calls and ONE population size):
    mopso      baseline: binary MOPSO of Coello Coello, Pulido and Lechuga (2004). Adaptive-grid archive and
               leader selection, sigmoid transfer, fixed inertia, Coello's decreasing mutation.
    nsga2      reference: binary NSGA-II (Deb et al. 2002). Tournament on rank and crowding, uniform
               crossover, bit-flip mutation.
    emopso     proposed: enhanced region-aware MOPSO. Six components, each can be switched off for the
               ablation study by adding '-<component>' to the name (for example 'emopso-init'):
         init      ANOVA-guided, size-stratified start: particles start at sizes spread on a log scale,
                   units drawn with a bias towards high ANOVA scores; one particle = top-k ANOVA units
         leader    crowding-distance archive (MOPSO-CD): leaders picked by tournament on crowding distance,
                   archive pruned by crowding distance  (off -> adaptive grid as in the baseline)
         vshape    V-shaped transfer |tanh(v)| that flips bits  (off -> sigmoid transfer)
         inertia   inertia decreasing linearly from w_max to w_min  (off -> fixed inertia of the baseline)
         mutation  region-aware mutation: shift a region to its m/z neighbour, drop a weak region, add a
                   strong region, or flip one bit  (off -> Coello's mutation of the baseline)
         restart   when the archive has not changed for `stall` iterations, the worst half of the swarm
                   is restarted next to random archive members
         local     a share of the budget is kept for a final archive local search that tries to remove
                   the weakest region / add the strongest region of archive members
    Fairness control: 'mopso+init' is the baseline with the same ANOVA start as the proposed method.
"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier

EMOPSO_COMPONENTS = ['init', 'leader', 'vshape', 'inertia', 'mutation', 'restart', 'local']


class BudgetExceeded(RuntimeError):
    pass


# ------------------------------------------------------------------ fitness (identical for all)
def wrapper_estimator(name):
    if name == 'LR':
        return LogisticRegression(C=0.1, class_weight='balanced', max_iter=300, tol=1e-3)
    if name == 'KNN':
        return KNeighborsClassifier(n_neighbors=5, weights='distance')
    if name == 'LightGBM':
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=50, learning_rate=0.1, num_leaves=15, colsample_bytree=0.5,
                              class_weight='balanced', n_jobs=1, random_state=0, verbose=-1)
    raise ValueError(name)


def wrapper_scores(est, A):
    if isinstance(est, LogisticRegression):
        return est.decision_function(A)
    return est.predict_proba(A)[:, 1]


def cv_auprc(Z, y, cols, folds, classifier):
    out = []
    for tr, va in folds:
        m = wrapper_estimator(classifier).fit(Z[np.ix_(tr, cols)], y[tr])
        out.append(average_precision_score(y[va], wrapper_scores(m, Z[np.ix_(va, cols)])))
    return out


class MOFitness:
    """Two-objective fitness. Counts every call and refuses calls beyond the budget.
    Repeated masks are served from a cache (saves time only; the call is still counted)."""

    def __init__(self, Z, y, groups, budget, classifier, n_folds, fold_seed, n_cols_total):
        self.Z, self.y, self.groups, self.budget = Z, y, groups, int(budget)
        self.classifier, self.n_cols_total = classifier, n_cols_total
        self.folds = list(StratifiedKFold(n_folds, shuffle=True, random_state=fold_seed).split(Z, y))
        self.calls, self.cache = 0, {}

    def remaining(self):
        return self.budget - self.calls

    def cols(self, mask):
        idx = np.flatnonzero(mask)
        return np.concatenate([self.groups[i] for i in idx]) if len(idx) else np.array([], dtype=int)

    def __call__(self, mask):
        if self.calls >= self.budget:
            raise BudgetExceeded('fitness budget exceeded')
        self.calls += 1
        key = np.packbits(mask).tobytes()
        if key not in self.cache:
            cols = self.cols(mask)
            if len(cols) == 0:
                self.cache[key] = np.array([1.0, 1.0])            # empty set: worst on both objectives
            else:
                ap = np.mean(cv_auprc(self.Z, self.y, cols, self.folds, self.classifier))
                self.cache[key] = np.array([1.0 - ap, len(cols) / self.n_cols_total])
        return self.cache[key].copy()

    def batch(self, X):
        return np.array([self(x) for x in X])


# ------------------------------------------------------------------ Pareto helpers
def dominates(a, b):
    return bool(np.all(a <= b) and np.any(a < b))


def nondominated(F):
    F = np.asarray(F)
    keep = np.ones(len(F), bool)
    for i in range(len(F)):
        if np.any(np.all(F <= F[i], 1) & np.any(F < F[i], 1)):
            keep[i] = False
    return keep


def fronts_and_crowding(F):
    """Fast non-dominated sorting + crowding distance (Deb et al. 2002)."""
    n = len(F)
    S = [[] for _ in range(n)]
    cnt = np.zeros(n, int)
    for i in range(n):
        for j in range(n):
            if i != j:
                if dominates(F[i], F[j]):
                    S[i].append(j)
                elif dominates(F[j], F[i]):
                    cnt[i] += 1
    rank = np.full(n, -1)
    cur = list(np.flatnonzero(cnt == 0))
    r = 0
    while cur:
        nxt = []
        for i in cur:
            rank[i] = r
            for j in S[i]:
                cnt[j] -= 1
                if cnt[j] == 0:
                    nxt.append(j)
        cur, r = nxt, r + 1
    crowd = np.zeros(n)
    for k in range(r):
        idx = np.flatnonzero(rank == k)
        crowd[idx] = crowding_distance(F[idx])
    return rank, crowd


def crowding_distance(F):
    n = len(F)
    if n <= 2:
        return np.full(n, np.inf)
    d = np.zeros(n)
    for m in range(F.shape[1]):
        o = np.argsort(F[:, m], kind='stable')
        span = F[o[-1], m] - F[o[0], m]
        d[o[0]] = d[o[-1]] = np.inf
        if span > 0:
            d[o[1:-1]] += (F[o[2:], m] - F[o[:-2], m]) / span
    return d


def hypervolume_2d(F, ref=(1.0, 1.0)):
    """Area dominated by the points in F and bounded by ref (minimisation)."""
    F = np.asarray(F, float)
    if len(F) == 0:
        return 0.0
    F = F[np.all(F < np.asarray(ref), 1)]
    if len(F) == 0:
        return 0.0
    F = F[nondominated(F)]
    F = F[np.argsort(F[:, 0])]
    nxt = np.append(F[1:, 0], ref[0])
    return float(np.sum((nxt - F[:, 0]) * (ref[1] - F[:, 1])))


def igd_plus(A, R):
    """IGD+ (Ishibuchi et al. 2015) of approximation A against reference front R (minimisation)."""
    A, R = np.asarray(A, float), np.asarray(R, float)
    if len(A) == 0 or len(R) == 0:
        return np.nan
    diff = np.maximum(A[None, :, :] - R[:, None, :], 0)
    return float(np.sqrt((diff ** 2).sum(2)).min(1).mean())


# ------------------------------------------------------------------ external archive
class Archive:
    """Bounded archive of non-dominated solutions. mode='grid' (Coello 2004) or 'crowding' (MOPSO-CD)."""

    def __init__(self, cap, mode, rng, ndiv=30):
        self.cap, self.mode, self.rng, self.ndiv = cap, mode, rng, ndiv
        self.X, self.F = [], np.empty((0, 2))

    def __len__(self):
        return len(self.X)

    def add(self, x, f):
        if len(self.F):
            if np.any(np.all(self.F <= f, 1)):                     # dominated by or equal to a member
                return False
            keep = ~(np.all(f <= self.F, 1) & np.any(f < self.F, 1))
            self.X = [m for m, k in zip(self.X, keep) if k]
            self.F = self.F[keep]
        self.X.append(np.asarray(x, bool).copy())
        self.F = np.vstack([self.F, f])
        while len(self.X) > self.cap:
            self._prune()
        return True

    def _cells(self):
        lo, hi = self.F.min(0), self.F.max(0)
        span = np.where(hi - lo > 0, hi - lo, 1.0)
        c = np.minimum(((self.F - lo) / span * self.ndiv).astype(int), self.ndiv - 1)
        return c[:, 0] * self.ndiv + c[:, 1]

    def _prune(self):
        if self.mode == 'grid':
            cells = self._cells()
            u, cnt = np.unique(cells, return_counts=True)
            members = np.flatnonzero(cells == u[np.argmax(cnt)])
            i = int(self.rng.choice(members))
        else:
            cd = crowding_distance(self.F)
            i = int(np.argmin(cd))
        del self.X[i]
        self.F = np.delete(self.F, i, 0)

    def leader(self):
        n = len(self.X)
        if n == 1:
            return self.X[0]
        if self.mode == 'grid':
            cells = self._cells()
            u, inv, cnt = np.unique(cells, return_inverse=True, return_counts=True)
            p = 10.0 / cnt
            c = self.rng.choice(len(u), p=p / p.sum())
            return self.X[int(self.rng.choice(np.flatnonzero(inv == c)))]
        cd = crowding_distance(self.F)
        a, b = self.rng.choice(n, 2, replace=False)
        return self.X[a if cd[a] >= cd[b] else b]


# ------------------------------------------------------------------ shared operators
def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -50, 50)))


def random_masks(rng, n, d, density):
    dens = rng.uniform(*density, size=(n, 1))
    m = rng.random((n, d)) < dens
    m[~m.any(1), 0] = True
    return m


def repair(X, rng):
    empty = ~X.any(1)
    if empty.any():
        X[np.flatnonzero(empty), rng.integers(X.shape[1], size=empty.sum())] = True
    return X


def anova_stratified_masks(rng, n, d, density, unit_rank, strength, seed_units):
    """Size-stratified start. Particle sizes are spread on a log scale between 1 unit and
    density[1] * d units; units are drawn with weights 1 + strength * (2 * score - 1), score = 1 for the
    best ANOVA unit and 0 for the worst. Particle 0 holds the top `seed_units` ANOVA units."""
    pos = np.empty(d); pos[unit_rank] = np.arange(d)
    score = 1 - pos / max(d - 1, 1)
    w = np.clip(1 + strength * (2 * score - 1), 1e-3, None)
    kmax = max(2, int(round(density[1] * d)))
    sizes = np.unique(np.round(np.geomspace(1, kmax, n)).astype(int))
    sizes = np.resize(sizes, n)
    rng.shuffle(sizes)
    X = np.zeros((n, d), bool)
    for i, k in enumerate(sizes):
        X[i, rng.choice(d, size=min(k, d), replace=False, p=w / w.sum())] = True
    X[0] = False
    X[0, unit_rank[:max(1, min(seed_units, d))]] = True
    return X


def coello_mutation(X, rng, it, T, rate):
    """Coello (2004): a particle mutates with probability (1 - t/T)^(5/rate); the number of bits flipped
    shrinks with the same factor."""
    d = X.shape[1]
    pm = (1 - min(it / max(T, 1), 1.0)) ** (5.0 / rate)
    for i in range(len(X)):
        if rng.random() < pm:
            k = max(1, int(round(pm * 0.1 * d)))
            j = rng.choice(d, size=k, replace=False)
            X[i, j] = ~X[i, j]
    return X


def region_mutation(X, rng, pm, unit_score, ordered):
    """Region-aware mutation. With probability pm a particle gets ONE of: shift a selected unit to its
    m/z neighbour (only when units are ordered by m/z), drop a weak unit, add a strong unit, flip one bit.
    'Weak' and 'strong' are decided by a 3-way tournament on ANOVA score, so the move stays random."""
    n, d = X.shape
    ops = ['shift', 'drop', 'add', 'flip'] if ordered else ['drop', 'add', 'flip']
    for i in range(n):
        if rng.random() >= pm:
            continue
        op = ops[rng.integers(len(ops))]
        on, off = np.flatnonzero(X[i]), np.flatnonzero(~X[i])
        if op == 'shift' and len(on):
            u = int(rng.choice(on)); v = u + (1 if rng.random() < 0.5 else -1)
            if 0 <= v < d and not X[i, v]:
                X[i, u], X[i, v] = False, True
        elif op == 'drop' and len(on) > 1:
            c = rng.choice(on, size=min(3, len(on)), replace=False)
            X[i, c[np.argmin(unit_score[c])]] = False
        elif op == 'add' and len(off):
            c = rng.choice(off, size=min(3, len(off)), replace=False)
            X[i, c[np.argmax(unit_score[c])]] = True
        else:
            X[i, rng.integers(d)] ^= True
    return X


def update_pbest(P, PF, X, F, rng):
    for i in range(len(X)):
        if dominates(F[i], PF[i]) or (not dominates(PF[i], F[i]) and rng.random() < 0.5):
            P[i], PF[i] = X[i], F[i]
    return P, PF


def hv_trace(trace, fit, A):
    trace.append((fit.calls, hypervolume_2d(A.F)))


# ------------------------------------------------------------------ baseline MOPSO
def mopso(fit, d, rng, cfg, p, init=None):
    N = cfg['pop']
    T = max((fit.budget - N) // N, 1)
    X = init.copy() if init is not None else random_masks(rng, N, d, cfg['init_density'])
    V = np.zeros((N, d))
    F = fit.batch(X)
    P, PF = X.copy(), F.copy()
    A = Archive(cfg['archive_size'], 'grid', rng, p['grid_divisions'])
    for x, f in zip(X, F):
        A.add(x, f)
    trace, it = [], 0
    hv_trace(trace, fit, A)
    while fit.remaining() >= N:
        L = np.array([A.leader() for _ in range(N)], float)
        r1, r2 = rng.random((N, d)), rng.random((N, d))
        Xf = X.astype(float)
        V = np.clip(p['inertia'] * V + p['c1'] * r1 * (P - Xf) + p['c2'] * r2 * (L - Xf), -p['vmax'], p['vmax'])
        X = rng.random((N, d)) < sigmoid(V)
        X = repair(coello_mutation(X, rng, it, T, p['mutation_rate']), rng)
        F = fit.batch(X)
        P, PF = update_pbest(P, PF, X, F, rng)
        for x, f in zip(X, F):
            A.add(x, f)
        it += 1
        hv_trace(trace, fit, A)
    return A, trace


# ------------------------------------------------------------------ NSGA-II
def nsga2(fit, d, rng, cfg, p):
    N = cfg['pop']
    X = random_masks(rng, N, d, cfg['init_density'])
    F = fit.batch(X)
    trace = [(fit.calls, hypervolume_2d(F))]
    while fit.remaining() >= N:
        rank, crowd = fronts_and_crowding(F)

        def pick():
            a, b = rng.choice(N, 2, replace=False)
            if rank[a] != rank[b]:
                return a if rank[a] < rank[b] else b
            return a if crowd[a] >= crowd[b] else b
        kids = np.empty((N, d), bool)
        for k in range(N):
            a, b = pick(), pick()
            c = np.where(rng.random(d) < 0.5, X[a], X[b]) if rng.random() < p['crossover_prob'] else X[a].copy()
            c ^= rng.random(d) < p['mutation_bits'] / d
            kids[k] = c
        kids = repair(kids, rng)
        FK = fit.batch(kids)
        XA, FA = np.vstack([X, kids]), np.vstack([F, FK])
        rank, crowd = fronts_and_crowding(FA)
        order = np.lexsort((-crowd, rank))[:N]
        X, F = XA[order], FA[order]
        trace.append((fit.calls, hypervolume_2d(F)))
    A = Archive(cfg['archive_size'], 'crowding', rng)
    for x, f in zip(X, F):
        A.add(x, f)
    return A, trace


# ------------------------------------------------------------------ enhanced region-aware MOPSO
def emopso(fit, d, rng, cfg, p, unit_rank, unit_score, ordered, off=()):
    off = set(off)
    N = cfg['pop']
    ls_budget = 0 if 'local' in off else int(round(p['local_share'] * fit.budget))
    T = max((fit.budget - ls_budget - N) // N, 1)
    if 'init' in off:
        X = random_masks(rng, N, d, cfg['init_density'])
    else:
        X = anova_stratified_masks(rng, N, d, cfg['init_density'], unit_rank, p['anova_strength'], p['seed_units'])
    X = repair(X, rng)
    V = np.zeros((N, d))
    F = fit.batch(X)
    P, PF = X.copy(), F.copy()
    A = Archive(cfg['archive_size'], 'grid' if 'leader' in off else 'crowding', rng, p['grid_divisions'])
    for x, f in zip(X, F):
        A.add(x, f)
    trace, it, stall = [], 0, 0
    hv_trace(trace, fit, A)
    while fit.remaining() - ls_budget >= N:
        t = min(it / T, 1.0)
        w = p['inertia_fixed'] if 'inertia' in off else p['w_max'] - (p['w_max'] - p['w_min']) * t
        L = np.array([A.leader() for _ in range(N)], float)
        r1, r2 = rng.random((N, d)), rng.random((N, d))
        Xf = X.astype(float)
        V = np.clip(w * V + p['c1'] * r1 * (P - Xf) + p['c2'] * r2 * (L - Xf), -p['vmax'], p['vmax'])
        if 'vshape' in off:
            X = rng.random((N, d)) < sigmoid(V)
        else:
            X = np.where(rng.random((N, d)) < np.abs(np.tanh(V)), ~X, X)
        if 'mutation' in off:
            X = coello_mutation(X, rng, it, T, p['mutation_rate'])
        else:
            pm = p['mut_min'] + (p['mut_max'] - p['mut_min']) * (1 - t)
            X = region_mutation(X, rng, pm, unit_score, ordered)
        X = repair(X, rng)
        F = fit.batch(X)
        P, PF = update_pbest(P, PF, X, F, rng)
        changed = sum(A.add(x, f) for x, f in zip(X, F))
        stall = 0 if changed else stall + 1
        if 'restart' not in off and stall >= p['stall']:
            rank, _ = fronts_and_crowding(PF)
            worst = np.argsort(-rank, kind='stable')[:max(1, int(N * p['restart_fraction']))]
            for i in worst:
                base = A.X[int(rng.integers(len(A)))]
                X[i] = np.where(rng.random(d) < p['restart_flip'], ~base, base)
                V[i] = 0.0
            X = repair(X, rng)
            # restarted particles are scored at once and become their own personal best
            # (otherwise they would be moved again before anyone looked at them)
            if fit.remaining() - ls_budget >= len(worst):
                FW = fit.batch(X[worst])
                P[worst], PF[worst] = X[worst], FW
                for x, f in zip(X[worst], FW):
                    A.add(x, f)
            stall = 0
        it += 1
        hv_trace(trace, fit, A)
    if ls_budget > 0:
        archive_local_search(fit, A, unit_rank, rng)
        hv_trace(trace, fit, A)
    return A, trace


def archive_local_search(fit, A, unit_rank, rng):
    """Spend the remaining calls on archive members, taking turns between members.
    Move 1: remove the weakest-ANOVA selected unit (fills the small-set end of the front).
    Move 2: add the strongest-ANOVA unselected unit (fills the accurate end).
    Every (member, move) pair is tried once; stops when the budget is used or nothing is left to try."""
    tried = set()
    while fit.remaining() > 0:
        progress = False
        for j in rng.permutation(len(A)):
            if fit.remaining() <= 0 or j >= len(A):
                break
            x = A.X[j]
            key = np.packbits(x).tobytes()
            for move in ('drop', 'add'):
                if (key, move) in tried or fit.remaining() <= 0:
                    continue
                tried.add((key, move))
                m = x.copy()
                if move == 'drop':
                    on = [u for u in unit_rank[::-1] if m[u]]
                    if len(on) <= 1:
                        continue
                    m[on[0]] = False
                else:
                    offu = [u for u in unit_rank if not m[u]]
                    if not offu:
                        continue
                    m[offu[0]] = True
                A.add(m, fit(m))
                progress = True
        if not progress:
            break


# ------------------------------------------------------------------ dispatcher
def run_algorithm(name, fit, d, rng, cfg, params, unit_rank, unit_score, ordered):
    """name: 'mopso', 'mopso+init', 'nsga2', 'emopso' or 'emopso-<component>'."""
    if name == 'mopso':
        return mopso(fit, d, rng, cfg, params['mopso'])
    if name == 'mopso+init':
        e = params['emopso']
        init = repair(anova_stratified_masks(rng, cfg['pop'], d, cfg['init_density'], unit_rank,
                                             e['anova_strength'], e['seed_units']), rng)
        return mopso(fit, d, rng, cfg, params['mopso'], init=init)
    if name == 'nsga2':
        return nsga2(fit, d, rng, cfg, params['nsga2'])
    if name == 'emopso' or name.startswith('emopso-'):
        off = name.split('-')[1:]
        bad = [c for c in off if c not in EMOPSO_COMPONENTS]
        if bad:
            raise ValueError(f'unknown emopso component(s) {bad}; choose from {EMOPSO_COMPONENTS}')
        q = dict(params['emopso'])
        q.setdefault('mutation_rate', params['mopso']['mutation_rate'])
        q.setdefault('inertia_fixed', params['mopso']['inertia'])
        return emopso(fit, d, rng, cfg, q, unit_rank, unit_score, ordered, off)
    raise ValueError(f'unknown algorithm {name}')
