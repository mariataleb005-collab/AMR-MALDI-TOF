"""Export the final ATHAR models (one per antibiotic) from the Experiment 4 results. Training years only.

For each of the 13 antibiotics:
  1. regions   : Raw-6000 Enhanced MOPSO chosen sets of the 10 seeds (exp4_Raw-6000_runs.csv);
                 keep the regions chosen by at least --min-votes seeds (default 5 of 10 = consensus).
                 If fewer than 3 regions pass, take the k most-voted regions instead
                 (k = median number of regions per seed; ties broken by the lower region id) and flag it.
  2. classifier: RF, XGBoost and LightGBM (same settings as the final evaluation), 5-fold CV on 2015-2017
                 with the same folds as the experiments; the one with the highest mean CV AUPRC is kept.
  3. threshold : Youden threshold from the out-of-fold CV predictions of that classifier (training years).
  4. final fit : the chosen classifier is refitted on all of 2015-2017 and saved with everything ATHAR needs.

The 2018 isolates are never loaded, and no *_test.csv file is read.

Usage (from the repository root):
    python export_athar_models.py "<spectra folder>" data/labels_ecoli_A_corrected.csv results/exp4 models/athar

Outputs in <out_dir>/ :
    <Antibiotic>.joblib    one bundle per antibiotic (model, bins, regions, m/z ranges, threshold, metadata)
    manifest.json          one entry per antibiotic (what ATHAR lists), plus code and library versions
    export_summary.csv     one row per antibiotic: regions, bins, classifier, CV AUROC/AUPRC of all three
    export_log.txt         commit, settings fingerprint, date, timings

In ATHAR:
    from export_athar_models import load_bundle, predict
    b = load_bundle('models/athar/Ciprofloxacin.joblib')
    p, call = predict(b, spectrum)      # spectrum: DRIAMS binned_6000 vector (6000 values, same preprocessing)
"""
import os
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import argparse, hashlib, json, platform, sys, time, warnings
import numpy as np, pandas as pd
import joblib
from joblib import Parallel, delayed

warnings.filterwarnings('ignore')

CANDIDATES = ['RF', 'XGBoost', 'LightGBM']     # the three models whose mean is cv_AUPRC in the report
INPUT, ALGO, N_SEEDS = 'Raw-6000', 'emopso', 10


# ---------------------------------------------------------------- used by ATHAR
def load_bundle(path):
    return joblib.load(path)


def predict(bundle, spectrum):
    """spectrum: 1-D array of 6000 binned intensities (DRIAMS binned_6000). Returns (score, 'R' or 'S').
    'R' means non-susceptible (I or R), the positive class of the study."""
    x = np.asarray(spectrum, dtype=np.float32).reshape(-1)
    if x.shape[0] != bundle['n_bins_expected']:
        raise ValueError(f"expected {bundle['n_bins_expected']} bins, got {x.shape[0]}")
    p = float(bundle['model'].predict_proba(x[bundle['bins']][None, :])[0, 1])
    return p, ('R' if p >= bundle['threshold'] else 'S')


# ---------------------------------------------------------------- export
def consensus_regions(runs, min_votes):
    sets = [json.loads(s) for s in runs['chosen_regions']]
    votes = pd.Series(np.concatenate([np.asarray(s, int) for s in sets])).value_counts()
    regions = sorted(int(r) for r, v in votes.items() if v >= min_votes)
    rule = f'consensus: chosen by >= {min_votes} of {len(sets)} seeds'
    if len(regions) < 3:
        k = int(np.median([len(s) for s in sets]))
        ranked = sorted(votes.items(), key=lambda t: (-t[1], t[0]))
        regions = sorted(int(r) for r, _ in ranked[:k])
        rule = f'fallback: top {k} most-voted regions (fewer than 3 passed >= {min_votes} votes)'
    return regions, {int(r): int(v) for r, v in votes.items()}, rule, [len(s) for s in sets]


def cv_one(name, A, y, folds, pos_weight, final_models):
    from sklearn.base import clone
    from sklearn.metrics import average_precision_score, roc_auc_score
    est0, scaled = final_models(pos_weight, 10)[name]
    assert not scaled, 'tree models use unscaled intensities'
    oof, aps, aucs = np.zeros(len(y)), [], []
    for tr, va in folds:
        m = clone(est0).fit(A[tr], y[tr])
        oof[va] = m.predict_proba(A[va])[:, 1]
        aps.append(average_precision_score(y[va], oof[va]))
        aucs.append(roc_auc_score(y[va], oof[va]))
    return dict(model=name, cv_AUPRC=float(np.mean(aps)), cv_AUPRC_sd=float(np.std(aps, ddof=1)),
                cv_AUROC=float(np.mean(aucs)), oof=oof)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_dir'); ap.add_argument('labels_csv'); ap.add_argument('results'); ap.add_argument('out_dir')
    ap.add_argument('--min-votes', type=int, default=5, help='seeds (of 10) that must choose a region')
    ap.add_argument('--antibiotic', default=None, help='one antibiotic only')
    ap.add_argument('--n-jobs', type=int, default=3)
    args = ap.parse_args()

    import common as C
    from experiment3_optimisers import final_models, git_commit
    import sklearn, xgboost, lightgbm

    abx_list = [args.antibiotic] if args.antibiotic else C.ANTIBIOTICS
    os.makedirs(args.out_dir, exist_ok=True)
    X = C.load_spectra(args.data_dir)
    L = C.load_labels(args.labels_csv)
    if X.shape[0] != len(L) or X.shape[1] != C.N_BINS:
        sys.exit(f'spectra {X.shape} do not match labels ({len(L)} rows) and {C.N_BINS} bins')
    t0, manifest, rows = time.time(), {}, []

    for abx in abx_list:
        t = time.time()
        p_runs = os.path.join(args.results, abx.replace(' ', '_'), f'exp4_{INPUT}_runs.csv')
        if not os.path.exists(p_runs):
            sys.exit(f'missing {p_runs}')
        R = pd.read_csv(p_runs)
        R = R[R.algorithm == ALGO]
        problems = []
        if len(R) != N_SEEDS: problems.append(f'{len(R)} {ALGO} rows, expected {N_SEEDS}')
        if not R.budget_ok.all(): problems.append('budget not respected')
        if (R.sample_frac < 1).any(): problems.append('sample (demo) runs')
        if set(R.antibiotic) != {abx} or set(R.input) != {INPUT}: problems.append('wrong antibiotic or input in file')
        if problems:
            sys.exit(f'[{abx}] stopped: ' + '; '.join(problems))

        regions, votes, rule, sizes = consensus_regions(R, args.min_votes)
        bins = C.region_to_bins(regions)

        # training years only: 2018 rows are never loaded
        tr = (L[abx].notna() & (L['year'] < C.TEST_YEAR)).to_numpy()
        y = L.loc[tr, abx].to_numpy().astype(int)
        A = np.asarray(X[np.flatnonzero(tr)][:, bins], dtype=np.float32)
        folds = C.train_folds(y)
        pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)

        cv = Parallel(n_jobs=args.n_jobs)(delayed(cv_one)(m, A, y, folds, pos_weight, final_models)
                                          for m in CANDIDATES)
        best = max(cv, key=lambda d: (d['cv_AUPRC'], -CANDIDATES.index(d['model'])))
        thr = C.youden_threshold(y, best['oof'])
        from sklearn.base import clone
        model = clone(final_models(pos_weight, 10)[best['model']][0]).fit(A, y)

        try:                                            # region importance for the ATHAR explanation view
            imp = np.asarray(model.feature_importances_, dtype=float)
            imp = imp / imp.sum() if imp.sum() > 0 else imp
            region_imp = imp.reshape(len(regions), C.REGION).sum(1)
        except Exception:
            region_imp = np.full(len(regions), np.nan)
        region_info = [dict(region=int(r), mz_from=C.mz_range(r)[0], mz_to=C.mz_range(r)[1],
                            votes=votes.get(int(r), 0), importance=float(i))
                       for r, i in zip(regions, region_imp)]

        bundle = dict(antibiotic=abx, input=INPUT, algorithm=ALGO, classifier=best['model'], model=model,
                      bins=bins.astype(int), regions=regions, region_info=region_info, n_bins_expected=C.N_BINS,
                      threshold=float(thr), threshold_rule='Youden, out-of-fold CV predictions, 2015-2017',
                      positive_class='non-susceptible (I or R)', region_rule=rule,
                      cv={d['model']: dict(cv_AUPRC=d['cv_AUPRC'], cv_AUPRC_sd=d['cv_AUPRC_sd'],
                                           cv_AUROC=d['cv_AUROC']) for d in cv},
                      n_train=int(len(y)), n_train_nonS=int(y.sum()), train_years='2015-2017',
                      created=time.strftime('%Y-%m-%d %H:%M'), commit=git_commit(),
                      versions=dict(python=platform.python_version(), numpy=np.__version__,
                                    sklearn=sklearn.__version__, xgboost=xgboost.__version__,
                                    lightgbm=lightgbm.__version__))
        fname = f"{abx.replace(' ', '_')}.joblib"
        path = os.path.join(args.out_dir, fname)
        joblib.dump(bundle, path, compress=3)

        # self-check: the saved bundle gives the same scores as the model in memory
        b2 = load_bundle(path)
        idx = np.flatnonzero(tr)[:20]
        p_mem = model.predict_proba(A[:20])[:, 1]
        p_disk = np.array([predict(b2, np.asarray(X[i], dtype=np.float32))[0] for i in idx])
        if not np.allclose(p_mem, p_disk, atol=1e-6):
            sys.exit(f'[{abx}] self-check failed: saved model does not reproduce the scores')

        size_mb = os.path.getsize(path) / 1e6
        manifest[abx] = dict(file=fname, classifier=best['model'], n_regions=len(regions), n_bins=int(len(bins)),
                             threshold=float(thr), cv_AUPRC=best['cv_AUPRC'], cv_AUROC=best['cv_AUROC'],
                             region_rule=rule, size_mb=round(size_mb, 2))
        rows.append(dict(antibiotic=abx, n_regions=len(regions), n_bins=int(len(bins)),
                         median_regions_per_seed=float(np.median(sizes)), region_rule=rule,
                         classifier=best['model'], threshold=round(float(thr), 4), n_train=len(y),
                         n_train_nonS=int(y.sum()), size_mb=round(size_mb, 2),
                         **{f'{d["model"]}_cv_AUPRC': round(d['cv_AUPRC'], 4) for d in cv},
                         **{f'{d["model"]}_cv_AUROC': round(d['cv_AUROC'], 4) for d in cv}))
        print(f'[{abx}] {len(regions)} regions ({len(bins)} bins; seeds chose median {np.median(sizes):.0f}) '
              f'-> {best["model"]}  CV AUPRC {best["cv_AUPRC"]:.3f}  threshold {thr:.3f}  '
              f'{size_mb:.1f} MB  {time.time() - t:.0f}s  self-check OK', flush=True)

    S = pd.DataFrame(rows)
    if not args.antibiotic:
        S.to_csv(os.path.join(args.out_dir, 'export_summary.csv'), index=False)
        with open(os.path.join(args.out_dir, 'manifest.json'), 'w') as fh:
            json.dump(dict(input=INPUT, algorithm=ALGO, min_votes=args.min_votes, created=time.strftime('%Y-%m-%d %H:%M'),
                           commit=git_commit(), antibiotics=manifest), fh, indent=2)
    sha = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read().replace(b'\r\n', b'\n')).hexdigest()[:12]
    with open(os.path.join(args.out_dir, 'export_log.txt'), 'a') as fh:
        fh.write(f'commit: {git_commit()}\nscript_sha: {sha}\ndate: {time.strftime("%Y-%m-%d %H:%M")}\n'
                 f'args: {vars(args)}\nminutes: {(time.time() - t0) / 60:.1f}\n'
                 f'2018 isolates loaded: no\n{S.to_string(index=False)}\n\n')
    print(f'done: {len(rows)} antibiotics in {(time.time() - t0) / 60:.1f} min -> {args.out_dir}')


if __name__ == '__main__':
    main()
