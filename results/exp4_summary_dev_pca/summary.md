# Experiment 4 summary (PCA-200)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ceftriaxone, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.4188 |     0.0108 |           25.1   |             0.7198 |     0.4305 |       54.645 |
| mopso       |        0.3224 |     0.1366 |           88.675 |             0.0557 |     0.4231 |      121.87  |
| nsga2       |        0.3902 |     0.0218 |           16.375 |             0.4927 |     0.4006 |       48.105 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        40 |        0.088  |     40 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        40 |        0.0281 |     40 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | mopso   |        40 |        0.093  |     40 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        40 |        0.0169 |     38 |      0 |        2 | 0      |   0      |
| igd_plus              | emopso     | mopso   |        40 |       -0.1104 |     40 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        40 |       -0.0099 |     40 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | mopso   |        40 |      -65      |     40 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        40 |        9      |      4 |      0 |       36 | 0      |   0      |
| chosen_auprc_rescored | emopso     | mopso   |        40 |        0.0502 |     40 |      0 |        0 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        40 |        0.0261 |     40 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | mopso   |        40 |        0.6357 |     40 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        40 |        0.213  |     40 |      0 |        0 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        40 |        0.011  |     28 |      0 |       12 | 0.0147 |   0.0147 |
| cv_AUPRC              | emopso     | nsga2   |        40 |        0.0337 |     37 |      0 |        3 | 0      |   0      |
| search_sec            | emopso     | mopso   |        40 |      -66.3    |     40 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        40 |        5.1    |      3 |      0 |       37 | 0      |   0      |
