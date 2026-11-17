# Experiment 4 summary (Raw-6000)

Antibiotics: Amikacin, Amoxicillin-Clavulanic acid, Ampicillin-Amoxicillin, Cefepime, Cefpodoxime, Ceftazidime, Ceftriaxone, Ciprofloxacin, Cotrimoxazole, Levofloxacin, Norfloxacin, Piperacillin-Tazobactam, Tobramycin  
Seeds per algorithm: 10  

## Mean over antibiotics

| algorithm   |   hv_rescored |   igd_plus |   chosen_columns |   stability_chosen |   cv_AUPRC |   search_sec |
|:------------|--------------:|-----------:|-----------------:|-------------------:|-----------:|-------------:|
| emopso      |        0.5665 |     0.0121 |          189.308 |             0.3541 |     0.5862 |      911.819 |
| mopso       |        0.4706 |     0.1415 |         2599.92  |             0.0101 |     0.584  |     7028.22  |
| nsga2       |        0.5586 |     0.0184 |          204.769 |             0.1685 |     0.5768 |      695.519 |

## Proposed against each algorithm (paired by antibiotic and seed, Wilcoxon, Holm)

| metric                | proposed   | other   |   n_pairs |   median_diff |   wins |   ties |   losses |      p |   p_holm |
|:----------------------|:-----------|:--------|----------:|--------------:|-------:|-------:|---------:|-------:|---------:|
| hv_rescored           | emopso     | mopso   |       130 |        0.099  |    130 |      0 |        0 | 0      |   0      |
| hv_rescored           | emopso     | nsga2   |       130 |        0.0067 |     91 |      0 |       39 | 0      |   0      |
| hv_search             | emopso     | mopso   |       130 |        0.104  |    130 |      0 |        0 | 0      |   0      |
| hv_search             | emopso     | nsga2   |       130 |       -0.0012 |     61 |      0 |       69 | 0.0581 |   0.0581 |
| igd_plus              | emopso     | mopso   |       130 |       -0.1296 |    130 |      0 |        0 | 0      |   0      |
| igd_plus              | emopso     | nsga2   |       130 |       -0.0035 |     88 |      0 |       42 | 0      |   0      |
| chosen_columns        | emopso     | mopso   |       130 |    -2450      |    130 |      0 |        0 | 0      |   0      |
| chosen_columns        | emopso     | nsga2   |       130 |      -30      |     75 |      6 |       49 | 0.0095 |   0.0095 |
| chosen_auprc_rescored | emopso     | mopso   |       130 |        0.0498 |    129 |      0 |        1 | 0      |   0      |
| chosen_auprc_rescored | emopso     | nsga2   |       130 |       -0.0017 |     61 |      0 |       69 | 0.1209 |   0.1209 |
| stability_chosen      | emopso     | mopso   |       130 |        0.381  |    130 |      0 |        0 | 0      |   0      |
| stability_chosen      | emopso     | nsga2   |       130 |        0.2008 |    130 |      0 |        0 | 0      |   0      |
| cv_AUPRC              | emopso     | mopso   |       130 |        0.0004 |     66 |      0 |       64 | 0.3171 |   0.3171 |
| cv_AUPRC              | emopso     | nsga2   |       130 |        0.0057 |     80 |      0 |       50 | 0.0001 |   0.0001 |
| search_sec            | emopso     | mopso   |       130 |    -4138.35   |    130 |      0 |        0 | 0      |   0      |
| search_sec            | emopso     | nsga2   |       130 |      122.3    |     43 |      0 |       87 | 0.0001 |   0.0001 |
