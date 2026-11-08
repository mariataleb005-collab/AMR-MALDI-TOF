"""Summarise Experiment 3 development rounds on the TRAINING years only (2018 scores are never read).

For every method (the four baselines in results/exp3/ and each enhanced-PSO version in results/exp3_rounds/<V>/)
and every antibiotic, it reports, averaged over the seeds:
  fitness        search score (KNN AUPRC on inner folds of the training years minus the size penalty)
  bins           number of m/z bins selected
  stability      Nogueira index over the seeds, as written by the experiment script (all 600 regions)
  stab_nonempty  the same index computed only on regions that still have bins in this input
                 (needs the spectra folder; empty regions do not change the model but add noise to stability)
  cv_AUROC/AUPRC 5-fold CV on 2015-2017 of the final models, mean of RF, XGBoost and LightGBM

Usage:
  python summarise_rounds.py [--input Var-2000] [--spectra "<folder with spectra_ecoli_A.npy>"]
Output: printed tables and results/exp3_rounds/summary_training_only.csv
"""
import argparse, glob, json, os
import numpy as np
import pandas as pd
import yaml
import common as C

TREE_MODELS = ['RF', 'XGBoost', 'LightGBM']
SEL_COLS = ['antibiotic', 'algorithm', 'seed', 'n_columns', 'fitness', 'nogueira_stability', 'regions']
CV_COLS = ['algorithm', 'seed', 'model', 'cv_AUROC', 'cv_AUPRC']          # no test_* column is read


def nonempty_regions(X, L, abx, S, inp_name):
    spec = S['inputs'][inp_name]
    if spec['type'] == 'raw':
        return np.arange(C.N_REGIONS)
    if spec['type'] != 'top_variance':
        return None                                        # PCA: components, no empty units
    Xtr = C.get_task(X, L, abx)[0]
    cols = np.argsort(Xtr.var(0))[::-1][:spec['k']]        # same ranking as build_input (training years only)
    return np.unique(cols // C.REGION)


def summarise(folder, label_of, inp_name, keep, X, L, S, cache):
    rows = []
    for d in sorted(glob.glob(os.path.join(folder, '*'))):
        sel_p = os.path.join(d, f'exp3_{inp_name}_selections.csv')
        cv_p = os.path.join(d, f'exp3_{inp_name}_test.csv')
        if not os.path.exists(sel_p):
            continue
        sel = pd.read_csv(sel_p, usecols=SEL_COLS)
        cv = pd.read_csv(cv_p, usecols=CV_COLS) if os.path.exists(cv_p) else None
        abx = sel['antibiotic'].iloc[0]
        for alg, g in sel.groupby('algorithm'):
            if alg not in keep:
                continue
            r = dict(antibiotic=abx, method=label_of(alg), fitness=g['fitness'].mean(),
                     bins=g['n_columns'].mean(), stability=g['nogueira_stability'].iloc[0])
            if X is not None:
                if abx not in cache:
                    cache[abx] = nonempty_regions(X, L, abx, S, inp_name)
                use = cache[abx]
                if use is not None:
                    masks = np.zeros((len(g), C.N_REGIONS), bool)
                    for i, reg in enumerate(g['regions']):
                        masks[i, json.loads(reg)] = True
                    r['stab_nonempty'] = C.nogueira_stability(masks[:, use])
            if cv is not None:
                c = cv[(cv['algorithm'] == alg) & cv['model'].isin(TREE_MODELS)]
                r['cv_AUROC'], r['cv_AUPRC'] = c['cv_AUROC'].mean(), c['cv_AUPRC'].mean()
            rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='Var-2000')
    ap.add_argument('--spectra', default=None, help='folder with spectra_ecoli_A.npy (for stab_nonempty)')
    ap.add_argument('--labels', default='data/labels_ecoli_A_corrected.csv')
    ap.add_argument('--settings', default='config/experiment3_settings.yaml')
    ap.add_argument('--baselines', default='results/exp3')
    ap.add_argument('--rounds', default='results/exp3_rounds')
    a = ap.parse_args()

    S = yaml.safe_load(open(a.settings))
    X = C.load_spectra(a.spectra) if a.spectra else None
    L = C.load_labels(a.labels) if a.spectra else None
    cache = {}
    names = {'binary_pso': 'Binary PSO', 'ga': 'GA', 'gwo': 'GWO', 'woa': 'WOA'}
    rows = summarise(a.baselines, lambda x: names[x], a.input, set(names), X, L, S, cache)
    for v in sorted(os.listdir(a.rounds)) if os.path.isdir(a.rounds) else []:
        if os.path.isdir(os.path.join(a.rounds, v)):
            rows += summarise(os.path.join(a.rounds, v), lambda x, v=v: f'Enhanced {v}', a.input,
                              {'enhanced_pso'}, X, L, S, cache)
    if not rows:
        raise SystemExit('no results found')

    T = pd.DataFrame(rows)
    order = ['Binary PSO', 'GA', 'GWO', 'WOA'] + sorted(m for m in T['method'].unique() if m.startswith('Enhanced'))
    T['method'] = pd.Categorical(T['method'], order, ordered=True)
    T = T.sort_values(['antibiotic', 'method'])
    pd.set_option('display.width', 200)
    for abx, g in T.groupby('antibiotic', sort=False):
        print(f'\n=== {abx} (training years only) ===')
        print(g.drop(columns='antibiotic').set_index('method').round(3).to_string())
    n_abx = T['antibiotic'].nunique()
    avg = T.drop(columns='antibiotic').groupby('method', observed=True).mean().round(3)
    print(f'\n=== Average over {n_abx} antibiotics (training years only) ===')
    print(avg.to_string())
    os.makedirs(a.rounds, exist_ok=True)
    T.to_csv(os.path.join(a.rounds, 'summary_training_only.csv'), index=False)
    print(f'\nsaved {os.path.join(a.rounds, "summary_training_only.csv")}')


if __name__ == '__main__':
    main()
