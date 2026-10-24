# Cycle 2 — règle Order Block de l'utilisateur (OB qui crée le FVG immédiatement)

- Généré le 2026-10-24 15:35 UTC, code `24ed8bf`
- Données : Dukascopy XAUUSD M1 Bid/Ask, 2018-01-01 → 2026-09-30 (3,100,386 minutes)
- Coûts de base : {"contract_size": 100.0, "commission_per_lot_rt": 7.0, "stop_slippage": 0.1, "partial_slippage": 0.05, "swap_long_per_lot": -40.0, "swap_short_per_lot": -15.0, "triple_swap_weekday": 2, "extra_spread": 0.0}
- Périodes : {"WARMUP": ["2018-01-01", "2019-01-01"], "DEV": ["2019-01-01", "2023-01-01"], "VAL": ["2023-01-01", "2024-07-01"], "TEST": ["2024-07-01", "2026-10-01"]}
- Configuration : baseline du cycle 1 + `ObMaxDistBars = 0` (seul changement)
- Exécuté **une seule fois** ; données déjà vues au cycle 1 ⇒ pas une validation indépendante
- Variantes cumulées évaluées : 75

> Résultats de simulation sur données historiques d'un fournisseur qui n'est pas le broker final. Ils ne constituent ni une preuve ni une promesse de rentabilité future.

## Résultat principal (runner C 5R, coûts de base)

| période   |   trades |   trades/mois |   taux réussite |   espérance R |   IC95 bas |   IC95 haut |    PF |   R total |   R/mois |   espérance stress |   DD max % |   net 10k$ | cycle 1 (n, E, PF)   |
|:----------|---------:|--------------:|----------------:|--------------:|-----------:|------------:|------:|----------:|---------:|-------------------:|-----------:|-----------:|:---------------------|
| DEV       |       34 |         0.708 |           0.265 |         0.318 |     -0.307 |       1.005 | 1.548 |    10.812 |    0.225 |              0.054 |      5.400 |   1017.950 | 84, -0.090, 0.87     |
| VAL       |       16 |         0.889 |           0.062 |        -0.717 |     -1.107 |      -0.017 | 0.256 |   -11.474 |   -0.637 |             -0.743 |     10.449 |  -1044.910 | 43, -0.343, 0.58     |
| TEST      |       22 |         0.815 |           0.227 |         0.004 |     -0.455 |       0.549 | 1.009 |     0.089 |    0.003 |             -0.193 |      5.332 |     -2.536 | 59, -0.089, 0.82     |

## Entonnoir (DEV)

|   setups_evaluated |   rejected_at_confirmation |   missed_before_placement |   orders_placed |   missed_at_placement |   cancelled_unfilled |   filled |   fill_rate |   invalidated_share_of_placed |
|-------------------:|---------------------------:|--------------------------:|----------------:|----------------------:|---------------------:|---------:|------------:|------------------------------:|
|               2769 |                       2713 |                         2 |              54 |                     0 |                   20 |       34 |       0.630 |                         0.370 |

| status      | reason                          |    n |
|:------------|:--------------------------------|-----:|
| REJECTED    | REJECT_NO_OB                    | 1216 |
| REJECTED    | REJECT_NO_FVG                   |  730 |
| REJECTED    | REJECT_CAUTION_SWEEP            |  301 |
| REJECTED    | REJECT_NO_OB_OTE_OVERLAP        |  248 |
| REJECTED    | REJECT_FVG_INVALIDATED          |   60 |
| REJECTED    | REJECT_SL_TOO_TIGHT             |   56 |
| INVALIDATED |                                 |   54 |
| REJECTED    | REJECT_RSI                      |   41 |
| REJECTED    | REJECT_OB_FULLY_MITIGATED       |   36 |
| REJECTED    | REJECT_OB_INVALIDATED           |   22 |
| REJECTED    | REJECT_ZONE_TOO_NARROW          |    3 |
| MISSED      | MISSED_TOUCHED_BEFORE_PLACEMENT |    2 |

## Tous les runners (information)

| period   | variant     |   trades |   win_rate |   expectancy_r |   ci95_low |   ci95_high |   t_stat |   profit_factor_r |   total_r |   max_dd_r |
|:---------|:------------|---------:|-----------:|---------------:|-----------:|------------:|---------:|------------------:|----------:|-----------:|
| DEV      | A_STRUCTURE |       34 |      0.265 |          0.365 |     -0.311 |       1.129 |    0.957 |             1.628 |    12.398 |      7.939 |
| DEV      | B_LIQUIDITY |       34 |      0.265 |          0.287 |     -0.329 |       0.957 |    0.857 |             1.495 |     9.760 |      7.110 |
| DEV      | C_FIXED_5R  |       34 |      0.265 |          0.318 |     -0.307 |       1.005 |    0.928 |             1.548 |    10.812 |      5.639 |
| DEV      | C_FIXED_6R  |       34 |      0.265 |          0.332 |     -0.315 |       1.069 |    0.930 |             1.572 |    11.292 |      5.433 |
| DEV      | D_TRAILING  |       34 |      0.265 |          0.376 |     -0.309 |       1.143 |    0.971 |             1.648 |    12.798 |      8.600 |
| VAL      | A_STRUCTURE |       16 |      0.062 |         -0.750 |     -1.107 |      -0.115 |   -2.617 |             0.223 |   -11.993 |     11.993 |
| VAL      | B_LIQUIDITY |       16 |      0.062 |         -0.694 |     -1.107 |       0.052 |   -2.038 |             0.280 |   -11.106 |     11.106 |
| VAL      | C_FIXED_5R  |       16 |      0.062 |         -0.717 |     -1.107 |      -0.017 |   -2.255 |             0.256 |   -11.474 |     11.474 |
| VAL      | C_FIXED_6R  |       16 |      0.062 |         -0.686 |     -1.107 |       0.076 |   -1.967 |             0.289 |   -10.974 |     10.974 |
| VAL      | D_TRAILING  |       16 |      0.062 |         -0.745 |     -1.107 |      -0.101 |   -2.560 |             0.227 |   -11.918 |     11.918 |
| TEST     | A_STRUCTURE |       22 |      0.227 |          0.112 |     -0.452 |       0.845 |    0.320 |             1.261 |     2.465 |      5.667 |
| TEST     | B_LIQUIDITY |       22 |      0.227 |         -0.014 |     -0.457 |       0.499 |   -0.055 |             0.968 |    -0.306 |      5.667 |
| TEST     | C_FIXED_5R  |       22 |      0.227 |          0.004 |     -0.455 |       0.549 |    0.015 |             1.009 |     0.089 |      5.667 |
| TEST     | C_FIXED_6R  |       22 |      0.227 |          0.027 |     -0.455 |       0.611 |    0.094 |             1.062 |     0.589 |      5.667 |
| TEST     | D_TRAILING  |       22 |      0.227 |          0.041 |     -0.439 |       0.601 |    0.147 |             1.094 |     0.893 |      5.667 |

## Ventilations DEV

**Par year**

|   year |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|-------:|---------:|-----------:|---------------:|----------:|-------:|
|   2019 |        8 |      0.125 |         -0.289 |    -2.314 |  0.631 |
|   2020 |       10 |      0.200 |          0.075 |     0.748 |  1.160 |
|   2021 |        4 |      0.250 |         -0.482 |    -1.927 |  0.414 |
|   2022 |       12 |      0.417 |          1.192 |    14.306 |  3.603 |


**Par session**

| session        |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| ASIA           |       10 |      0.200 |          0.093 |     0.929 |  1.133 |
| LDN_NY_OVERLAP |       10 |      0.300 |          0.246 |     2.462 |  1.360 |
| LONDON         |       11 |      0.273 |          0.513 |     5.646 |  2.507 |
| NEW_YORK       |        3 |      0.333 |          0.592 |     1.775 |  1.815 |


**Par side**

| side   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------|---------:|-----------:|---------------:|----------:|-------:|
| BUY    |       18 |      0.167 |         -0.080 |    -1.434 |  0.866 |
| SELL   |       16 |      0.375 |          0.765 |    12.246 |  2.357 |


**Par vol_regime**

| vol_regime   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------------|---------:|-----------:|---------------:|----------:|-------:|
| LOW_VOL      |       12 |      0.167 |         -0.124 |    -1.488 |  0.842 |
| MID_VOL      |       11 |      0.364 |          0.858 |     9.437 |  3.431 |
| HIGH_VOL     |       11 |      0.273 |          0.260 |     2.863 |  1.445 |


**Par exit_reason**

| exit_reason   |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:--------------|---------:|-----------:|---------------:|----------:|--------:|
| BE            |       10 |      0.200 |          0.212 |     2.115 |   3.992 |
| SL            |       17 |      0.000 |         -1.119 |   -19.029 |   0.000 |
| TP            |        7 |      1.000 |          3.961 |    27.726 | inf     |


**Par s_entry_case**

| s_entry_case   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| A              |        2 |      0.000 |         -0.563 |    -1.125 |  0.000 |
| B              |       32 |      0.281 |          0.373 |    11.938 |  1.641 |


**Par mois** : 8 mois positifs / 23 ; meilleur 7.95R, pire -2.34R

**Coûts moyens** (R/trade) : commission -0.037, swap -0.011 ; spread moyen à l'exécution 0.351 $ ; 1R moyen 2.44 $ ; détention moyenne 3.8 h
## Ventilations VAL

**Par year**

|   year |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|-------:|---------:|-----------:|---------------:|----------:|-------:|
|   2023 |        9 |      0.111 |         -0.436 |    -3.927 |  0.502 |
|   2024 |        7 |      0.000 |         -1.078 |    -7.548 |  0.000 |


**Par session**

| session        |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| ASIA           |        6 |      0.000 |         -1.099 |    -6.591 |  0.000 |
| LATE           |        1 |      0.000 |         -1.081 |    -1.081 |  0.000 |
| LDN_NY_OVERLAP |        3 |      0.333 |          0.930 |     2.791 |  3.405 |
| LONDON         |        3 |      0.000 |         -1.074 |    -3.221 |  0.000 |
| NEW_YORK       |        3 |      0.000 |         -1.124 |    -3.372 |  0.000 |


**Par side**

| side   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------|---------:|-----------:|---------------:|----------:|-------:|
| BUY    |       12 |      0.000 |         -1.015 |   -12.183 |  0.000 |
| SELL   |        4 |      0.250 |          0.177 |     0.709 |  1.219 |


**Par vol_regime**

| vol_regime   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------------|---------:|-----------:|---------------:|----------:|-------:|
| LOW_VOL      |        6 |      0.167 |         -0.254 |    -1.522 |  0.722 |
| MID_VOL      |        5 |      0.000 |         -1.093 |    -5.463 |  0.000 |
| HIGH_VOL     |        5 |      0.000 |         -0.898 |    -4.490 |  0.000 |


**Par exit_reason**

| exit_reason   |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:--------------|---------:|-----------:|---------------:|----------:|--------:|
| BE            |        1 |      0.000 |         -0.068 |    -0.068 |   0.000 |
| SL            |       14 |      0.000 |         -1.097 |   -15.358 |   0.000 |
| TP            |        1 |      1.000 |          3.952 |     3.952 | inf     |


**Par s_entry_case**

| s_entry_case   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| A              |        1 |      0.000 |         -1.101 |    -1.101 |  0.000 |
| B              |       15 |      0.067 |         -0.692 |   -10.373 |  0.276 |


**Par mois** : 1 mois positifs / 10 ; meilleur 3.95R, pire -2.24R

**Coûts moyens** (R/trade) : commission -0.034, swap -0.012 ; spread moyen à l'exécution 0.355 $ ; 1R moyen 2.25 $ ; détention moyenne 0.9 h
## Ventilations TEST

**Par year**

|   year |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|-------:|---------:|-----------:|---------------:|----------:|-------:|
|   2024 |       10 |      0.000 |         -0.567 |    -5.667 |  0.000 |
|   2025 |        9 |      0.333 |          0.130 |     1.168 |  1.360 |
|   2026 |        3 |      0.667 |          1.529 |     4.587 |  9.407 |


**Par session**

| session        |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|--------:|
| ASIA           |        6 |      0.167 |         -0.308 |    -1.847 |   0.445 |
| LATE           |        2 |      0.000 |         -0.283 |    -0.566 |   0.000 |
| LDN_NY_OVERLAP |        5 |      0.400 |          0.159 |     0.793 |   1.372 |
| LONDON         |        6 |      0.000 |         -0.564 |    -3.387 |   0.000 |
| NEW_YORK       |        3 |      0.667 |          1.699 |     5.096 | 137.689 |


**Par side**

| side   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------|---------:|-----------:|---------------:|----------:|-------:|
| BUY    |       13 |      0.154 |         -0.314 |    -4.077 |  0.392 |
| SELL   |        9 |      0.333 |          0.463 |     4.166 |  2.514 |


**Par vol_regime**

| vol_regime   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------------|---------:|-----------:|---------------:|----------:|-------:|
| LOW_VOL      |        8 |      0.125 |         -0.510 |    -4.082 |  0.263 |
| MID_VOL      |        7 |      0.143 |         -0.239 |    -1.672 |  0.408 |
| HIGH_VOL     |        7 |      0.429 |          0.835 |     5.843 |  6.329 |


**Par exit_reason**

| exit_reason    |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|--------:|
| BE             |       12 |      0.333 |          0.426 |     5.116 |  12.468 |
| GAP_THROUGH_SL |        1 |      0.000 |         -0.546 |    -0.546 |   0.000 |
| SL             |        8 |      0.000 |         -1.058 |    -8.463 |   0.000 |
| TP             |        1 |      1.000 |          3.982 |     3.982 | inf     |


**Par s_entry_case**

| s_entry_case   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| B              |       22 |      0.227 |          0.004 |     0.089 |  1.009 |


**Par mois** : 5 mois positifs / 14 ; meilleur 3.98R, pire -2.18R

**Coûts moyens** (R/trade) : commission -0.021, swap -0.015 ; spread moyen à l'exécution 0.681 $ ; 1R moyen 4.73 $ ; détention moyenne 1.7 h
