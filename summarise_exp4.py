"""Summarise Experiment 4 (multi-objective region selection) and export tables, statistics and figures.

Reads every <results>/<antibiotic>/exp4_<input>_{runs,fronts,test}.csv and writes to <out>/ :
    exp4_summary.xlsx              all tables below, one sheet each
    per_antibiotic.csv             mean and sd per antibiotic x algorithm
    overall.csv                    mean over antibiotics + mean Friedman rank per metric
    wilcoxon_vs_<proposed>.csv     paired tests of the proposed method against every other algorithm
    friedman.csv                   Friedman test per metric over antibiotics
    ablation.csv                   proposed minus each ablation variant (if ablation runs exist)
    fig_fronts.png, fig_hv_convergence.png, fig_hv_box.png, fig_ablation.png
    summary.md                     short text report

Metrics (all from the training years unless the column name starts with test_):
    hv_rescored     hypervolume of the front after re-scoring on fresh folds (higher is better; ref point (1, 1))
    igd_plus        IGD+ to the reference front = non-dominated union of all algorithms (lower is better)
    chosen_columns  bins in the set chosen by the 1-SE rule; stability_chosen = Nogueira index over seeds
    cv_AUPRC        5-fold CV on 2015-2017 of the chosen set, mean of RF, XGBoost and LightGBM
    test_AUROC, test_AUPRC, test_MCC, test_VME, test_ME   2018, same three models (skipped with --training-only)

Usage:
    python summarise_exp4.py --results results/exp4 --input Var-2000 --out results/exp4_summary
    python summarise_exp4.py --results results/exp4,results/exp4_ablation --input Var-2000 --out results/exp4_summary
    add --training-only during development so no 2018 number is read.
"""
import argparse, glob, json, os
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, wilcoxon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mopso as M

TREES = ['RF', 'XGBoost', 'LightGBM']
COLORS = {'emopso': '#2a78d6', 'mopso': '#eb6834', 'nsga2': '#1baf7a', 'mopso+init': '#eda100'}
NAMES = {'emopso': 'Enhanced MOPSO', 'mopso': 'MOPSO (baseline)', 'nsga2': 'NSGA-II', 'mopso+init': 'MOPSO + ANOVA start'}
HIGHER = {'hv_rescored': True, 'hv_search': True, 'igd_plus': False, 'chosen_columns': False,
          'chosen_auprc_rescored': True, 'stability_chosen': True, 'cv_AUPRC': True, 'test_AUROC': True,
          'test_AUPRC': True, 'test_MCC': True, 'test_VME': False, 'test_ME': False, 'search_sec': False}
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'


def load(results, inp):
    runs, fronts, tests = [], [], []
    for root in results:
        for d in sorted(glob.glob(os.path.join(root, '*'))):
            for kind, lst in (('runs', runs), ('fronts', fronts), ('test', tests)):
                p = os.path.join(d, f'exp4_{inp}_{kind}.csv')
                if os.path.exists(p):
                    lst.append(pd.read_csv(p))
    if not runs:
        raise SystemExit(f'no exp4_{inp}_runs.csv found under {results}')
    cat = lambda l: pd.concat(l, ignore_index=True) if l else pd.DataFrame()
    return cat(runs), cat(fronts), cat(tests)


def add_igd(R, Fr):
    """IGD+ of every run's re-scored front against the union front of all algorithms (per antibiotic)."""
    Fr = Fr.assign(g1=1 - Fr['auprc_rescored'], g2=Fr['frac_columns'])
    igd = {}
    for abx, g in Fr.groupby('antibiotic'):
        P = g[['g1', 'g2']].to_numpy()
        ref = P[M.nondominated(P)]
        for (a, s), h in g.groupby(['algorithm', 'seed']):
            igd[(abx, a, s)] = M.igd_plus(h[['g1', 'g2']].to_numpy(), ref)
    R['igd_plus'] = [igd.get((r.antibiotic, r.algorithm, r.seed), np.nan) for r in R.itertuples()]
    return R


def add_model_scores(R, T, training_only):
    if T.empty:
        return R
    t = T[(T['solution'] == 'chosen') & T['model'].isin(TREES)]
    cols = ['cv_AUROC', 'cv_AUPRC'] + ([] if training_only else
                                       ['test_AUROC', 'test_AUPRC', 'test_MCC', 'test_BalAcc', 'test_VME', 'test_ME'])
    cols = [c for c in cols if c in t.columns]
    m = t.groupby(['antibiotic', 'algorithm', 'seed'])[cols].mean().reset_index()
    return R.merge(m, on=['antibiotic', 'algorithm', 'seed'], how='left')


def metrics_present(R):
    return [m for m in HIGHER if m in R.columns and R[m].notna().any()]


def holm(p):
    p = np.asarray(p, float)
    o = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for k, i in enumerate(o):
        run = max(run, (len(p) - k) * p[i])
        adj[i] = min(run, 1.0)
    return adj


def wilcoxon_table(R, proposed, metrics):
    rows = []
    others = [a for a in R['algorithm'].unique() if a != proposed]
    for m in metrics:
        P = R[R.algorithm == proposed].set_index(['antibiotic', 'seed'])[m]
        res = []
        for o in others:
            Q = R[R.algorithm == o].set_index(['antibiotic', 'seed'])[m]
            j = P.index.intersection(Q.index)
            diff = (P.loc[j] - Q.loc[j]).to_numpy()
            diff = diff[~np.isnan(diff)]
            sgn = diff if HIGHER[m] else -diff
            wins, ties, losses = int((sgn > 1e-12).sum()), int((np.abs(sgn) <= 1e-12).sum()), int((sgn < -1e-12).sum())
            p = wilcoxon(diff).pvalue if len(diff) >= 6 and np.any(diff != 0) else np.nan
            res.append(dict(metric=m, proposed=proposed, other=o, n_pairs=len(diff), median_diff=np.median(diff)
                            if len(diff) else np.nan, wins=wins, ties=ties, losses=losses, p=p))
        ps = [r['p'] for r in res]
        ok = [i for i, p in enumerate(ps) if not np.isnan(p)]
        adj = holm([ps[i] for i in ok]) if ok else []
        for i, r in enumerate(res):
            r['p_holm'] = adj[ok.index(i)] if i in ok else np.nan
        rows += res
    return pd.DataFrame(rows)


def friedman_table(per_abx, algos, metrics):
    rows = []
    for m in metrics:
        W = per_abx.pivot(index='antibiotic', columns='algorithm', values=(m, 'mean'))[algos].dropna()
        ranks = (-W if HIGHER[m] else W).rank(axis=1).mean()
        p = friedmanchisquare(*[W[a] for a in algos]).pvalue if len(W) >= 3 and len(algos) >= 3 else np.nan
        rows.append(dict(metric=m, n_antibiotics=len(W), p=p, **{f'rank_{a}': ranks[a] for a in algos}))
    return pd.DataFrame(rows)


def style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc='left', fontsize=10, color=INK)
    ax.set_xlabel(xlabel, fontsize=9, color=INK2); ax.set_ylabel(ylabel, fontsize=9, color=INK2)
    ax.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)


def fig_fronts(Fr, algos, out, seed=0):
    abx = sorted(Fr['antibiotic'].unique())
    n = len(abx); c = min(n, 3); r = int(np.ceil(n / c))
    fig, axes = plt.subplots(r, c, figsize=(max(4.2 * c, 8.0), 3.4 * r + 0.6), squeeze=False)
    for ax, a in zip(axes.flat, abx):
        for al in algos:
            g = Fr[(Fr.antibiotic == a) & (Fr.algorithm == al) & (Fr.seed == seed)].sort_values('n_columns')
            if g.empty:
                continue
            P = np.column_stack([1 - g['auprc_rescored'], g['frac_columns']])
            g = g[M.nondominated(P)].sort_values('n_columns')
            ax.plot(g['n_columns'], g['auprc_rescored'], '-o', ms=4, lw=2, color=COLORS.get(al, '#6250d6'),
                    label=NAMES.get(al, al), mec='white', mew=1)
            ch = g[g['chosen']]
            ax.plot(ch['n_columns'], ch['auprc_rescored'], 'o', ms=9, mfc='none', mec=COLORS.get(al, '#6250d6'), mew=1.5)
        ax.set_xscale('log')
        style(ax, a, 'Selected bins (log scale)', 'AUPRC, re-scored folds')
    for ax in list(axes.flat)[n:]:
        ax.axis('off')
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=len(l), frameon=False, fontsize=9)
    fig.suptitle(f'Pareto fronts (seed {seed}); open circle = set chosen by the 1-SE rule', x=0.01, ha='left', fontsize=11)
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(os.path.join(out, 'fig_fronts.png'), dpi=160); plt.close(fig)


def fig_convergence(R, algos, out):
    abx = sorted(R['antibiotic'].unique())
    n = len(abx); c = min(n, 3); r = int(np.ceil(n / c))
    fig, axes = plt.subplots(r, c, figsize=(max(4.2 * c, 8.0), 3.2 * r + 0.6), squeeze=False)
    for ax, a in zip(axes.flat, abx):
        for al in algos:
            g = R[(R.antibiotic == a) & (R.algorithm == al)]
            if g.empty:
                continue
            curves = [np.array(json.loads(t)) for t in g['hv_trace']]
            grid = np.linspace(0, max(cv[-1, 0] for cv in curves), 60)
            Y = np.array([np.interp(grid, cv[:, 0], cv[:, 1]) for cv in curves])
            ax.plot(grid, Y.mean(0), lw=2, color=COLORS.get(al, '#6250d6'), label=NAMES.get(al, al))
        style(ax, a, 'Fitness calls', 'Hypervolume (search folds)')
    for ax in list(axes.flat)[n:]:
        ax.axis('off')
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=len(l), frameon=False, fontsize=9)
    fig.suptitle('Hypervolume against fitness calls, mean over seeds', x=0.01, ha='left', fontsize=11)
    fig.tight_layout(rect=(0, 0.07, 1, 0.94))
    fig.savefig(os.path.join(out, 'fig_hv_convergence.png'), dpi=160); plt.close(fig)


def fig_box(R, algos, out):
    fig, ax = plt.subplots(figsize=(1.6 + 1.3 * len(algos), 3.4))
    data = [R[R.algorithm == a]['hv_rescored'].dropna() for a in algos]
    bp = ax.boxplot(data, widths=0.5, patch_artist=True, medianprops=dict(color=INK, lw=1.5))
    for patch, a in zip(bp['boxes'], algos):
        patch.set_facecolor(COLORS.get(a, '#6250d6')); patch.set_alpha(0.85); patch.set_edgecolor('white')
    ax.set_xticks(range(1, len(algos) + 1), [NAMES.get(a, a) for a in algos])
    style(ax, 'Hypervolume of the re-scored front, all antibiotics and seeds', '', 'Hypervolume (higher is better)')
    fig.tight_layout(); fig.savefig(os.path.join(out, 'fig_hv_box.png'), dpi=160); plt.close(fig)


def ablation_table(R, proposed):
    var = [a for a in R['algorithm'].unique() if a.startswith(proposed + '-')]
    if not var:
        return pd.DataFrame()
    rows = []
    P = R[R.algorithm == proposed].set_index(['antibiotic', 'seed'])
    for v in var:
        Q = R[R.algorithm == v].set_index(['antibiotic', 'seed'])
        j = P.index.intersection(Q.index)
        row = dict(variant=v, removed=v.split('-', 1)[1], n_pairs=len(j))
        for m in ('hv_rescored', 'igd_plus', 'chosen_columns', 'stability_chosen', 'cv_AUPRC', 'test_AUPRC'):
            if m in R.columns:
                if m == 'stability_chosen':           # one value per antibiotic, not per seed
                    row[f'{m}_drop'] = (P[m].groupby('antibiotic').first() - Q[m].groupby('antibiotic').first()).mean()
                else:
                    row[f'{m}_drop'] = (P.loc[j, m] - Q.loc[j, m]).mean()
        rows.append(row)
    return pd.DataFrame(rows).sort_values('hv_rescored_drop', ascending=False)


def fig_ablation(A, out):
    if A.empty:
        return
    A = A.sort_values('hv_rescored_drop')
    fig, ax = plt.subplots(figsize=(6.4, 0.45 * len(A) + 1.2))
    ax.barh(A['removed'], A['hv_rescored_drop'], color='#2a78d6', height=0.6, edgecolor='white', lw=2)
    ax.axvline(0, color=INK2, lw=1)
    style(ax, 'Hypervolume lost when one component is removed', 'Full method minus variant (positive = component helps)', '')
    fig.tight_layout(); fig.savefig(os.path.join(out, 'fig_ablation.png'), dpi=160); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results', default='results/exp4', help='one or more folders, comma separated')
    ap.add_argument('--input', default='Var-2000')
    ap.add_argument('--out', default='results/exp4_summary')
    ap.add_argument('--proposed', default='emopso')
    ap.add_argument('--main', default='emopso,mopso,nsga2', help='algorithms in the main comparison')
    ap.add_argument('--training-only', action='store_true', help='never read a 2018 score')
    ap.add_argument('--antibiotics', default=None,
                    help="comma list to keep, e.g. the evaluation group only (default: all found)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    R, Fr, T = load(a.results.split(','), a.input)
    if a.antibiotics:
        keep = [x.strip() for x in a.antibiotics.split(',')]
        R, Fr = R[R.antibiotic.isin(keep)], Fr[Fr.antibiotic.isin(keep)]
        T = T[T.antibiotic.isin(keep)] if not T.empty else T
    if (R['sample_frac'] < 1).any():
        print('WARNING: some runs used --sample-frac (demo data). Do not report them in the paper.')
    R = add_igd(R, Fr)
    R = add_model_scores(R, T, a.training_only)
    metrics = metrics_present(R)
    main_algos = [x for x in a.main.split(',') if x in set(R['algorithm'])]
    Rm = R[R.algorithm.isin(main_algos)]

    per = Rm.groupby(['antibiotic', 'algorithm'])[metrics].agg(['mean', 'std']).reset_index()
    overall = Rm.groupby(['antibiotic', 'algorithm'])[metrics].mean().groupby('algorithm').mean()
    for m in metrics:
        W = Rm.groupby(['antibiotic', 'algorithm'])[m].mean().unstack()
        overall[f'rank_{m}'] = (-W if HIGHER[m] else W).rank(axis=1).mean()
    overall = overall.loc[main_algos]
    wil = wilcoxon_table(Rm, a.proposed, metrics)
    fri = friedman_table(per, main_algos, metrics)
    abl = ablation_table(R, a.proposed)

    flat = per.copy(); flat.columns = ['_'.join(c).rstrip('_') for c in flat.columns]
    flat.to_csv(os.path.join(a.out, 'per_antibiotic.csv'), index=False)
    overall.to_csv(os.path.join(a.out, 'overall.csv'))
    wil.to_csv(os.path.join(a.out, f'wilcoxon_vs_{a.proposed}.csv'), index=False)
    fri.to_csv(os.path.join(a.out, 'friedman.csv'), index=False)
    if not abl.empty:
        abl.to_csv(os.path.join(a.out, 'ablation.csv'), index=False)
    with pd.ExcelWriter(os.path.join(a.out, 'exp4_summary.xlsx')) as xw:
        overall.round(4).to_excel(xw, sheet_name='overall')
        flat.round(4).to_excel(xw, sheet_name='per_antibiotic', index=False)
        wil.round(4).to_excel(xw, sheet_name='wilcoxon', index=False)
        fri.round(4).to_excel(xw, sheet_name='friedman', index=False)
        if not abl.empty:
            abl.round(4).to_excel(xw, sheet_name='ablation', index=False)
        R.drop(columns=['hv_trace']).round(5).to_excel(xw, sheet_name='all_runs', index=False)

    fig_fronts(Fr, main_algos, a.out)
    fig_convergence(R, main_algos, a.out)
    fig_box(Rm, main_algos, a.out)
    fig_ablation(abl, a.out)

    show = [m for m in ('hv_rescored', 'igd_plus', 'chosen_columns', 'stability_chosen', 'cv_AUPRC',
                        'test_AUROC', 'test_AUPRC', 'search_sec') if m in overall.columns]
    with open(os.path.join(a.out, 'summary.md'), 'w') as fh:
        fh.write(f'# Experiment 4 summary ({a.input})\n\n')
        fh.write(f'Antibiotics: {", ".join(sorted(R.antibiotic.unique()))}  \n')
        fh.write(f'Seeds per algorithm: {int(Rm.groupby(["antibiotic", "algorithm"]).size().min())}  \n')
        if (R['sample_frac'] < 1).any():
            fh.write('\n**SAMPLE DATA (demo). Not valid for the paper.**\n')
        fh.write('\n## Mean over antibiotics\n\n' + overall[show].round(4).to_markdown() + '\n')
        fh.write('\n## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)\n\n')
        fh.write(wil.round(4).to_markdown(index=False) + '\n')
        if not abl.empty:
            fh.write('\n## Ablation (full method minus variant)\n\n' + abl.round(4).to_markdown(index=False) + '\n')
    print(overall[show].round(4).to_string())
    print(f'\nwritten to {a.out}')


if __name__ == '__main__':
    main()
