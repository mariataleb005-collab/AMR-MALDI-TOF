# Experiment 4 summary (Var-2000)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ceftriaxone, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.5631 |     0.0097 |          155.923 |             0.3203 |     0.5844 |      628.845 |
| mopso       |        0.5014 |     0.0878 |          835.854 |             0.0275 |     0.597  |     2616.22  |
| nsga2       |        0.5669 |     0.0109 |          132.585 |             0.2504 |     0.5817 |      274.642 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |       130 |        0.0609 |    130 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |       130 |       -0.0036 |     49 |      0 |       81 | 0.0014 |   0.0014 |
| hv_search             | emopso     | mopso   |       130 |        0.0681 |    130 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |       130 |       -0.0092 |     27 |      0 |      103 | 0      |   0      |
| igd_plus              | emopso     | mopso   |       130 |       -0.0761 |    130 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |       130 |       -0.0002 |     72 |      0 |       58 | 0.0362 |   0.0362 |
| chosen_columns        | emopso     | mopso   |       130 |     -691      |    130 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |       130 |        9      |     52 |      3 |       75 | 0.0065 |   0.0065 |
| chosen_auprc_rescored | emopso     | mopso   |       130 |        0.0165 |    115 |      0 |       15 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |       130 |       -0.0059 |     39 |      0 |       91 | 0      |   0      |
| stability_chosen      | emopso     | mopso   |       130 |        0.2474 |    130 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |       130 |        0.0743 |    120 |      0 |       10 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |       130 |       -0.011  |     29 |      0 |      101 | 0      |   0      |
| cv_AUPRC              | emopso     | nsga2   |       130 |        0.0018 |     73 |      0 |       57 | 0.2238 |   0.2238 |
| search_sec            | emopso     | mopso   |       130 |    -1524.4    |    130 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |       130 |      160.5    |      1 |      0 |      129 | 0      |   0      |

## Ablation (full method minus variant)

| variant         | removed   |   n_pairs |   hv_rescored_drop |   igd_plus_drop |   chosen_columns_drop |   stability_chosen_drop |   cv_AUPRC_drop |
|:----------------|:----------|----------:|-------------------:|----------------:|----------------------:|------------------------:|----------------:|
| emopso-vshape   | vshape    |       130 |             0.0094 |         -0.0072 |             -177.754  |                  0.018  |         -0.0066 |
| emopso-init     | init      |       130 |             0.0067 |         -0.0087 |              -94.0154 |                  0.135  |         -0.0057 |
| emopso-local    | local     |       130 |             0.0048 |         -0.0106 |              -28.7154 |                  0.0896 |         -0.0018 |
| emopso-restart  | restart   |       130 |             0.0015 |         -0.0011 |               -7.2846 |                  0.0102 |         -0.0017 |
| emopso-leader   | leader    |       130 |             0.0002 |          0.0001 |                6.2077 |                 -0.005  |         -0.0012 |
| emopso-mutation | mutation  |       130 |            -0.0004 |         -0.0017 |              -45.3769 |                  0.0652 |         -0.0048 |
| emopso-inertia  | inertia   |       130 |            -0.001  |          0.0028 |               56.6231 |                 -0.0708 |          0.0071 |
