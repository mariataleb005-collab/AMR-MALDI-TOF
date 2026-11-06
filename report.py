"""Summary tables, Friedman / Nemenyi tests and the region map for Steps 2 and 3.

Usage: python report.py <results_dir>
Writes <results_dir>/summary_*.csv and <results_dir>/fig_*.png
"""
import sys, glob, json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common as C

# Nemenyi critical values q_0.05 (Demsar 2006), index = number of compared methods
Q05 = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031, 9: 3.102, 10: 3.164,
       11: 3.219, 12: 3.268, 13: 3.313, 14: 3.354, 15: 3.391}


def friedman(table):
    """table: rows = datasets (antibiotics), cols = methods, higher is better."""
    t = table.dropna(axis=1)
    N, k = t.shape
    if N < 3 or k < 2:
        return None
    ranks = t.rank(axis=1, ascending=False)
    chi2, p = stats.friedmanchisquare(*[t[c] for c in t.columns])
    ff = (N - 1) * chi2 / max(N * (k - 1) - chi2, 1e-12)          # Iman-Davenport
    p_id = 1 - stats.f.cdf(ff, k - 1, (k - 1) * (N - 1))
    cd = Q05.get(k, np.nan) * np.sqrt(k * (k + 1) / (6 * N))
    return ranks.mean().sort_values(), chi2, p, ff, p_id, cd


def write_friedman(name, table, out):
    r = friedman(table)
    if r is None:
        return
    mean_ranks, chi2, p, ff, p_id, cd = r
    df = mean_ranks.rename('mean_rank').to_frame()
    df.attrs = {}
    with open(f'{out}/summary_{name}_friedman.txt', 'w') as f:
        f.write(f'datasets={len(table)} methods={table.shape[1]}\n'
                f'Friedman chi2={chi2:.3f} p={p:.4g}; Iman-Davenport F={ff:.3f} p={p_id:.4g}; '
                f'Nemenyi CD(0.05)={cd:.3f}\n\n{df.to_string()}\n')
    # critical-difference style plot
    fig, ax = plt.subplots(figsize=(7, 0.35 * len(df) + 1))
    ax.barh(df.index[::-1], df['mean_rank'][::-1], color='#4C78A8')
    best = df['mean_rank'].min()
    ax.axvline(best + cd, color='#E45756', ls='--', label=f'best + CD ({cd:.2f})')
    ax.set_xlabel('mean rank over antibiotics (lower = better)'); ax.legend(loc='lower right', fontsize=8)
    ax.set_title(f'{name}: Friedman p = {p_id:.3g} (Iman-Davenport)', fontsize=10)
    fig.tight_layout(); fig.savefig(f'{out}/fig_{name}_ranks.png', dpi=160); plt.close(fig)


def step2(out):
    files = glob.glob(f'{out}/step2_test_*.csv')
    if not files:
        return
    T = pd.concat(map(pd.read_csv, files), ignore_index=True)
    T.round(4).to_csv(f'{out}/summary_step2_all.csv', index=False)
    for metric in ('cv_AUPRC_mean', 'test_AUPRC'):
        piv = T.pivot_table(index=['model', 'input'], columns='antibiotic', values=metric)
        piv['mean'] = piv.mean(axis=1)
        piv.round(3).to_csv(f'{out}/summary_step2_{metric}.csv')
    best_input = T.loc[T.groupby(['antibiotic', 'model'])['cv_AUPRC_mean'].idxmax()]
    best_input[['antibiotic', 'model', 'input', 'best_config', 'cv_AUPRC_mean', 'test_AUROC',
                'test_AUPRC', 'test_MCC', 'test_BalAcc', 'test_VME', 'test_ME']].round(3) \
        .to_csv(f'{out}/summary_step2_best_input_per_model.csv', index=False)
    # which input wins, across antibiotics x models (each model-antibiotic pair is one "dataset")
    tab = T.pivot_table(index=['antibiotic', 'model'], columns='input', values='cv_AUPRC_mean')
    write_friedman('step2_inputs', tab, out)
    tab = T.pivot_table(index='antibiotic', columns=['model', 'input'], values='cv_AUPRC_mean')
    tab.columns = [f'{m} | {i}' for m, i in tab.columns]
    top = tab.mean().sort_values(ascending=False).index[:15]
    write_friedman('step2_top15_pipelines', tab[top], out)


def step3(out):
    files = glob.glob(f'{out}/step3_test_*.csv')
    if not files:
        return
    T = pd.concat(map(pd.read_csv, files), ignore_index=True)
    S = pd.concat(map(pd.read_csv, glob.glob(f'{out}/step3_selections_*.csv')), ignore_index=True)
    agg = T.groupby(['antibiotic', 'selector', 'model'])[['test_AUROC', 'test_AUPRC', 'n_bins', 'n_regions']].mean()
    agg.round(4).to_csv(f'{out}/summary_step3_by_model.csv')
    # main table: per selector, mean over seeds and antibiotics
    main = T.groupby(['selector', 'model'])['test_AUPRC'].mean().unstack('model')
    main['mean_AUPRC'] = main.mean(axis=1)
    sz = S.groupby('selector')[['n_bins', 'n_regions', 'fitness', 'fitness_calls', 'select_sec',
                                'nogueira_stability']].mean()
    allb = T[T.selector == 'All-bins'].groupby('selector')[['n_bins', 'n_regions']].mean()
    sz = pd.concat([sz, allb])
    main.join(sz).sort_values('mean_AUPRC', ascending=False).round(4).to_csv(f'{out}/summary_step3_main.csv')
    for model in ('LR', 'LightGBM', 'SVM'):
        tab = T[T.model == model].groupby(['antibiotic', 'selector'])['test_AUPRC'].mean().unstack()
        write_friedman(f'step3_selectors_{model}', tab, out)
    fit = S.groupby(['antibiotic', 'selector'])['fitness'].mean().unstack()
    write_friedman('step3_fitness_value', fit.drop(columns=[c for c in fit if fit[c].isna().all()]), out)

    # region map across antibiotics
    R = pd.concat(map(pd.read_csv, glob.glob(f'{out}/step3_regions_*.csv')), ignore_index=True)
    R.round(4).to_csv(f'{out}/summary_step3_important_regions.csv', index=False)
    shared = R.groupby('region').agg(n_antibiotics=('antibiotic', 'nunique'),
                                    antibiotics=('antibiotic', lambda s: ', '.join(sorted(s))),
                                    mz_from=('mz_from', 'first'), mz_to=('mz_to', 'first')) \
        .sort_values('n_antibiotics', ascending=False)
    shared.to_csv(f'{out}/summary_step3_shared_regions.csv')
    abx = [a for a in C.ANTIBIOTICS if a in set(R.antibiotic)]
    fig, ax = plt.subplots(figsize=(11, 0.55 * len(abx) + 1.2))
    for i, a in enumerate(abx):
        r = R[R.antibiotic == a]
        imp = r['dAUPRC_if_removed'].clip(lower=0)
        size = 20 + 2000 * imp
        col = np.where(r['direction'] == 'higher in R', '#E45756', '#4C78A8')
        ax.scatter((r.mz_from + r.mz_to) / 2, np.full(len(r), i), s=size, c=col, alpha=0.8, edgecolor='k', lw=0.3)
    ax.set_yticks(range(len(abx))); ax.set_yticklabels(abx)
    ax.set_xlim(2000, 20000); ax.set_xlabel('m/z (Da)')
    ax.set_title('RA-PSO signature regions (size = AUPRC lost if removed; red = higher in R, blue = higher in S)',
                 fontsize=9)
    ax.grid(axis='x', alpha=0.3)
    fig.tight_layout(); fig.savefig(f'{out}/fig_step3_region_map.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    out = sys.argv[1]
    step2(out)
    step3(out)
    print('report written to', out)


