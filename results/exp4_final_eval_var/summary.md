# Experiment 4 summary (Var-2000)

Antibiotics: Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   test_AUROC |   test_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|-------------:|-------------:|
| emopso      |        0.6215 |     0.011  |          154.3   |             0.3196 |     0.6422 |       0.7427 |       0.5774 |       428.71 |
| mopso       |        0.5571 |     0.0965 |          836.367 |             0.0288 |     0.6563 |       0.751  |       0.5888 |      1847.92 |
| nsga2       |        0.6238 |     0.0104 |          134.667 |             0.2517 |     0.6409 |       0.7383 |       0.5678 |       223.38 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        90 |        0.0673 |     90 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        90 |       -0.0037 |     36 |      0 |       54 | 0.0392 |   0.0392 |
| hv_search             | emopso     | mopso   |        90 |        0.0693 |     90 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        90 |       -0.0083 |     22 |      0 |       68 | 0      |   0      |
| igd_plus              | emopso     | mopso   |        90 |       -0.0819 |     90 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        90 |        0.0007 |     37 |      0 |       53 | 0.236  |   0.236  |
| chosen_columns        | emopso     | mopso   |        90 |     -682      |     90 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        90 |        8      |     38 |      1 |       51 | 0.0899 |   0.0899 |
| chosen_auprc_rescored | emopso     | mopso   |        90 |        0.0156 |     82 |      0 |        8 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        90 |       -0.0042 |     26 |      0 |       64 | 0.0001 |   0.0001 |
| stability_chosen      | emopso     | mopso   |        90 |        0.2469 |     90 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        90 |        0.0743 |     80 |      0 |       10 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        90 |       -0.0114 |     14 |      0 |       76 | 0      |   0      |
| cv_AUPRC              | emopso     | nsga2   |        90 |        0.0025 |     51 |      0 |       39 | 0.441  |   0.441  |
| test_AUROC            | emopso     | mopso   |        90 |       -0.0081 |     28 |      0 |       62 | 0.0001 |   0.0001 |
| test_AUROC            | emopso     | nsga2   |        90 |        0.0044 |     55 |      0 |       35 | 0.0236 |   0.0236 |
| test_AUPRC            | emopso     | mopso   |        90 |       -0.0123 |     27 |      0 |       63 | 0      |   0      |
| test_AUPRC            | emopso     | nsga2   |        90 |        0.0074 |     64 |      0 |       26 | 0.0001 |   0.0001 |
| test_MCC              | emopso     | mopso   |        90 |       -0.0111 |     36 |      0 |       54 | 0.008  |   0.0159 |
| test_MCC              | emopso     | nsga2   |        90 |        0.0043 |     50 |      0 |       40 | 0.1608 |   0.1608 |
| test_VME              | emopso     | mopso   |        90 |        0      |     43 |      3 |       44 | 0.6607 |   0.6607 |
| test_VME              | emopso     | nsga2   |        90 |       -0.016  |     61 |      0 |       29 | 0.0083 |   0.0165 |
| test_ME               | emopso     | mopso   |        90 |        0.0108 |     37 |      0 |       53 | 0.2251 |   0.3439 |
| test_ME               | emopso     | nsga2   |        90 |        0.007  |     38 |      0 |       52 | 0.1719 |   0.3439 |
| search_sec            | emopso     | mopso   |        90 |    -1300.45   |     90 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        90 |      115.15   |      1 |      0 |       89 | 0      |   0      |
