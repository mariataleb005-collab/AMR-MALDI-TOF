"""Antibiotic-level Wilcoxon tests (one pair per antibiotic) from per_antibiotic.csv.
Use for stability_chosen (one value per antibiotic) and as the conservative check for the other metrics.
    python abx_level_tests.py results/exp4_summary_eval_raw
"""
import sys, os
import numpy as np, pandas as pd
from scipy.stats import wilcoxon

HIGHER = {'hv_rescored': True, 'igd_plus': False, 'chosen_columns': False, 'stability_chosen': True,
          'cv_AUPRC': True, 'search_sec': False}
folder, proposed, others = sys.argv[1], 'emopso', ['mopso', 'nsga2']
per = pd.read_csv(os.path.join(folder, 'per_antibiotic.csv'))
rows = []
for m, hi in HIGHER.items():
    col = f'{m}_mean'
    if col not in per: continue
    W = per.pivot(index='antibiotic', columns='algorithm', values=col)
    res = []
    for o in others:
        d = (W[proposed] - W[o]).dropna().to_numpy()
        s = d if hi else -d
        p = wilcoxon(d).pvalue if np.any(d != 0) else np.nan
        res.append(dict(metric=m, other=o, n_antibiotics=len(d), median_diff=np.median(d),
                        wins=int((s > 1e-12).sum()), losses=int((s < -1e-12).sum()), p=p))
    ps = sorted(range(len(res)), key=lambda i: res[i]['p'])     # Holm over the two comparisons
    run = 0
    for k, i in enumerate(ps):
        run = max(run, min(1, res[i]['p'] * (len(res) - k))); res[i]['p_holm'] = run
    rows += res
out = pd.DataFrame(rows)
out.to_csv(os.path.join(folder, 'wilcoxon_by_antibiotic.csv'), index=False)
print(out.round(4).to_string(index=False))
