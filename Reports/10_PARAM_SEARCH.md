# Cycle 3 — recherche de paramètres et walk-forward

- 400 configurations de signaux × 6 gestions = **2400 variantes** (plan pré-enregistré)
- Coûts de base (spread réel Dukascopy, commission 7 $/lot, slippage, swaps). R par trade, sans limites de compte.
- **Le chiffre de référence est le R/mois hors échantillon du walk-forward.** Le meilleur réglage in-sample est
  mécaniquement surévalué (choisi parmi des milliers d'essais sur les mêmes données).

## 1. Meilleures variantes in-sample 2019 → 2026-09 (biaisées à la hausse)

|   cfg | mgmt           |   n |   r_month |   mean |    pf |     t |   total |
|------:|:---------------|----:|----------:|-------:|------:|------:|--------:|
|    93 | M3_noBE_TP3    | 111 |     0.245 |  0.205 | 1.283 | 1.153 |  22.767 |
|   344 | M3_noBE_TP3    |  80 |     0.204 |  0.237 | 1.327 | 1.114 |  18.994 |
|    93 | M2_BE2_P3_TP5  | 111 |     0.200 |  0.167 | 1.245 | 0.927 |  18.570 |
|    99 | M3_noBE_TP3    |  72 |     0.194 |  0.250 | 1.347 | 1.116 |  18.000 |
|    99 | M1_noBE_P3_TP5 |  72 |     0.174 |  0.224 | 1.281 | 0.865 |  16.134 |
|   106 | M3_noBE_TP3    |  90 |     0.169 |  0.174 | 1.236 | 0.885 |  15.703 |
|   228 | M3_noBE_TP3    |  58 |     0.165 |  0.264 | 1.370 | 1.050 |  15.310 |
|   244 | M4_noBE_TP2    |  57 |     0.158 |  0.258 | 1.428 | 1.281 |  14.708 |
|   194 | M3_noBE_TP3    | 100 |     0.153 |  0.142 | 1.191 | 0.769 |  14.218 |
|   154 | M3_noBE_TP3    |  90 |     0.153 |  0.158 | 1.212 | 0.806 |  14.210 |

Seuil « hasard » pour 2400 variantes : t ≈ √(2 ln N) = 3.95.

Paramètres des 3 premières :

- cfg 93 / M3_noBE_TP3 : `{"entry_tf": 15, "swing_entry": 2, "swing_htf": 2, "bias_flip_mode": "NEUTRAL_ON_CHOCH", "caution_sweep_action": "LOG_ONLY", "rsi": "OFF", "entry_depth": 0.5, "continuation_invalidation": "WICK", "impulse_anchor": "SWING_CONFIRM", "sl_buffer_atr": 0.3, "fvg_min_atr": 0.3, "reject_if_touched_before_placement": false}`
- cfg 344 / M3_noBE_TP3 : `{"entry_tf": 15, "swing_entry": 2, "swing_htf": 3, "bias_flip_mode": "FLIP_ON_CHOCH", "caution_sweep_action": "BLOCK", "rsi": "GATE_ENTRY", "entry_depth": 0.5, "continuation_invalidation": "WICK", "impulse_anchor": "SWING_CONFIRM", "sl_buffer_atr": 0.3, "fvg_min_atr": 0.0, "reject_if_touched_before_placement": true}`
- cfg 93 / M2_BE2_P3_TP5 : `{"entry_tf": 15, "swing_entry": 2, "swing_htf": 2, "bias_flip_mode": "NEUTRAL_ON_CHOCH", "caution_sweep_action": "LOG_ONLY", "rsi": "OFF", "entry_depth": 0.5, "continuation_invalidation": "WICK", "impulse_anchor": "SWING_CONFIRM", "sl_buffer_atr": 0.3, "fvg_min_atr": 0.3, "reject_if_touched_before_placement": false}`

Distribution du R/mois sur les 1164 variantes ayant ≥ 50 trades : médiane -0.32, 10 % -1.15, 90 % -0.04, max 0.24.

## 2.A Walk-forward — critère R total, toutes gestions

|   test |   cfg | mgmt           |   train_n |   train_R_month |   train_pf |   test_n |   test_R_total |   test_R_month |   test_E |
|-------:|------:|:---------------|----------:|----------------:|-----------:|---------:|---------------:|---------------:|---------:|
|   2022 |   163 | M5_BE1_TP3     |        37 |            0.51 |       2.36 |       14 |           1.41 |           0.12 |    0.101 |
|   2023 |   382 | M1_noBE_P3_TP5 |        74 |            0.65 |       1.4  |       22 |         -16.03 |          -1.34 |   -0.729 |
|   2024 |    93 | M3_noBE_TP3    |        34 |            0.66 |       2.14 |       25 |          -2.45 |          -0.2  |   -0.098 |
|   2025 |    93 | M3_noBE_TP3    |        53 |            0.43 |       1.42 |       17 |           2.56 |           0.21 |    0.15  |
|   2026 |   317 | M1_noBE_P3_TP5 |        37 |            0.56 |       1.75 |        7 |          -7.22 |          -0.8  |   -1.031 |

**Hors échantillon 2022 → 2026-09 : 85 trades, espérance -0.256 R (IC95 [-0.574 ; +0.095]), PF 0.69, total -21.7 R, soit -0.38 R/mois, drawdown max 24.3 R.**

Mois positifs : 12 / 45 mois avec trades ; meilleur mois +6.0 R, pire mois -5.3 R.

## 2.B Walk-forward — critère t, toutes gestions

|   test |   cfg | mgmt          |   train_n |   train_R_month |   train_pf |   test_n |   test_R_total |   test_R_month |   test_E |
|-------:|------:|:--------------|----------:|----------------:|-----------:|---------:|---------------:|---------------:|---------:|
|   2022 |   163 | M5_BE1_TP3    |        37 |            0.51 |       2.36 |       14 |           1.41 |           0.12 |    0.101 |
|   2023 |    93 | M3_noBE_TP3   |        32 |            0.62 |       2.16 |       12 |          -1.01 |          -0.08 |   -0.084 |
|   2024 |    93 | M3_noBE_TP3   |        34 |            0.66 |       2.14 |       25 |          -2.45 |          -0.2  |   -0.098 |
|   2025 |   373 | M3_noBE_TP3   |        32 |            0.37 |       1.61 |       10 |          -6.43 |          -0.54 |   -0.643 |
|   2026 |   317 | M2_BE2_P3_TP5 |        37 |            0.54 |       1.79 |        7 |          -4.71 |          -0.53 |   -0.673 |

**Hors échantillon 2022 → 2026-09 : 68 trades, espérance -0.194 R (IC95 [-0.600 ; +0.226]), PF 0.77, total -13.2 R, soit -0.23 R/mois, drawdown max 21.5 R.**

Mois positifs : 13 / 40 mois avec trades ; meilleur mois +4.9 R, pire mois -5.3 R.

## 2.C Walk-forward — critère R total, gestion de l'utilisateur (M0) seulement

|   test |   cfg | mgmt          |   train_n |   train_R_month |   train_pf |   test_n |   test_R_total |   test_R_month |   test_E |
|-------:|------:|:--------------|----------:|----------------:|-----------:|---------:|---------------:|---------------:|---------:|
|   2022 |   163 | M0_BE1_P3_TP5 |        37 |            0.38 |       2.03 |       14 |           4.38 |           0.37 |    0.313 |
|   2023 |    70 | M0_BE1_P3_TP5 |        31 |            0.36 |       2.06 |        9 |           3.15 |           0.26 |    0.35  |
|   2024 |    70 | M0_BE1_P3_TP5 |        30 |            0.44 |       2.08 |       19 |          -9.24 |          -0.77 |   -0.486 |
|   2025 |   369 | M0_BE1_P3_TP5 |        59 |            0.3  |       1.34 |       25 |          -5.83 |          -0.49 |   -0.233 |
|   2026 |   317 | M0_BE1_P3_TP5 |        37 |            0.41 |       1.82 |        7 |          -2.71 |          -0.3  |   -0.387 |

**Hors échantillon 2022 → 2026-09 : 74 trades, espérance -0.139 R (IC95 [-0.452 ; +0.222]), PF 0.76, total -10.3 R, soit -0.18 R/mois, drawdown max 21.1 R.**

Mois positifs : 9 / 40 mois avec trades ; meilleur mois +4.0 R, pire mois -4.1 R.

## 3. Influence des paramètres (moyenne du R/mois in-sample par valeur)

**entry_tf**

|   entry_tf |   r_month |   trades_month |   expectancy |
|-----------:|----------:|---------------:|-------------:|
|          5 |    -0.407 |          1.249 |       -0.313 |
|         15 |    -0.091 |          0.540 |       -0.200 |

**swing_entry**

|   swing_entry |   r_month |   trades_month |   expectancy |
|--------------:|----------:|---------------:|-------------:|
|             2 |    -0.357 |          1.207 |       -0.260 |
|             3 |    -0.250 |          0.835 |       -0.263 |
|             5 |    -0.155 |          0.682 |       -0.252 |

**swing_htf**

|   swing_htf |   r_month |   trades_month |   expectancy |
|------------:|----------:|---------------:|-------------:|
|           2 |    -0.232 |          0.839 |       -0.260 |
|           3 |    -0.265 |          0.965 |       -0.248 |
|           5 |    -0.267 |          0.917 |       -0.267 |

**bias_flip_mode**

| bias_flip_mode   |   r_month |   trades_month |   expectancy |
|:-----------------|----------:|---------------:|-------------:|
| FLIP_ON_CHOCH    |    -0.330 |          1.131 |       -0.272 |
| NEUTRAL_ON_CHOCH |    -0.184 |          0.695 |       -0.245 |

**caution_sweep_action**

| caution_sweep_action   |   r_month |   trades_month |   expectancy |
|:-----------------------|----------:|---------------:|-------------:|
| BLOCK                  |    -0.127 |          0.465 |       -0.265 |
| LOG_ONLY               |    -0.389 |          1.372 |       -0.251 |

**rsi**

| rsi            |   r_month |   trades_month |   expectancy |
|:---------------|----------:|---------------:|-------------:|
| AT_SETUP_ENTRY |    -0.226 |          0.765 |       -0.291 |
| AT_SETUP_H1    |    -0.289 |          0.847 |       -0.373 |
| GATE_ENTRY     |    -0.229 |          0.970 |       -0.168 |
| OFF            |    -0.273 |          1.034 |       -0.207 |

**entry_depth**

|   entry_depth |   r_month |   trades_month |   expectancy |
|--------------:|----------:|---------------:|-------------:|
|         0.000 |    -0.278 |          0.981 |       -0.242 |
|         0.500 |    -0.227 |          0.846 |       -0.258 |
|         1.000 |    -0.256 |          0.881 |       -0.279 |

**continuation_invalidation**

| continuation_invalidation   |   r_month |   trades_month |   expectancy |
|:----------------------------|----------:|---------------:|-------------:|
| CLOSE                       |    -0.305 |          1.049 |       -0.264 |
| WICK                        |    -0.208 |          0.775 |       -0.254 |

**impulse_anchor**

| impulse_anchor   |   r_month |   trades_month |   expectancy |
|:-----------------|----------:|---------------:|-------------:|
| BOS_BAR          |    -0.152 |          0.577 |       -0.262 |
| SWING_CONFIRM    |    -0.360 |          1.247 |       -0.255 |

**sl_buffer_atr**

|   sl_buffer_atr |   r_month |   trades_month |   expectancy |
|----------------:|----------:|---------------:|-------------:|
|           0.100 |    -0.277 |          0.916 |       -0.268 |
|           0.300 |    -0.231 |          0.896 |       -0.248 |

**fvg_min_atr**

|   fvg_min_atr |   r_month |   trades_month |   expectancy |
|--------------:|----------:|---------------:|-------------:|
|         0.000 |    -0.385 |          1.461 |       -0.232 |
|         0.300 |    -0.290 |          0.976 |       -0.230 |
|         0.600 |    -0.100 |          0.320 |       -0.309 |

**reject_if_touched_before_placement**

| reject_if_touched_before_placement   |   r_month |   trades_month |   expectancy |
|:-------------------------------------|----------:|---------------:|-------------:|
| False                                |    -0.255 |          0.926 |       -0.263 |
| True                                 |    -0.254 |          0.883 |       -0.253 |

**mgmt**

| mgmt           |   r_month |   trades_month |   expectancy |
|:---------------|----------:|---------------:|-------------:|
| M0_BE1_P3_TP5  |    -0.239 |          0.906 |       -0.278 |
| M1_noBE_P3_TP5 |    -0.321 |          0.906 |       -0.306 |
| M2_BE2_P3_TP5  |    -0.250 |          0.906 |       -0.258 |
| M3_noBE_TP3    |    -0.222 |          0.906 |       -0.196 |
| M4_noBE_TP2    |    -0.256 |          0.906 |       -0.243 |
| M5_BE1_TP3     |    -0.238 |          0.906 |       -0.269 |
