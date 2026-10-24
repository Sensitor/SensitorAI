# Rapport de backtest — période de développement (DEV 2019-2022)

- Généré le 2026-10-24 11:25 UTC, code `d14a658`
- Données : Dukascopy XAUUSD M1 Bid/Ask, 2018-01-01 → 2023-12-29 (2,124,715 minutes)
- Coûts de base : {"contract_size": 100.0, "commission_per_lot_rt": 7.0, "stop_slippage": 0.1, "partial_slippage": 0.05, "swap_long_per_lot": -40.0, "swap_short_per_lot": -15.0, "triple_swap_weekday": 2, "extra_spread": 0.0}
- Périodes : {"WARMUP": ["2018-01-01", "2019-01-01"], "DEV": ["2019-01-01", "2023-01-01"], "VAL": ["2023-01-01", "2024-07-01"], "TEST": ["2024-07-01", "2026-10-01"]}
- Variantes testées : **70** (14 configurations de signaux × 5 runners)

> Résultats de simulation sur données historiques d'un fournisseur qui n'est pas le broker final. Ils ne constituent ni une preuve ni une promesse de rentabilité future.

## 1. Entonnoir des signaux (baseline, DEV)

|   setups_evaluated |   rejected_at_confirmation |   missed_before_placement |   orders_placed |   missed_at_placement |   cancelled_unfilled |   filled |   fill_rate |   invalidated_share_of_placed |
|-------------------:|---------------------------:|--------------------------:|----------------:|----------------------:|---------------------:|---------:|------------:|------------------------------:|
|               2769 |                       2596 |                        11 |             162 |                     0 |                   78 |       84 |       0.519 |                         0.481 |


**Raisons de rejet / statut des setups (DEV)**

| status      | reason                          |   n |
|:------------|:--------------------------------|----:|
| REJECTED    | REJECT_CAUTION_SWEEP            | 866 |
| REJECTED    | REJECT_NO_FVG                   | 730 |
| REJECTED    | REJECT_NO_OB_OTE_OVERLAP        | 400 |
| REJECTED    | REJECT_FVG_INVALIDATED          | 202 |
| INVALIDATED |                                 | 162 |
| REJECTED    | REJECT_SL_TOO_TIGHT             | 121 |
| REJECTED    | REJECT_RSI                      | 115 |
| REJECTED    | REJECT_OB_FULLY_MITIGATED       |  84 |
| REJECTED    | REJECT_OB_INVALIDATED           |  50 |
| REJECTED    | REJECT_NO_OB                    |  21 |
| MISSED      | MISSED_TOUCHED_BEFORE_PLACEMENT |  11 |
| REJECTED    | REJECT_ZONE_TOO_NARROW          |   7 |


**Invalidations des setups valides (DEV)**

| end_reason       |   n |
|:-----------------|----:|
| INV_BIAS_CHANGED |   2 |
| INV_CONTINUATION |  97 |
| INV_DEEP_FAILURE |  59 |
| INV_SUPERSEDED   |   4 |


## 2. Baseline C_FIXED_5R — statistiques (DEV)

| experiment   | config   | variant    |   trades |   placed |   fill_rate |   win_rate |   expectancy_r |   ci95_low |   ci95_high |   t_stat |   profit_factor_r |   total_r |   max_dd_r |   avg_cost_r |
|:-------------|:---------|:-----------|---------:|---------:|------------:|-----------:|---------------:|-----------:|------------:|---------:|------------------:|----------:|-----------:|-------------:|
| E1/E2        | BASE     | C_FIXED_5R |       84 |      162 |       0.519 |      0.155 |         -0.090 |     -0.433 |       0.292 |   -0.476 |             0.866 |    -7.532 |     14.566 |       -0.045 |


**Simulation de compte (10 000 $, 1 %, limites de risque)**

```
{
  "trades": 84,
  "rejected_by_limits": 0,
  "net_profit": -789.3699999995105,
  "final_balance": 9210.63000000049,
  "profit_factor": 0.8418701458961447,
  "max_dd": 1357.6899999997277,
  "max_dd_pct": 13.566955421673022,
  "reject_reasons": {
    "PLACED": 162
  }
}
```

## 3. Ventilations (baseline, DEV)

**Par year**

|   year |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|-------:|---------:|-----------:|---------------:|----------:|-------:|
|   2019 |       23 |      0.130 |         -0.184 |    -4.240 |  0.734 |
|   2020 |       24 |      0.167 |          0.050 |     1.190 |  1.081 |
|   2021 |       18 |      0.111 |         -0.509 |    -9.154 |  0.366 |
|   2022 |       19 |      0.211 |          0.246 |     4.671 |  1.419 |


**Par session**

| session        |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| ASIA           |       27 |      0.222 |          0.193 |     5.202 |  1.283 |
| LATE           |        3 |      0.000 |         -0.796 |    -2.387 |  0.000 |
| LDN_NY_OVERLAP |       23 |      0.087 |         -0.553 |   -12.708 |  0.295 |
| LONDON         |       22 |      0.136 |          0.010 |     0.216 |  1.018 |
| NEW_YORK       |        9 |      0.222 |          0.238 |     2.145 |  1.381 |


**Par side**

| side   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------|---------:|-----------:|---------------:|----------:|-------:|
| BUY    |       46 |      0.196 |          0.128 |     5.910 |  1.220 |
| SELL   |       38 |      0.105 |         -0.354 |   -13.442 |  0.541 |


**Par vol_regime**

| vol_regime   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------------|---------:|-----------:|---------------:|----------:|-------:|
| LOW_VOL      |       28 |      0.107 |         -0.416 |   -11.652 |  0.502 |
| MID_VOL      |       28 |      0.214 |          0.336 |     9.421 |  1.658 |
| HIGH_VOL     |       28 |      0.143 |         -0.189 |    -5.301 |  0.712 |


**Par exit_reason**

| exit_reason   |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:--------------|---------:|-----------:|---------------:|----------:|--------:|
| BE            |       23 |      0.043 |         -0.026 |    -0.606 |   0.693 |
| SL            |       49 |      0.000 |         -1.105 |   -54.165 |   0.000 |
| TP            |       12 |      1.000 |          3.937 |    47.239 | inf     |


**Par s_entry_case**

| s_entry_case   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| A              |        2 |      0.000 |         -0.563 |    -1.125 |  0.000 |
| B              |       82 |      0.159 |         -0.078 |    -6.407 |  0.884 |


**Par mois** : 11 mois positifs / 37 ; meilleur 4.83R, pire -4.48R

**Coûts moyens** (R/trade) : commission -0.039, swap -0.006 ; spread moyen à l'exécution 0.347 $ ; 1R moyen 2.16 $ ; détention moyenne 2.4 h

## 4. Toutes les variantes (DEV)

| experiment   | config          | variant     |   trades |   placed |   fill_rate |   win_rate |   expectancy_r |   ci95_low |   ci95_high |   t_stat |   profit_factor_r |   total_r |   max_dd_r |   avg_cost_r |
|:-------------|:----------------|:------------|---------:|---------:|------------:|-----------:|---------------:|-----------:|------------:|---------:|------------------:|----------:|-----------:|-------------:|
| E1/E2        | BASE            | A_STRUCTURE |       84 |      162 |       0.519 |      0.155 |         -0.152 |     -0.481 |       0.215 |   -0.827 |             0.772 |   -12.808 |     23.512 |       -0.054 |
| E1/E2        | BASE            | B_LIQUIDITY |       84 |      162 |       0.519 |      0.155 |         -0.126 |     -0.464 |       0.245 |   -0.686 |             0.812 |   -10.551 |     18.410 |       -0.045 |
| E1/E2        | BASE            | C_FIXED_5R  |       84 |      162 |       0.519 |      0.155 |         -0.090 |     -0.433 |       0.292 |   -0.476 |             0.866 |    -7.532 |     14.566 |       -0.045 |
| E1/E2        | BASE            | C_FIXED_6R  |       84 |      162 |       0.519 |      0.155 |         -0.129 |     -0.473 |       0.252 |   -0.691 |             0.807 |   -10.843 |     16.933 |       -0.048 |
| E1/E2        | BASE            | D_TRAILING  |       84 |      162 |       0.519 |      0.155 |         -0.131 |     -0.473 |       0.249 |   -0.693 |             0.803 |   -11.035 |     22.767 |       -0.048 |
| E3           | RSI_CONTINUOUS  | A_STRUCTURE |      107 |      226 |       0.473 |      0.150 |         -0.155 |     -0.446 |       0.161 |   -0.998 |             0.757 |   -16.633 |     31.174 |       -0.049 |
| E3           | RSI_CONTINUOUS  | B_LIQUIDITY |      107 |      226 |       0.473 |      0.150 |         -0.159 |     -0.437 |       0.147 |   -1.053 |             0.751 |   -17.014 |     26.721 |       -0.045 |
| E3           | RSI_CONTINUOUS  | C_FIXED_5R  |      107 |      226 |       0.473 |      0.150 |         -0.122 |     -0.412 |       0.187 |   -0.779 |             0.809 |   -13.066 |     23.481 |       -0.044 |
| E3           | RSI_CONTINUOUS  | C_FIXED_6R  |      107 |      226 |       0.473 |      0.150 |         -0.148 |     -0.434 |       0.166 |   -0.947 |             0.768 |   -15.877 |     26.245 |       -0.046 |
| E3           | RSI_CONTINUOUS  | D_TRAILING  |      107 |      226 |       0.473 |      0.150 |         -0.135 |     -0.431 |       0.190 |   -0.839 |             0.789 |   -14.397 |     29.936 |       -0.045 |
| E3           | RSI_GATE        | A_STRUCTURE |      107 |      226 |       0.473 |      0.150 |         -0.155 |     -0.446 |       0.161 |   -0.998 |             0.757 |   -16.633 |     31.174 |       -0.049 |
| E3           | RSI_GATE        | B_LIQUIDITY |      107 |      226 |       0.473 |      0.150 |         -0.159 |     -0.437 |       0.147 |   -1.053 |             0.751 |   -17.014 |     26.721 |       -0.045 |
| E3           | RSI_GATE        | C_FIXED_5R  |      107 |      226 |       0.473 |      0.150 |         -0.122 |     -0.412 |       0.187 |   -0.779 |             0.809 |   -13.066 |     23.481 |       -0.044 |
| E3           | RSI_GATE        | C_FIXED_6R  |      107 |      226 |       0.473 |      0.150 |         -0.148 |     -0.434 |       0.166 |   -0.947 |             0.768 |   -15.877 |     26.245 |       -0.046 |
| E3           | RSI_GATE        | D_TRAILING  |      107 |      226 |       0.473 |      0.150 |         -0.135 |     -0.431 |       0.190 |   -0.839 |             0.789 |   -14.397 |     29.936 |       -0.045 |
| E3           | RSI_OFF         | A_STRUCTURE |      122 |      271 |       0.450 |      0.148 |         -0.198 |     -0.469 |       0.091 |   -1.377 |             0.703 |   -24.113 |     38.240 |       -0.052 |
| E3           | RSI_OFF         | B_LIQUIDITY |      122 |      271 |       0.450 |      0.148 |         -0.181 |     -0.454 |       0.120 |   -1.266 |             0.728 |   -22.090 |     31.074 |       -0.048 |
| E3           | RSI_OFF         | C_FIXED_5R  |      122 |      271 |       0.450 |      0.148 |         -0.168 |     -0.440 |       0.131 |   -1.165 |             0.747 |   -20.541 |     29.474 |       -0.048 |
| E3           | RSI_OFF         | C_FIXED_6R  |      122 |      271 |       0.450 |      0.148 |         -0.187 |     -0.460 |       0.109 |   -1.288 |             0.718 |   -22.853 |     33.121 |       -0.050 |
| E3           | RSI_OFF         | D_TRAILING  |      122 |      271 |       0.450 |      0.148 |         -0.179 |     -0.455 |       0.114 |   -1.214 |             0.731 |   -21.853 |     37.294 |       -0.049 |
| E4           | DEPTH_0         | A_STRUCTURE |       83 |      160 |       0.519 |      0.181 |          0.007 |     -0.341 |       0.408 |    0.034 |             1.011 |     0.540 |     15.938 |       -0.052 |
| E4           | DEPTH_0         | B_LIQUIDITY |       83 |      160 |       0.519 |      0.181 |          0.013 |     -0.334 |       0.413 |    0.071 |             1.022 |     1.106 |     11.779 |       -0.045 |
| E4           | DEPTH_0         | C_FIXED_5R  |       83 |      160 |       0.519 |      0.181 |         -0.008 |     -0.345 |       0.377 |   -0.045 |             0.986 |    -0.683 |     11.174 |       -0.045 |
| E4           | DEPTH_0         | C_FIXED_6R  |       83 |      160 |       0.519 |      0.181 |         -0.019 |     -0.361 |       0.390 |   -0.099 |             0.969 |    -1.546 |     14.058 |       -0.048 |
| E4           | DEPTH_0         | D_TRAILING  |       83 |      160 |       0.519 |      0.181 |         -0.047 |     -0.365 |       0.335 |   -0.260 |             0.922 |    -3.864 |     19.129 |       -0.047 |
| E4           | DEPTH_1         | A_STRUCTURE |       75 |      146 |       0.514 |      0.107 |         -0.289 |     -0.613 |       0.083 |   -1.586 |             0.562 |   -21.683 |     28.873 |       -0.058 |
| E4           | DEPTH_1         | B_LIQUIDITY |       75 |      146 |       0.514 |      0.107 |         -0.324 |     -0.610 |      -0.011 |   -2.078 |             0.508 |   -24.331 |     26.501 |       -0.049 |
| E4           | DEPTH_1         | C_FIXED_5R  |       75 |      146 |       0.514 |      0.107 |         -0.308 |     -0.604 |       0.012 |   -1.921 |             0.534 |   -23.067 |     23.691 |       -0.049 |
| E4           | DEPTH_1         | C_FIXED_6R  |       75 |      146 |       0.514 |      0.107 |         -0.308 |     -0.610 |       0.028 |   -1.871 |             0.533 |   -23.083 |     24.708 |       -0.049 |
| E4           | DEPTH_1         | D_TRAILING  |       75 |      146 |       0.514 |      0.107 |         -0.272 |     -0.602 |       0.115 |   -1.459 |             0.587 |   -20.433 |     27.935 |       -0.052 |
| E5           | ENTRY_M5        | A_STRUCTURE |      198 |      443 |       0.447 |      0.131 |         -0.368 |     -0.565 |      -0.151 |   -3.482 |             0.501 |   -72.884 |     73.279 |       -0.055 |
| E5           | ENTRY_M5        | B_LIQUIDITY |      198 |      443 |       0.447 |      0.131 |         -0.417 |     -0.593 |      -0.228 |   -4.585 |             0.434 |   -82.661 |     82.661 |       -0.055 |
| E5           | ENTRY_M5        | C_FIXED_5R  |      198 |      443 |       0.447 |      0.131 |         -0.402 |     -0.580 |      -0.214 |   -4.325 |             0.455 |   -79.666 |     81.176 |       -0.055 |
| E5           | ENTRY_M5        | C_FIXED_6R  |      198 |      443 |       0.447 |      0.131 |         -0.433 |     -0.601 |      -0.253 |   -4.850 |             0.412 |   -85.814 |     85.814 |       -0.056 |
| E5           | ENTRY_M5        | D_TRAILING  |      198 |      443 |       0.447 |      0.131 |         -0.356 |     -0.556 |      -0.133 |   -3.307 |             0.517 |   -70.481 |     71.037 |       -0.055 |
| E6           | BIAS_H4_LEADS   | A_STRUCTURE |       84 |      162 |       0.519 |      0.155 |         -0.152 |     -0.481 |       0.215 |   -0.827 |             0.772 |   -12.808 |     23.512 |       -0.054 |
| E6           | BIAS_H4_LEADS   | B_LIQUIDITY |       84 |      162 |       0.519 |      0.155 |         -0.126 |     -0.464 |       0.245 |   -0.686 |             0.812 |   -10.551 |     18.410 |       -0.045 |
| E6           | BIAS_H4_LEADS   | C_FIXED_5R  |       84 |      162 |       0.519 |      0.155 |         -0.090 |     -0.433 |       0.292 |   -0.476 |             0.866 |    -7.532 |     14.566 |       -0.045 |
| E6           | BIAS_H4_LEADS   | C_FIXED_6R  |       84 |      162 |       0.519 |      0.155 |         -0.129 |     -0.473 |       0.252 |   -0.691 |             0.807 |   -10.843 |     16.933 |       -0.048 |
| E6           | BIAS_H4_LEADS   | D_TRAILING  |       84 |      162 |       0.519 |      0.155 |         -0.131 |     -0.473 |       0.249 |   -0.693 |             0.803 |   -11.035 |     22.767 |       -0.048 |
| E6           | FLIP_NEUTRAL    | A_STRUCTURE |       48 |       96 |       0.500 |      0.167 |         -0.008 |     -0.504 |       0.564 |   -0.029 |             0.988 |    -0.368 |     13.478 |       -0.062 |
| E6           | FLIP_NEUTRAL    | B_LIQUIDITY |       48 |       96 |       0.500 |      0.167 |          0.007 |     -0.473 |       0.545 |    0.029 |             1.012 |     0.360 |     11.529 |       -0.047 |
| E6           | FLIP_NEUTRAL    | C_FIXED_5R  |       48 |       96 |       0.500 |      0.167 |          0.029 |     -0.463 |       0.578 |    0.111 |             1.047 |     1.401 |     11.120 |       -0.047 |
| E6           | FLIP_NEUTRAL    | C_FIXED_6R  |       48 |       96 |       0.500 |      0.167 |         -0.018 |     -0.510 |       0.541 |   -0.071 |             0.971 |    -0.885 |     11.115 |       -0.051 |
| E6           | FLIP_NEUTRAL    | D_TRAILING  |       48 |       96 |       0.500 |      0.167 |         -0.030 |     -0.513 |       0.532 |   -0.115 |             0.952 |    -1.454 |     14.580 |       -0.052 |
| E6           | IMPULSE_BOS_BAR | A_STRUCTURE |       51 |      180 |       0.283 |      0.176 |         -0.232 |     -0.629 |       0.210 |   -1.069 |             0.684 |   -11.813 |     15.791 |       -0.059 |
| E6           | IMPULSE_BOS_BAR | B_LIQUIDITY |       51 |      180 |       0.283 |      0.176 |         -0.185 |     -0.613 |       0.306 |   -0.778 |             0.748 |    -9.421 |     12.864 |       -0.051 |
| E6           | IMPULSE_BOS_BAR | C_FIXED_5R  |       51 |      180 |       0.283 |      0.176 |         -0.089 |     -0.555 |       0.443 |   -0.348 |             0.879 |    -4.533 |     11.126 |       -0.047 |
| E6           | IMPULSE_BOS_BAR | C_FIXED_6R  |       51 |      180 |       0.283 |      0.176 |         -0.129 |     -0.589 |       0.385 |   -0.509 |             0.824 |    -6.575 |     13.147 |       -0.047 |
| E6           | IMPULSE_BOS_BAR | D_TRAILING  |       51 |      180 |       0.283 |      0.176 |         -0.189 |     -0.605 |       0.277 |   -0.829 |             0.742 |    -9.653 |     12.919 |       -0.048 |
| E6           | INV_WICK        | A_STRUCTURE |       67 |      162 |       0.414 |      0.194 |         -0.003 |     -0.417 |       0.443 |   -0.015 |             0.995 |    -0.231 |     16.553 |       -0.058 |
| E6           | INV_WICK        | B_LIQUIDITY |       67 |      162 |       0.414 |      0.194 |          0.030 |     -0.379 |       0.470 |    0.135 |             1.047 |     2.026 |     12.143 |       -0.047 |
| E6           | INV_WICK        | C_FIXED_5R  |       67 |      162 |       0.414 |      0.194 |          0.075 |     -0.341 |       0.528 |    0.327 |             1.116 |     5.045 |     10.259 |       -0.047 |
| E6           | INV_WICK        | C_FIXED_6R  |       67 |      162 |       0.414 |      0.194 |          0.026 |     -0.403 |       0.481 |    0.113 |             1.040 |     1.734 |      9.988 |       -0.050 |
| E6           | INV_WICK        | D_TRAILING  |       67 |      162 |       0.414 |      0.194 |          0.023 |     -0.401 |       0.491 |    0.099 |             1.035 |     1.542 |     15.240 |       -0.051 |
| E6           | SL_BUFFER_025   | A_STRUCTURE |       90 |      174 |       0.517 |      0.189 |         -0.150 |     -0.459 |       0.194 |   -0.882 |             0.781 |   -13.544 |     26.128 |       -0.048 |
| E6           | SL_BUFFER_025   | B_LIQUIDITY |       90 |      174 |       0.517 |      0.189 |         -0.045 |     -0.383 |       0.336 |   -0.240 |             0.935 |    -4.056 |     14.814 |       -0.044 |
| E6           | SL_BUFFER_025   | C_FIXED_5R  |       90 |      174 |       0.517 |      0.189 |         -0.087 |     -0.415 |       0.272 |   -0.483 |             0.873 |    -7.857 |     20.173 |       -0.045 |
| E6           | SL_BUFFER_025   | C_FIXED_6R  |       90 |      174 |       0.517 |      0.189 |         -0.124 |     -0.444 |       0.244 |   -0.691 |             0.820 |   -11.135 |     19.894 |       -0.048 |
| E6           | SL_BUFFER_025   | D_TRAILING  |       90 |      174 |       0.517 |      0.189 |         -0.124 |     -0.440 |       0.234 |   -0.701 |             0.820 |   -11.130 |     24.751 |       -0.045 |
| E6           | SWEEP_LOG_ONLY  | A_STRUCTURE |      304 |      640 |       0.475 |      0.135 |         -0.227 |     -0.387 |      -0.063 |   -2.671 |             0.641 |   -68.882 |     79.039 |       -0.049 |
| E6           | SWEEP_LOG_ONLY  | B_LIQUIDITY |      304 |      640 |       0.475 |      0.135 |         -0.230 |     -0.382 |      -0.073 |   -2.859 |             0.635 |   -69.965 |     80.511 |       -0.047 |
| E6           | SWEEP_LOG_ONLY  | C_FIXED_5R  |      304 |      640 |       0.475 |      0.135 |         -0.186 |     -0.348 |      -0.019 |   -2.156 |             0.705 |   -56.503 |     71.283 |       -0.047 |
| E6           | SWEEP_LOG_ONLY  | C_FIXED_6R  |      304 |      640 |       0.475 |      0.135 |         -0.196 |     -0.360 |      -0.028 |   -2.236 |             0.690 |   -59.480 |     72.314 |       -0.048 |
| E6           | SWEEP_LOG_ONLY  | D_TRAILING  |      304 |      640 |       0.475 |      0.135 |         -0.230 |     -0.386 |      -0.068 |   -2.773 |             0.635 |   -69.904 |     79.064 |       -0.047 |
| E6           | SWING_ENTRY_3   | A_STRUCTURE |       63 |      122 |       0.516 |      0.143 |         -0.194 |     -0.522 |       0.207 |   -1.030 |             0.679 |   -12.209 |     13.828 |       -0.043 |
| E6           | SWING_ENTRY_3   | B_LIQUIDITY |       63 |      122 |       0.516 |      0.143 |         -0.142 |     -0.485 |       0.264 |   -0.722 |             0.766 |    -8.915 |     13.608 |       -0.042 |
| E6           | SWING_ENTRY_3   | C_FIXED_5R  |       63 |      122 |       0.516 |      0.143 |         -0.121 |     -0.472 |       0.275 |   -0.613 |             0.800 |    -7.607 |     13.313 |       -0.042 |
| E6           | SWING_ENTRY_3   | C_FIXED_6R  |       63 |      122 |       0.516 |      0.143 |         -0.113 |     -0.470 |       0.301 |   -0.553 |             0.813 |    -7.125 |     14.830 |       -0.042 |
| E6           | SWING_ENTRY_3   | D_TRAILING  |       63 |      122 |       0.516 |      0.143 |         -0.137 |     -0.485 |       0.277 |   -0.685 |             0.773 |    -8.644 |     12.792 |       -0.043 |


## 5. Comparaisons multiples

- Nombre de variantes : 70
- Meilleur t observé : 0.33 ; seuil « hasard » √(2 ln N) ≈ 2.91
- Conclusion : aucune variante ne dépasse ce qui est attendu par le seul hasard

## 6. Sensibilité aux coûts (signaux baseline, DEV)

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


## 7. Walk-forward ancré (choix runner × profondeur d'entrée)

- 2020: choisi DEPTH_0/C_FIXED_5R (E in-sample=-0.180R) -> OOS n=23 E=0.062R
- 2021: choisi DEPTH_0/B_LIQUIDITY (E in-sample=-0.030R) -> OOS n=17 E=-0.300R
- 2022: choisi DEPTH_0/B_LIQUIDITY (E in-sample=-0.103R) -> OOS n=20 E=0.379R
- 2023: choisi DEPTH_0/B_LIQUIDITY (E in-sample=0.013R) -> OOS n=29 E=-0.165R
- 2024: choisi DEPTH_0/A_STRUCTURE (E in-sample=-0.017R) -> OOS n=0 E=nanR

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|
|       89 |      0.202 |       2.945 |       -0.759 |         -0.010 |     -1.037 |   1.641 |   -0.057 |     -0.334 |       0.338 |         0.530 |             0.983 |    -0.890 |     11.779 |    4.481 |    -1.248 |


## 8. Application de la règle de sélection pré-enregistrée

- Baseline BASE/C_FIXED_5R: n=84, E=-0.090R, PF=0.87
- Aucune variante ne satisfait toutes les contraintes (n>=100, PF>=1.10, espérance hors meilleur trade > 0, >=3 années positives sur 4). Conformément au plan, la baseline est conservée et la conclusion DEV est : pas d'avantage démontré.

Configuration retenue pour la validation : `BASE` / `C_FIXED_5R` (Reports/selected_config.json)
