# Experiment 4 summary (Raw-6000)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ceftriaxone, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.4435 |     0.0124 |              165 |             0.3383 |     0.4689 |      1555.06 |
| mopso       |        0.3502 |     0.1436 |             2563 |             0.0096 |     0.4667 |     12002.2  |
| nsga2       |        0.4391 |     0.0184 |              184 |             0.1957 |     0.4599 |      1173.56 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        40 |        0.0963 |     40 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        40 |        0.0052 |     26 |      0 |       14 | 0.0548 |   0.0548 |
| hv_search             | emopso     | mopso   |        40 |        0.1055 |     40 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        40 |       -0.0038 |     16 |      0 |       24 | 0.0381 |   0.0381 |
| igd_plus              | emopso     | mopso   |        40 |       -0.1314 |     40 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        40 |       -0.0035 |     27 |      0 |       13 | 0.0094 |   0.0094 |
| chosen_columns        | emopso     | mopso   |        40 |    -2455      |     40 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        40 |      -15      |     23 |      3 |       14 | 0.1537 |   0.1537 |
| chosen_auprc_rescored | emopso     | mopso   |        40 |        0.0512 |     40 |      0 |        0 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        40 |       -0.0006 |     20 |      0 |       20 | 0.536  |   0.536  |
| stability_chosen      | emopso     | mopso   |        40 |        0.3697 |     40 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        40 |        0.1507 |     40 |      0 |        0 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        40 |       -0      |     20 |      0 |       20 | 0.4845 |   0.4845 |
| cv_AUPRC              | emopso     | nsga2   |        40 |        0.0057 |     22 |      0 |       18 | 0.0531 |   0.1062 |
| search_sec            | emopso     | mopso   |        40 |   -10856.9    |     40 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        40 |      233.65   |     13 |      0 |       27 | 0.0332 |   0.0332 |
