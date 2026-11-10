"""Experiment 4: multi-objective region selection. Enhanced MOPSO (emopso) against the baseline MOPSO
(Coello Coello et al. 2004) and NSGA-II, with one fitness, one budget and identical folds.

Each run returns a Pareto front (accuracy against number of bins). The front is then handled identically for
every algorithm: re-scored on fresh folds of the selection data, one set chosen by the one-standard-error
rule (and the knee point), and the chosen sets are scored with the six models (5-fold CV on 2015-2017,
then 2018 once).

Usage (full run, one input at a time):
    python experiment4_mopso.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4/ \\
           --runner maria --input Var-2000
Ablation (proposed method minus one component, and the baseline with the ANOVA start):
    python experiment4_mopso.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4_ablation/ \\
           --runner maria --input Var-2000 --algorithms ablation
Demo on a sample (small and fast; never mixed with real results):
    python experiment4_mopso.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4_demo/ \\
           --runner maria --input Var-2000 --antibiotic Ceftriaxone --sample-frac 0.3 --budget 300 --seeds 0,1

Outputs, in <out_dir>/<antibiotic>/ :
    exp4_<input>_fronts.csv   one row per algorithm x seed x front point (search and re-scored objectives)
    exp4_<input>_runs.csv     one row per algorithm x seed (hypervolume, chosen set, calls, time, stability)
    exp4_<input>_test.csv     one row per algorithm x seed x solution (chosen / knee) x model
    exp4_<input>_log.txt      code version, settings fingerprint, timings
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
os.environ.setdefault('PYTHONWARNINGS', 'ignore')
import argparse, hashlib, json, platform, sys, time, warnings
import numpy as np, pandas as pd, yaml
from joblib import Parallel, delayed
from sklearn.feature_selection import f_classif
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit
import common as C
import mopso as M
from experiment3_optimisers import build_input, evaluate, git_commit

warnings.filterwarnings('ignore')


def load_settings(path):
    raw = open(path, 'rb').read()
    S = yaml.safe_load(raw)
    S['_sha'] = hashlib.sha256(raw).hexdigest()[:12]
    return S


def sample_task(Xtr, ytr, Xte, yte, frac, seed=0):
    """Stratified sample of the training and test isolates (demo only)."""
    def take(X, y):
        i = next(StratifiedShuffleSplit(1, train_size=frac, random_state=seed).split(X, y))[0]
        i = np.sort(i)
        return X[i], y[i]
    a, b = take(Xtr, ytr)
    c, d = take(Xte, yte)
    return a, b, c, d


def knee_index(F):
    """Front point farthest from the line joining the two extreme points (objectives scaled to [0, 1])."""
    if len(F) < 3:
        return int(np.argmin(F[:, 0]))
    lo, hi = F.min(0), F.max(0)
    G = (F - lo) / np.where(hi - lo > 0, hi - lo, 1)
    a, b = G[np.argmin(G[:, 0])], G[np.argmin(G[:, 1])]
    ab = b - a
    if np.allclose(ab, 0):
        return int(np.argmin(F[:, 0]))
    dist = np.abs(ab[0] * (G[:, 1] - a[1]) - ab[1] * (G[:, 0] - a[0])) / np.linalg.norm(ab)
    return int(np.argmax(dist))


def run_one(algo, seed, inp, ytr, units, S, budget):
    se, fi, fc = S['search'], S['fitness'], S['final_choice']
    sub = next(StratifiedShuffleSplit(1, train_size=se['subsample_fraction'], random_state=seed).split(inp.Z, ytr))[0]
    Zs, ys = inp.Z[sub], ytr[sub]
    groups = [inp.groups[u] for u in units]
    d = len(groups)
    n_cols_total = int(sum(len(g) for g in groups))
    Fa, _ = f_classif(Zs, ys)
    Fa = np.nan_to_num(Fa)
    unit_score = np.array([Fa[g].mean() for g in groups])
    unit_rank = np.argsort(-unit_score, kind='stable')
    ordered = bool(np.all(inp.bin_of_col >= 0))                 # regions ordered by m/z (not PCA)
    cfg = dict(pop=se['population'], archive_size=se['archive_size'], init_density=tuple(se['init_density']))
    fit = M.MOFitness(Zs, ys, groups, budget, fi['wrapper_classifier'], fi['inner_folds'], fi['inner_seed'],
                      n_cols_total)
    rng = np.random.default_rng(1000 + seed)
    t = time.time()
    A, trace = M.run_algorithm(algo, fit, d, rng, cfg, S['algorithms']['params'], unit_rank, unit_score, ordered)
    sec = time.time() - t

    # ---- identical post-processing for every algorithm (outside the budget, selection data only)
    FX, FF = np.array(A.X), np.array(A.F)
    folds_r = []
    for r in range(fc['rescore_repeats']):
        folds_r += list(StratifiedKFold(fi['inner_folds'], shuffle=True,
                                        random_state=10_000 + 97 * seed + r).split(Zs, ys))
    AP = np.array([M.cv_auprc(Zs, ys, fit.cols(m), folds_r, fi['wrapper_classifier']) for m in FX])
    mean, sem = AP.mean(1), AP.std(1, ddof=1) / np.sqrt(AP.shape[1])
    ncols = np.array([len(fit.cols(m)) for m in FX])
    FR = np.column_stack([1 - mean, ncols / n_cols_total])
    b = int(np.argmax(mean))
    ok = np.flatnonzero(mean >= mean[b] - sem[b])
    chosen = int(ok[np.lexsort((-mean[ok], ncols[ok]))[0]])     # fewest columns, then highest mean
    knee = knee_index(FR)

    def full(m):
        z = np.zeros(len(inp.groups), bool)
        z[np.asarray(units)[m]] = True
        return z

    front = [dict(point=i, f1_search=float(FF[i, 0]), f2_search=float(FF[i, 1]),
                  auprc_search=float(1 - FF[i, 0]), auprc_rescored=float(mean[i]), auprc_rescored_se=float(sem[i]),
                  n_units=int(FX[i].sum()), n_columns=int(ncols[i]), frac_columns=float(ncols[i] / n_cols_total),
                  chosen=i == chosen, knee=i == knee,
                  regions=json.dumps(np.flatnonzero(full(FX[i])).tolist())) for i in range(len(FX))]
    return dict(algorithm=algo, seed=seed, front=front, sec=sec, calls=fit.calls, budget=budget,
                hv_search=M.hypervolume_2d(FF), hv_rescored=M.hypervolume_2d(FR), front_size=len(FX),
                chosen_mask=full(FX[chosen]), knee_mask=full(FX[knee]),
                chosen_columns=int(ncols[chosen]), chosen_auprc_rescored=float(mean[chosen]),
                knee_columns=int(ncols[knee]), knee_auprc_rescored=float(mean[knee]),
                trace=[(int(c), round(float(h), 5)) for c, h in trace[::max(len(trace) // 100, 1)]])


def expand_algorithms(arg, S):
    out = []
    for a in arg.split(','):
        a = a.strip()
        out += S['algorithms'][a] if a in ('default', 'ablation') else [a]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir'); ap.add_argument('labels_csv'); ap.add_argument('out_dir')
    ap.add_argument('--runner', required=True, choices=['joud', 'maria', 'zainab'])
    ap.add_argument('--input', required=True, choices=['Raw-6000', 'Var-2000', 'PCA-200'])
    ap.add_argument('--antibiotic', default=None, help='one antibiotic only')
    ap.add_argument('--algorithms', default='default', help="comma list, or 'default' / 'ablation'")
    ap.add_argument('--budget', type=int, default=None, help='override the budget (demo or pilot only)')
    ap.add_argument('--seeds', default=None, help='e.g. 0,1 (demo or pilot only)')
    ap.add_argument('--sample-frac', type=float, default=None,
                    help='DEMO ONLY: use a stratified share of the isolates (results are not valid for the paper)')
    ap.add_argument('--settings', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                       'config', 'experiment4_mopso.yaml'))
    ap.add_argument('--n-jobs', type=int, default=None)
    ap.add_argument('--skip-final', action='store_true', help='search only, skip the six-model scoring')
    args = ap.parse_args()

    S = load_settings(args.settings)
    algos = expand_algorithms(args.algorithms, S)
    seeds = [int(s) for s in args.seeds.split(',')] if args.seeds else S['search']['seeds']
    budget = args.budget or S['search']['budget_fitness_calls']
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
        if args.sample_frac:
            Xtr, ytr, Xte, yte = sample_task(Xtr, ytr, Xte, yte, args.sample_frac)
        inp = build_input(args.input, S, Xtr, Xte)
        units = [i for i, g in enumerate(inp.groups) if len(g)]
        print(f'[{abx} | {args.input}] train {len(ytr)} ({ytr.sum()} non-S)  test {len(yte)} ({yte.sum()} non-S)  '
              f'units {len(units)} of {len(inp.groups)}  budget {budget}  wrapper {S["fitness"]["wrapper_classifier"]}'
              f'{"  SAMPLE " + str(args.sample_frac) if args.sample_frac else ""}', flush=True)

        runs = Parallel(n_jobs=n_jobs)(delayed(run_one)(a, s, inp, ytr, units, S, budget) for a in algos for s in seeds)
        t_search = time.time() - t0

        fronts, rows = [], []
        for a in algos:
            rs = [r for r in runs if r['algorithm'] == a]
            stab = C.nogueira_stability([r['chosen_mask'][units] for r in rs])
            for r in rs:
                for p in r['front']:
                    fronts.append(dict(antibiotic=abx, input=args.input, algorithm=a, seed=r['seed'], **p))
                rows.append(dict(antibiotic=abx, input=args.input, algorithm=a, seed=r['seed'],
                                 hv_search=r['hv_search'], hv_rescored=r['hv_rescored'], front_size=r['front_size'],
                                 chosen_columns=r['chosen_columns'], chosen_auprc_rescored=r['chosen_auprc_rescored'],
                                 knee_columns=r['knee_columns'], knee_auprc_rescored=r['knee_auprc_rescored'],
                                 stability_chosen=stab, fitness_calls=r['calls'], budget=r['budget'],
                                 budget_ok=bool(r['calls'] <= r['budget']), search_sec=round(r['sec'], 1),
                                 sample_frac=args.sample_frac or 1.0,
                                 chosen_regions=json.dumps(np.flatnonzero(r['chosen_mask']).tolist()),
                                 hv_trace=json.dumps(r['trace'])))
        pd.DataFrame(fronts).to_csv(f'{out}/exp4_{args.input}_fronts.csv', index=False)
        R = pd.DataFrame(rows)
        R.to_csv(f'{out}/exp4_{args.input}_runs.csv', index=False)

        if not args.skip_final:
            folds = C.train_folds(ytr)
            jobs = []
            for r in runs:
                jobs.append(('chosen', dict(algorithm=r['algorithm'], seed=r['seed'], mask=r['chosen_mask'])))
                if S['final_choice'].get('also_score_knee', True):
                    jobs.append(('knee', dict(algorithm=r['algorithm'], seed=r['seed'], mask=r['knee_mask'])))
            res = Parallel(n_jobs=n_jobs)(delayed(evaluate)(run, inp, ytr, yte, folds, S['final_evaluation']['svm_C'],
                                                            m, None)
                                          for _, run in jobs for m in S['final_evaluation']['models'])
            sol = [s for s, _ in jobs for _ in S['final_evaluation']['models']]
            T = pd.DataFrame(res)
            T.insert(0, 'solution', sol)
            T.insert(0, 'input', args.input); T.insert(0, 'antibiotic', abx)
            T.to_csv(f'{out}/exp4_{args.input}_test.csv', index=False)

        with open(f'{out}/exp4_{args.input}_log.txt', 'w') as fh:
            fh.write(f'commit: {git_commit()}\nsettings_sha: {S["_sha"]}\ndate: {time.strftime("%Y-%m-%d %H:%M")}\n')
            if args.sample_frac:
                fh.write(f'*** SAMPLE MODE ({args.sample_frac} of the isolates): demo only, not for the paper ***\n')
            fh.write(f'args: {vars(args)}\nalgorithms: {algos}\nseeds: {seeds}\nbudget: {budget}\n')
            fh.write(f'train {len(ytr)} ({int(ytr.sum())} non-S)  test {len(yte)} ({int(yte.sum())} non-S)  '
                     f'units searched {len(units)}\n')
            fh.write(f'python {platform.python_version()}  numpy {np.__version__}  pandas {pd.__version__}\n')
            fh.write(f'search minutes: {t_search / 60:.1f}   total minutes: {(time.time() - t0) / 60:.1f}\n')
            fh.write(R.groupby('algorithm')[['hv_rescored', 'chosen_columns', 'chosen_auprc_rescored', 'front_size',
                                            'stability_chosen', 'search_sec']].mean().round(4).to_string())
            fh.write(f'\nall budgets respected: {bool(R.budget_ok.all())}\n')
        print(R.groupby('algorithm')[['hv_search', 'hv_rescored', 'chosen_columns', 'chosen_auprc_rescored',
                                      'stability_chosen', 'search_sec']].mean().round(4).to_string())
        print(f'[{abx}] budgets respected: {bool(R.budget_ok.all())}; done in {(time.time() - t0) / 60:.1f} min',
              flush=True)


if __name__ == '__main__':
    main()
