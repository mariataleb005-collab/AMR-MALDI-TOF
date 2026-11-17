# Experiment 4 summary (Var-2000)

Antibiotics: Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.6215 |     0.0096 |          154.3   |             0.3196 |     0.6422 |       428.71 |
| mopso       |        0.5571 |     0.0911 |          836.367 |             0.0288 |     0.6563 |      1847.92 |
| nsga2       |        0.6238 |     0.0109 |          134.667 |             0.2517 |     0.6409 |       223.38 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |        90 |        0.0673 |     90 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |        90 |       -0.0037 |     36 |      0 |       54 | 0.0392 |   0.0392 |
| hv_search             | emopso     | mopso   |        90 |        0.0693 |     90 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |        90 |       -0.0083 |     22 |      0 |       68 | 0      |   0      |
| igd_plus              | emopso     | mopso   |        90 |       -0.0817 |     90 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |        90 |       -0.0002 |     50 |      0 |       40 | 0.0668 |   0.0668 |
| chosen_columns        | emopso     | mopso   |        90 |     -682      |     90 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |        90 |        8      |     38 |      1 |       51 | 0.0899 |   0.0899 |
| chosen_auprc_rescored | emopso     | mopso   |        90 |        0.0156 |     82 |      0 |        8 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |        90 |       -0.0042 |     26 |      0 |       64 | 0.0001 |   0.0001 |
| stability_chosen      | emopso     | mopso   |        90 |        0.2469 |     90 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |        90 |        0.0743 |     80 |      0 |       10 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |        90 |       -0.0114 |     14 |      0 |       76 | 0      |   0      |
| cv_AUPRC              | emopso     | nsga2   |        90 |        0.0025 |     51 |      0 |       39 | 0.441  |   0.441  |
| search_sec            | emopso     | mopso   |        90 |    -1300.45   |     90 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |        90 |      115.15   |      1 |      0 |       89 | 0      |   0      |

## Ablation (full method minus variant)

| variant         | removed   |   n_pairs |   hv_rescored_drop |   igd_plus_drop |   chosen_columns_drop |   stability_chosen_drop |   cv_AUPRC_drop |
|:----------------|:----------|----------:|-------------------:|----------------:|----------------------:|------------------------:|----------------:|
| emopso-vshape   | vshape    |        90 |             0.0089 |         -0.0066 |             -156.778  |                 -0.0143 |         -0.0056 |
| emopso-init     | init      |        90 |             0.0073 |         -0.0081 |              -89.0444 |                  0.1297 |         -0.0046 |
| emopso-local    | local     |        90 |             0.0045 |         -0.0094 |              -26.1    |                  0.0859 |         -0.0021 |
| emopso-restart  | restart   |        90 |             0.0016 |         -0.0008 |               -5.9889 |                  0.0071 |         -0.0024 |
| emopso-mutation | mutation  |        90 |             0.0002 |         -0.0016 |              -41.7222 |                  0.06   |         -0.0045 |
| emopso-leader   | leader    |        90 |            -0.0005 |         -0      |               -3.1556 |                  0.0051 |         -0.0035 |
| emopso-inertia  | inertia   |        90 |            -0.0011 |          0.003  |               54.9111 |                 -0.0793 |          0.0046 |
