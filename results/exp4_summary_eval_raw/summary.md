# Experiment 4 summary (Raw-6000)

Antibiotics: Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.6212 |     0.0119 |          200.111 |             0.3611 |     0.6383 |      625.934 |
| mopso       |        0.5241 |     0.1406 |         2616.33  |             0.0103 |     0.6361 |     4817.58  |
| nsga2       |        0.6117 |     0.0184 |          214     |             0.1564 |     0.6287 |      483.056 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        90 |        0.0996 |     90 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        90 |        0.0077 |     65 |      0 |       25 | 0      |   0      |
| hv_search             | emopso     | mopso   |        90 |        0.101  |     90 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        90 |        0.0002 |     45 |      0 |       45 | 0.4106 |   0.4106 |
| igd_plus              | emopso     | mopso   |        90 |       -0.1296 |     90 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        90 |       -0.0034 |     61 |      0 |       29 | 0      |   0      |
| chosen_columns        | emopso     | mopso   |        90 |    -2445      |     90 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        90 |      -30      |     52 |      3 |       35 | 0.032  |   0.032  |
| chosen_auprc_rescored | emopso     | mopso   |        90 |        0.0495 |     89 |      0 |        1 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        90 |       -0.0029 |     41 |      0 |       49 | 0.1745 |   0.1745 |
| stability_chosen      | emopso     | mopso   |        90 |        0.381  |     90 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        90 |        0.2173 |     90 |      0 |        0 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        90 |        0.0009 |     46 |      0 |       44 | 0.4876 |   0.4876 |
| cv_AUPRC              | emopso     | nsga2   |        90 |        0.0057 |     58 |      0 |       32 | 0.0003 |   0.0007 |
| search_sec            | emopso     | mopso   |        90 |    -3655.95   |     90 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        90 |       96.55   |     30 |      0 |       60 | 0.001  |   0.001  |
