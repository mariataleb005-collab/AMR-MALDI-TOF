# Experiment 4 summary (PCA-200)

Antibiotics: Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   test_AUROC |   test_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|-------------:|-------------:|
| emopso      |        0.6092 |     0.0092 |          27.3    |             0.7597 |     0.618  |       0.6986 |       0.5018 |      56.1311 |
| mopso       |        0.4966 |     0.1608 |          89.6333 |             0.0572 |     0.6048 |       0.6999 |       0.4988 |     137.136  |
| nsga2       |        0.577  |     0.0211 |          17.4556 |             0.5134 |     0.5888 |       0.6814 |       0.4829 |      48.15   |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        90 |        0.1154 |     90 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        90 |        0.0301 |     90 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | mopso   |        90 |        0.1131 |     90 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        90 |        0.0223 |     88 |      0 |        2 | 0      |   0      |
| igd_plus              | emopso     | mopso   |        90 |       -0.1641 |     90 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        90 |       -0.0098 |     89 |      0 |        1 | 0      |   0      |
| chosen_columns        | emopso     | mopso   |        90 |      -62      |     90 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        90 |        9      |      5 |      2 |       83 | 0      |   0      |
| chosen_auprc_rescored | emopso     | mopso   |        90 |        0.0458 |     90 |      0 |        0 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        90 |        0.0252 |     90 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | mopso   |        90 |        0.7008 |     90 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        90 |        0.2496 |     90 |      0 |        0 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        90 |        0.0098 |     71 |      0 |       19 | 0      |   0      |
| cv_AUPRC              | emopso     | nsga2   |        90 |        0.0289 |     85 |      0 |        5 | 0      |   0      |
| test_AUROC            | emopso     | mopso   |        90 |        0.0004 |     46 |      0 |       44 | 0.6364 |   0.6364 |
| test_AUROC            | emopso     | nsga2   |        90 |        0.015  |     75 |      0 |       15 | 0      |   0      |
| test_AUPRC            | emopso     | mopso   |        90 |        0.0007 |     46 |      0 |       44 | 0.2441 |   0.2441 |
| test_AUPRC            | emopso     | nsga2   |        90 |        0.0167 |     73 |      0 |       17 | 0      |   0      |
| test_MCC              | emopso     | mopso   |        90 |        0.0038 |     49 |      0 |       41 | 0.1561 |   0.1561 |
| test_MCC              | emopso     | nsga2   |        90 |        0.015  |     64 |      0 |       26 | 0      |   0      |
| test_VME              | emopso     | mopso   |        90 |       -0.0013 |     46 |      0 |       44 | 0.9039 |   0.9039 |
| test_VME              | emopso     | nsga2   |        90 |       -0.05   |     65 |      0 |       25 | 0      |   0      |
| test_ME               | emopso     | mopso   |        90 |        0.0076 |     43 |      0 |       47 | 0.7384 |   0.7384 |
| test_ME               | emopso     | nsga2   |        90 |        0.0239 |     32 |      0 |       58 | 0.0341 |   0.0683 |
| search_sec            | emopso     | mopso   |        90 |      -55.15   |     90 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        90 |        5.35   |     19 |      0 |       71 | 0      |   0      |
