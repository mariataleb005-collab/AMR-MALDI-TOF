"""Step 0 - choose the antibiotics that can be modelled, from the original shortlist.

Input : the original DRIAMS shortlist file(s) (e.g. DRIAMS_A_SHORT_LIST.xlsx, .xlsx or .csv),
        one row per isolate with 'code', 'species', 'year' and one column per antibiotic
        holding the raw S / I / R results
        + labels_ecoli_A.csv (optional but recommended): only isolates that have a spectrum
          in spectra_ecoli_A.npy are counted, so the counts match what the models see
Output: <out_dir>/antibiotic_selection.csv   counts, checks and decision for every antibiotic
        <out_dir>/selected_antibiotics.txt   the kept antibiotics, one per line

Only E. coli rows are used. Every column that is not metadata is treated as an antibiotic.
Labels follow the project rule: S = 0, I or R = 1; anything else is missing
(same parsing as step 1, so a cell with two results such as 'R(1), S(1)' is missing).
Split: train = years before 2018, test = 2018.

An antibiotic is kept only if all checks pass:
  1. tested      : it has S, I or R results
  2. two labels  : the results are not all one label (S, I and R each count)
  3. two classes : with S = 0, I or R = 1, both classes exist in train and in test
  4. enough      : the smaller class has at least MIN_MINORITY isolates in train and in test

Usage : python step0_select_antibiotics.py <out_dir> <shortlist> [<shortlist> ...] [--spectra-labels labels_ecoli_A.csv]
Example: python step0_select_antibiotics.py data/ DRIAMS_A_SHORT_LIST.xlsx --spectra-labels labels_ecoli_A.csv
"""
import os, re, sys
import pandas as pd

MIN_MINORITY = 30
TEST_YEAR = 2018
SPECIES = 'Escherichia coli'
META = {'code', 'species', 'laboratory_species', 'genus', 'sample_type', 'year', 'hospital',
        'ESBL', 'MRSA', 'Quinolones', 'Aminoglycosides', 'combined_code'}


def sir(v):
    if pd.isna(v) or ',' in str(v):      # missing, or two results in one cell -> missing
        return None
    m = re.match(r'\s*([SIR])\b', str(v).upper())
    return m.group(1) if m else None


def read_table(path):
    if path.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(path)
    return pd.read_csv(path, low_memory=False)


def main():
    args = sys.argv[1:]
    spectra_csv = None
    if '--spectra-labels' in args:
        i = args.index('--spectra-labels')
        spectra_csv = args[i + 1]
        del args[i:i + 2]
    out_dir, files = args[0], args[1:]
    os.makedirs(out_dir, exist_ok=True)

    raw = pd.concat([read_table(f) for f in files], ignore_index=True)
    raw = raw.loc[:, ~raw.columns.astype(str).str.startswith('Unnamed')]
    if 'Cotrimoxazol' in raw.columns:      # same antibiotic stored under two names
        if 'Cotrimoxazole' in raw.columns:
            raw['Cotrimoxazole'] = raw['Cotrimoxazole'].combine_first(raw['Cotrimoxazol'])
            raw = raw.drop(columns='Cotrimoxazol')
        else:
            raw = raw.rename(columns={'Cotrimoxazol': 'Cotrimoxazole'})
    print(f'shortlist rows: {len(raw)}')

    raw = raw[raw['species'].astype(str).str.contains(SPECIES, case=False)]
    raw = raw.drop_duplicates('code')
    print(f'E. coli rows (unique code): {len(raw)}')

    if spectra_csv:
        spec = pd.read_csv(spectra_csv)
        raw = raw[raw['code'].isin(spec['code'])]
        if 'year' not in raw.columns or raw['year'].isna().all():
            raw = raw.drop(columns='year', errors='ignore').merge(
                spec[['code', 'year']].drop_duplicates('code'), on='code', how='left')
        print(f'E. coli rows with a spectrum: {len(raw)} (spectra file has {len(spec)} rows)')

    abx = [c for c in raw.columns if c not in META]
    test = (raw['year'] == TEST_YEAR).values
    train = (raw['year'] < TEST_YEAR).values
    print(f'train isolates: {train.sum()}, test isolates: {test.sum()}, candidate antibiotics: {len(abx)}')

    rows, odd = [], {}
    for a in abx:
        s = raw[a].map(sir).values
        bad = sorted({str(v) for v, p in zip(raw[a].values, s) if p is None and pd.notna(v)})
        if bad:
            odd[a] = bad[:5]
        nS, nI, nR = (s == 'S').sum(), (s == 'I').sum(), (s == 'R').sum()
        n = nS + nI + nR
        n_labels = int(nS > 0) + int(nI > 0) + int(nR > 0)
        pos = (s == 'I') | (s == 'R')
        neg = s == 'S'
        tr_pos, tr_neg = int((pos & train).sum()), int((neg & train).sum())
        te_pos, te_neg = int((pos & test).sum()), int((neg & test).sum())

        if n == 0:
            decision = 'drop: not tested'
        elif n_labels < 2:
            decision = 'drop: single label only'
        elif min(tr_pos, tr_neg, te_pos, te_neg) == 0:
            decision = 'drop: one class in train or test'
        elif min(tr_pos, tr_neg) < MIN_MINORITY or min(te_pos, te_neg) < MIN_MINORITY:
            decision = f'drop: minority class < {MIN_MINORITY}'
        else:
            decision = 'keep'

        rows.append({'antibiotic': a, 'S': int(nS), 'I': int(nI), 'R': int(nR), 'n_labelled': int(n),
                     'labels_present': n_labels,
                     'positive_rate_%': round(100 * (nI + nR) / n, 1) if n else None,
                     'train_pos': tr_pos, 'train_neg': tr_neg, 'test_pos': te_pos, 'test_neg': te_neg,
                     'decision': decision})

    if odd:
        print('\nvalues that are not S / I / R and were set to missing (first 5 per column):')
        for a, v in odd.items():
            print(f'  {a}: {v}')

    out = pd.DataFrame(rows)
    out['_keep'] = out['decision'] != 'keep'
    out = out.sort_values(['_keep', 'n_labelled'], ascending=[True, False]).drop(columns='_keep')
    out.to_csv(f'{out_dir}/antibiotic_selection.csv', index=False)
    kept = out.loc[out.decision == 'keep', 'antibiotic'].tolist()
    with open(f'{out_dir}/selected_antibiotics.txt', 'w') as f:
        f.write('\n'.join(kept) + '\n')

    print('\n' + out.to_string(index=False))
    print('\ndecisions:')
    print(out['decision'].value_counts().to_string())
    print(f'\nkept {len(kept)} of {len(out)}: {kept}')


if __name__ == '__main__':
    main()
