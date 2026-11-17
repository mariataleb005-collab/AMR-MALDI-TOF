# Experiment 4 summary (Var-2000)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ceftriaxone, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.5631 |     0.0117 |          155.923 |             0.3203 |     0.5844 |      628.845 |
| mopso       |        0.5014 |     0.0942 |          835.854 |             0.0275 |     0.597  |     2616.22  |
| nsga2       |        0.5669 |     0.0107 |          132.585 |             0.2504 |     0.5817 |      274.642 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |       130 |        0.0609 |    130 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |       130 |       -0.0036 |     49 |      0 |       81 | 0.0014 |   0.0014 |
| hv_search             | emopso     | mopso   |       130 |        0.0681 |    130 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |       130 |       -0.0092 |     27 |      0 |      103 | 0      |   0      |
| igd_plus              | emopso     | mopso   |       130 |       -0.0797 |    130 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |       130 |        0.0007 |     52 |      0 |       78 | 0.0508 |   0.0508 |
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
