"""Step 1 (Exp 0) - rebuild the E. coli DRIAMS-A labels with the literature definition.

Input : the DRIAMS-A id tables that still hold the raw AST results
        (DRIAMS-A/id/<year>/<year>_clean.csv, one per year, or any CSV with a 'code'
        column and the antibiotic columns as S / I / R strings)
        + the students' labels_ecoli_A.csv (gives the row order of spectra_ecoli_A.npy)
Output: labels_ecoli_A_corrected.csv  same layout as before, plus
          split        'train' (2015-2017) or 'test' (2018)
          fold_<abx>   0-4 stratified folds inside train, -1 for test or unlabelled rows
        labels_ecoli_A_noI.csv        sensitivity version: I set to missing (old rule)
        label_counts.csv              S / I / R counts per antibiotic and split, and the
                                      published counts to check against

Rule  : S = 0, I = 1, R = 1 (Weis et al. 2022, Nat Med; Aro-Sati et al. 2026, NCA).
        Anything else ('-', empty, 'neg', ...) = missing.

Usage : python step1_build_labels.py <old_labels_csv> <out_dir> <id_csv> [<id_csv> ...]
"""
import os, re, sys
import numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold

ALL_ABX = ['Ampicillin-Amoxicillin', 'Cotrimoxazole', 'Ciprofloxacin', 'Levofloxacin',
           'Amoxicillin-Clavulanic acid', 'Ceftriaxone', 'Cefpodoxime', 'Tobramycin', 'Ceftazidime',
           'Norfloxacin', 'Cefepime', 'Piperacillin-Tazobactam', 'Amikacin', 'Fosfomycin-Trometamol',
           'Ertapenem']
# resistant (I + R) counts over all years reported by Aro-Sati et al. (NCA 2026), E. coli, DRIAMS-A
PUBLISHED_POS = {'Ciprofloxacin': 1466, 'Ceftriaxone': 1086, 'Cefepime': 839,
                 'Piperacillin-Tazobactam': 350, 'Tobramycin': 636}


def sir(v):
    if pd.isna(v):
        return None
    if ',' in str(v):          # two results in one cell (e.g. 'R(1), S(1)') -> missing
        return None
    if chr(44) in str(v):
        return None
    m = re.match(r'\s*([SIR])\b', str(v).upper())
    return m.group(1) if m else None


def main():
    old_csv, out_dir = sys.argv[1:3]
    id_files = sys.argv[3:]
    os.makedirs(out_dir, exist_ok=True)
    old = pd.read_csv(old_csv)

    raw = pd.concat([pd.read_csv(f, low_memory=False) for f in id_files], ignore_index=True)
    if 'species' in raw.columns:
        raw = raw[raw['species'].astype(str).str.contains('Escherichia coli', case=False)]
    raw = raw.drop_duplicates('code')
    missing = [a for a in ALL_ABX if a not in raw.columns]
    if missing:
        print('WARNING antibiotic columns not found in the id files:', missing)
    abx = [a for a in ALL_ABX if a in raw.columns]
    letters = raw.set_index('code')[abx].map(sir)

    # keep the exact row order of spectra_ecoli_A.npy
    letters = letters.reindex(old['code'])
    print(f'spectra rows: {len(old)}, matched in id files: {letters.notna().any(axis=1).sum()}')

    new = old[['code', 'year']].copy()
    noI = old[['code', 'year']].copy()
    for a in abx:
        s = letters[a].values
        new[a] = pd.Series(s).map({'S': 0.0, 'I': 1.0, 'R': 1.0}).values
        noI[a] = pd.Series(s).map({'S': 0.0, 'R': 1.0}).values
    for df in (new, noI):
        df['split'] = np.where(df['year'] < 2018, 'train', 'test')
        for a in abx:
            fold = np.full(len(df), -1)
            tr = (df['split'] == 'train').values & df[a].notna().values
            y = df.loc[tr, a].values.astype(int)
            idx = np.flatnonzero(tr)
            for f, (_, va) in enumerate(StratifiedKFold(5, shuffle=True, random_state=0).split(idx, y)):
                fold[idx[va]] = f
            df[f'fold_{a}'] = fold
    new.to_csv(f'{out_dir}/labels_ecoli_A_corrected.csv', index=False)
    noI.to_csv(f'{out_dir}/labels_ecoli_A_noI.csv', index=False)

    rows = []
    for a in abx:
        for split in ('train', 'test', 'all'):
            m = np.ones(len(old), bool) if split == 'all' else (new['split'] == split).values
            s = letters[a].values[m]
            nS, nI, nR = (s == 'S').sum(), (s == 'I').sum(), (s == 'R').sum()
            rows.append({'antibiotic': a, 'split': split, 'S': nS, 'I': nI, 'R': nR,
                         'n_labelled': nS + nI + nR, 'positive_IR': nI + nR,
                         'positive_rate': (nI + nR) / max(nS + nI + nR, 1),
                         'old_positive_R_only': int(old.loc[m, a].sum()) if a in old else np.nan,
                         'published_positive': PUBLISHED_POS.get(a, np.nan) if split == 'all' else np.nan})
    counts = pd.DataFrame(rows)
    counts.to_csv(f'{out_dir}/label_counts.csv', index=False)
    print(counts[counts.split == 'all'].to_string(index=False))


if __name__ == '__main__':
    main()
