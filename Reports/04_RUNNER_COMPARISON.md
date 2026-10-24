# Comparaison des méthodes de sortie du runner (mêmes signaux, DEV)

- Généré le 2026-10-24 11:25 UTC, code `d14a658`
- Données : Dukascopy XAUUSD M1 Bid/Ask, 2018-01-01 → 2023-12-29 (2,124,715 minutes)
- Coûts de base : {"contract_size": 100.0, "commission_per_lot_rt": 7.0, "stop_slippage": 0.1, "partial_slippage": 0.05, "swap_long_per_lot": -40.0, "swap_short_per_lot": -15.0, "triple_swap_weekday": 2, "extra_spread": 0.0}
- Périodes : {"WARMUP": ["2018-01-01", "2019-01-01"], "DEV": ["2019-01-01", "2023-01-01"], "VAL": ["2023-01-01", "2024-07-01"], "TEST": ["2024-07-01", "2026-10-01"]}

> Résultats de simulation sur données historiques d'un fournisseur qui n'est pas le broker final. Ils ne constituent ni une preuve ni une promesse de rentabilité future.

Toutes les méthodes utilisent **exactement les mêmes setups exécutés** (signaux baseline), les mêmes coûts et la même période. Seule la gestion des 50 % restants après la prise partielle à +3R diffère.

| experiment   | config   | variant     |   trades |   placed |   fill_rate |   win_rate |   expectancy_r |   ci95_low |   ci95_high |   t_stat |   profit_factor_r |   total_r |   max_dd_r |   avg_cost_r |
|:-------------|:---------|:------------|---------:|---------:|------------:|-----------:|---------------:|-----------:|------------:|---------:|------------------:|----------:|-----------:|-------------:|
| E1/E2        | BASE     | A_STRUCTURE |       84 |      162 |       0.519 |      0.155 |         -0.152 |     -0.481 |       0.215 |   -0.827 |             0.772 |   -12.808 |     23.512 |       -0.054 |
| E1/E2        | BASE     | B_LIQUIDITY |       84 |      162 |       0.519 |      0.155 |         -0.126 |     -0.464 |       0.245 |   -0.686 |             0.812 |   -10.551 |     18.410 |       -0.045 |
| E1/E2        | BASE     | C_FIXED_5R  |       84 |      162 |       0.519 |      0.155 |         -0.090 |     -0.433 |       0.292 |   -0.476 |             0.866 |    -7.532 |     14.566 |       -0.045 |
| E1/E2        | BASE     | C_FIXED_6R  |       84 |      162 |       0.519 |      0.155 |         -0.129 |     -0.473 |       0.252 |   -0.691 |             0.807 |   -10.843 |     16.933 |       -0.048 |
| E1/E2        | BASE     | D_TRAILING  |       84 |      162 |       0.519 |      0.155 |         -0.131 |     -0.473 |       0.249 |   -0.693 |             0.803 |   -11.035 |     22.767 |       -0.048 |


**Différences appariées (bootstrap, mêmes trades)**

|   n |   mean_diff_r |   ci_low |   ci_high |   p_le_0 | comparison               |
|----:|--------------:|---------:|----------:|---------:|:-------------------------|
|  84 |        -0.063 |   -0.195 |     0.064 |    0.833 | A_STRUCTURE - C_FIXED_5R |
|  84 |        -0.036 |   -0.118 |     0.034 |    0.815 | B_LIQUIDITY - C_FIXED_5R |
|  84 |        -0.039 |   -0.159 |     0.060 |    0.748 | C_FIXED_6R - C_FIXED_5R  |
|  84 |        -0.042 |   -0.170 |     0.091 |    0.737 | D_TRAILING - C_FIXED_5R  |


**Stabilité par année**

_A_STRUCTURE_

|   year |   trades |   expectancy_r |   total_r |   win_rate |   pf_r |
|-------:|---------:|---------------:|----------:|-----------:|-------:|
|   2019 |       23 |         -0.247 |    -5.690 |      0.130 |  0.642 |
|   2020 |       24 |         -0.163 |    -3.915 |      0.167 |  0.732 |
|   2021 |       18 |         -0.650 |   -11.697 |      0.111 |  0.190 |
|   2022 |       19 |          0.447 |     8.495 |      0.211 |  1.762 |

_B_LIQUIDITY_

|   year |   trades |   expectancy_r |   total_r |   win_rate |   pf_r |
|-------:|---------:|---------------:|----------:|-----------:|-------:|
|   2019 |       23 |         -0.217 |    -4.998 |      0.130 |  0.686 |
|   2020 |       24 |         -0.097 |    -2.320 |      0.167 |  0.842 |
|   2021 |       18 |         -0.435 |    -7.824 |      0.111 |  0.458 |
|   2022 |       19 |          0.242 |     4.591 |      0.211 |  1.412 |

_C_FIXED_5R_

|   year |   trades |   expectancy_r |   total_r |   win_rate |   pf_r |
|-------:|---------:|---------------:|----------:|-----------:|-------:|
|   2019 |       23 |         -0.184 |    -4.240 |      0.130 |  0.734 |
|   2020 |       24 |          0.050 |     1.190 |      0.167 |  1.081 |
|   2021 |       18 |         -0.509 |    -9.154 |      0.111 |  0.366 |
|   2022 |       19 |          0.246 |     4.671 |      0.211 |  1.419 |

_C_FIXED_6R_

|   year |   trades |   expectancy_r |   total_r |   win_rate |   pf_r |
|-------:|---------:|---------------:|----------:|-----------:|-------:|
|   2019 |       23 |         -0.261 |    -6.006 |      0.130 |  0.623 |
|   2020 |       24 |          0.007 |     0.165 |      0.167 |  1.011 |
|   2021 |       18 |         -0.481 |    -8.654 |      0.111 |  0.401 |
|   2022 |       19 |          0.192 |     3.651 |      0.211 |  1.327 |

_D_TRAILING_

|   year |   trades |   expectancy_r |   total_r |   win_rate |   pf_r |
|-------:|---------:|---------------:|----------:|-----------:|-------:|
|   2019 |       23 |         -0.272 |    -6.257 |      0.130 |  0.607 |
|   2020 |       24 |         -0.212 |    -5.086 |      0.167 |  0.653 |
|   2021 |       18 |         -0.512 |    -9.215 |      0.111 |  0.362 |
|   2022 |       19 |          0.501 |     9.522 |      0.211 |  1.854 |


**Sensibilité aux coûts**

| costs     | variant     |   trades |   expectancy_r |   profit_factor_r |   total_r |
|:----------|:------------|---------:|---------------:|------------------:|----------:|
| zéro coût | A_STRUCTURE |       84 |         -0.045 |             0.923 |    -3.759 |
| zéro coût | B_LIQUIDITY |       84 |         -0.030 |             0.949 |    -2.494 |
| zéro coût | C_FIXED_5R  |       84 |          0.006 |             1.010 |     0.500 |
| zéro coût | C_FIXED_6R  |       84 |         -0.030 |             0.949 |    -2.500 |
| zéro coût | D_TRAILING  |       84 |         -0.029 |             0.950 |    -2.427 |
| base      | A_STRUCTURE |       84 |         -0.152 |             0.772 |   -12.808 |
| base      | B_LIQUIDITY |       84 |         -0.126 |             0.812 |   -10.551 |
| base      | C_FIXED_5R  |       84 |         -0.090 |             0.866 |    -7.532 |
| base      | C_FIXED_6R  |       84 |         -0.129 |             0.807 |   -10.843 |
| base      | D_TRAILING  |       84 |         -0.131 |             0.803 |   -11.035 |
| stress    | A_STRUCTURE |       82 |         -0.407 |             0.523 |   -33.408 |
| stress    | B_LIQUIDITY |       82 |         -0.409 |             0.521 |   -33.521 |
| stress    | C_FIXED_5R  |       82 |         -0.366 |             0.571 |   -30.017 |
| stress    | C_FIXED_6R  |       82 |         -0.424 |             0.504 |   -34.738 |
| stress    | D_TRAILING  |       82 |         -0.401 |             0.530 |   -32.907 |


**Avertissement** : 70 variantes ont été évaluées au total ; les écarts entre méthodes doivent être lus à la lumière des intervalles de confiance ci-dessus. Le choix d'une méthode ne repose pas sur le profit total.
