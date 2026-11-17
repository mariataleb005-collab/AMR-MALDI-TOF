# Experiment 4 summary (PCA-200)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ceftriaxone, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.5506 |     0.0097 |          26.6231 |             0.7474 |     0.5603 |      55.6738 |
| mopso       |        0.443  |     0.1533 |          89.3385 |             0.0568 |     0.5489 |     132.439  |
| nsga2       |        0.5195 |     0.0213 |          17.1231 |             0.507  |     0.5309 |      48.1362 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |   p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|----:|---------:|
| hv_rescored           | emopso     | mopso   |       130 |        0.1058 |    130 |      0 |        0 |   0 |        0 |
| hv_rescored           | emopso     | nsga2   |       130 |        0.0287 |    130 |      0 |        0 |   0 |        0 |
| hv_search             | emopso     | mopso   |       130 |        0.1028 |    130 |      0 |        0 |   0 |        0 |
| hv_search             | emopso     | nsga2   |       130 |        0.0211 |    126 |      0 |        4 |   0 |        0 |
| igd_plus              | emopso     | mopso   |       130 |       -0.1389 |    130 |      0 |        0 |   0 |        0 |
| igd_plus              | emopso     | nsga2   |       130 |       -0.0098 |    129 |      0 |        1 |   0 |        0 |
| chosen_columns        | emopso     | mopso   |       130 |      -63.5    |    130 |      0 |        0 |   0 |        0 |
| chosen_columns        | emopso     | nsga2   |       130 |        9      |      9 |      2 |      119 |   0 |        0 |
| chosen_auprc_rescored | emopso     | mopso   |       130 |        0.0466 |    130 |      0 |        0 |   0 |        0 |
| chosen_auprc_rescored | emopso     | nsga2   |       130 |        0.0258 |    130 |      0 |        0 |   0 |        0 |
| stability_chosen      | emopso     | mopso   |       130 |        0.7    |    130 |      0 |        0 |   0 |        0 |
| stability_chosen      | emopso     | nsga2   |       130 |        0.2148 |    130 |      0 |        0 |   0 |        0 |
| cv_AUPRC              | emopso     | mopso   |       130 |        0.0104 |     99 |      0 |       31 |   0 |        0 |
| cv_AUPRC              | emopso     | nsga2   |       130 |        0.0299 |    122 |      0 |        8 |   0 |        0 |
| search_sec            | emopso     | mopso   |       130 |      -57.45   |    130 |      0 |        0 |   0 |        0 |
| search_sec            | emopso     | nsga2   |       130 |        5.1    |     22 |      0 |      108 |   0 |        0 |
