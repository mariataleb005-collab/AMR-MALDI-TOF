# Experiment 4 summary (Var-2000)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ceftriaxone, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.4318 |     0.0099 |          159.575 |             0.322  |     0.4543 |     1079.15  |
| mopso       |        0.3759 |     0.0806 |          834.7   |             0.0246 |     0.4637 |     4344.9   |
| nsga2       |        0.4388 |     0.0109 |          127.9   |             0.2474 |     0.4484 |      389.983 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        40 |        0.055  |     40 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        40 |       -0.0036 |     13 |      0 |       27 | 0.0086 |   0.0086 |
| hv_search             | emopso     | mopso   |        40 |        0.0633 |     40 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        40 |       -0.0128 |      5 |      0 |       35 | 0      |   0      |
| igd_plus              | emopso     | mopso   |        40 |       -0.072  |     40 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        40 |       -0.0003 |     22 |      0 |       18 | 0.3138 |   0.3138 |
| chosen_columns        | emopso     | mopso   |        40 |     -704      |     40 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        40 |       21      |     14 |      2 |       24 | 0.026  |   0.026  |
| chosen_auprc_rescored | emopso     | mopso   |        40 |        0.0196 |     33 |      0 |        7 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        40 |       -0.0086 |     13 |      0 |       27 | 0.0044 |   0.0044 |
| stability_chosen      | emopso     | mopso   |        40 |        0.2982 |     40 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        40 |        0.0658 |     40 |      0 |        0 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        40 |       -0.0091 |     15 |      0 |       25 | 0.031  |   0.0619 |
| cv_AUPRC              | emopso     | nsga2   |        40 |        0.0014 |     22 |      0 |       18 | 0.3472 |   0.3472 |
| search_sec            | emopso     | mopso   |        40 |    -3393.25   |     40 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        40 |      571.95   |      0 |      0 |       40 | 0      |   0      |

## Ablation (full method minus variant)

| variant         | removed   |   n_pairs |   hv_rescored_drop |   igd_plus_drop |   chosen_columns_drop |   stability_chosen_drop |   cv_AUPRC_drop |
|:----------------|:----------|----------:|-------------------:|----------------:|----------------------:|------------------------:|----------------:|
| emopso-vshape   | vshape    |        40 |             0.0107 |         -0.0087 |              -224.95  |                  0.0907 |         -0.0089 |
| emopso-local    | local     |        40 |             0.0055 |         -0.0133 |               -34.6   |                  0.098  |         -0.0012 |
| emopso-init     | init      |        40 |             0.0052 |         -0.0101 |              -105.2   |                  0.1469 |         -0.0082 |
| emopso-leader   | leader    |        40 |             0.0016 |          0.0006 |                27.275 |                 -0.0278 |          0.0038 |
| emopso-restart  | restart   |        40 |             0.0013 |         -0.0018 |               -10.2   |                  0.0172 |         -0.0002 |
| emopso-inertia  | inertia   |        40 |            -0.0007 |          0.0023 |                60.475 |                 -0.0516 |          0.0128 |
| emopso-mutation | mutation  |        40 |            -0.0017 |         -0.002  |               -53.6   |                  0.0769 |         -0.0055 |
