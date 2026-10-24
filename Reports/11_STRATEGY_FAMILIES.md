# Cycle 4 — familles de stratégies reconnues sur XAU/USD

- Plan pré-enregistré : `Research/EXPERIMENT_PLAN.md` (cycle 4). 46 variantes, coûts de base du plan v1 (spread réel, 7 $/lot, slippage 0,10 $ sur entrées marché/stop et stops, swaps).
- **Chiffre de référence : walk-forward** (réglage choisi sur les 3 années précédentes, appliqué à l'année suivante). Les tableaux in-sample sont fournis pour comprendre, pas pour choisir.
- L'or a triplé sur la période : comparer espérance acheteuse (E_long) et vendeuse (E_short).

## 1. In-sample 2019 → 2026-09 (toutes variantes, biaisé à la hausse)

| family         | variant          |   trades |   trades_month |   expectancy |    pf |      t |   R_month |   max_dd_r |   E_long |   E_short |   R_month_stress |
|:---------------|:-----------------|---------:|---------------:|-------------:|------:|-------:|----------:|-----------:|---------:|----------:|-----------------:|
| F1_DONCHIAN    | tf1440_N55_k2    |       23 |          0.247 |        1.384 | 2.781 |  0.888 |     0.342 |     11.392 |    3.437 |    -0.856 |            0.180 |
| F1_DONCHIAN    | tf240_N20_k2     |      365 |          3.926 |        0.072 | 1.123 |  0.675 |     0.282 |     20.773 |    0.252 |    -0.131 |           -0.210 |
| F1_DONCHIAN    | tf240_N20_k3     |      335 |          3.603 |        0.071 | 1.168 |  0.894 |     0.255 |     13.466 |    0.197 |    -0.077 |           -0.050 |
| F1_DONCHIAN    | tf1440_N55_k3    |       22 |          0.237 |        0.936 | 2.606 |  0.858 |     0.221 |      8.347 |    2.359 |    -0.772 |            0.117 |
| F5_COMPRESSION | INSIDE_tp2R      |      271 |          2.915 |        0.058 | 1.177 |  1.072 |     0.169 |      8.360 |    0.127 |    -0.021 |            0.009 |
| F5_COMPRESSION | INSIDE_tpEOD     |      271 |          2.915 |        0.054 | 1.162 |  0.949 |     0.159 |      7.834 |    0.099 |     0.004 |           -0.014 |
| F5_COMPRESSION | NR7_tp2R         |      276 |          2.968 |        0.045 | 1.120 |  0.783 |     0.134 |      9.959 |    0.095 |    -0.016 |           -0.082 |
| F5_COMPRESSION | INSIDE_tp1R      |      271 |          2.915 |        0.046 | 1.150 |  0.995 |     0.134 |      8.065 |    0.084 |     0.002 |           -0.026 |
| F1_DONCHIAN    | tf240_N55_k3     |      160 |          1.721 |        0.054 | 1.088 |  0.321 |     0.094 |     18.973 |    0.449 |    -0.393 |           -0.147 |
| F5_COMPRESSION | NR7_tpEOD        |      276 |          2.968 |        0.029 | 1.077 |  0.495 |     0.087 |     10.509 |    0.074 |    -0.025 |           -0.141 |
| F1_DONCHIAN    | tf240_N55_k2     |      187 |          2.011 |        0.030 | 1.039 |  0.144 |     0.059 |     26.786 |    0.553 |    -0.535 |           -0.308 |
| F5_COMPRESSION | NR7_tp1R         |      276 |          2.968 |        0.019 | 1.053 |  0.383 |     0.055 |     11.016 |    0.035 |    -0.002 |           -0.152 |
| F1_DONCHIAN    | tf1440_N20_k2    |       60 |          0.645 |        0.015 | 1.025 |  0.062 |     0.009 |     15.330 |    0.535 |    -0.581 |           -0.126 |
| F1_DONCHIAN    | tf1440_N20_k3    |       58 |          0.624 |       -0.035 | 0.922 | -0.209 |    -0.022 |     12.133 |    0.304 |    -0.424 |           -0.117 |
| F4_PULLBACK    | tp3R_long        |      646 |          6.948 |       -0.005 | 0.993 | -0.080 |    -0.036 |     50.951 |   -0.005 |   nan     |           -0.771 |
| F4_PULLBACK    | tp1.5R_long      |      800 |          8.604 |       -0.021 | 0.965 | -0.494 |    -0.181 |     46.151 |   -0.021 |   nan     |           -1.074 |
| F4_PULLBACK    | tp2R_long        |      724 |          7.787 |       -0.038 | 0.943 | -0.746 |    -0.297 |     56.217 |   -0.038 |   nan     |           -0.890 |
| F3_RSI2        | s5_sma200_long   |      676 |          7.271 |       -0.054 | 0.830 | -1.947 |    -0.391 |     44.070 |   -0.054 |   nan     |           -0.983 |
| F4_PULLBACK    | tp3R_both        |     1059 |         11.390 |       -0.048 | 0.933 | -0.979 |    -0.552 |    110.733 |    0.003 |    -0.126 |           -1.856 |
| F4_PULLBACK    | tp2R_both        |     1193 |         12.831 |       -0.057 | 0.916 | -1.431 |    -0.726 |     99.865 |   -0.032 |    -0.093 |           -1.813 |
| F3_RSI2        | s10_sma200_long  |     1289 |         13.864 |       -0.053 | 0.827 | -2.729 |    -0.742 |     78.702 |   -0.053 |   nan     |           -1.923 |
| F4_PULLBACK    | tp1.5R_both      |     1307 |         14.057 |       -0.056 | 0.909 | -1.674 |    -0.781 |    101.730 |   -0.020 |    -0.110 |           -2.117 |
| F2_ORB         | NY_60m_tpEOS     |     1948 |         20.951 |       -0.039 | 0.918 | -1.420 |    -0.820 |     92.681 |   -0.003 |    -0.081 |           -2.614 |
| F3_RSI2        | s5_sma200_both   |     1178 |         12.670 |       -0.076 | 0.770 | -3.614 |    -0.965 |     98.875 |   -0.054 |    -0.106 |           -2.006 |
| F2_ORB         | NY_60m_tp2R      |     1948 |         20.951 |       -0.047 | 0.899 | -1.990 |    -0.981 |    102.055 |   -0.032 |    -0.064 |           -2.680 |
| F2_ORB         | NY_60m_tp1R      |     1948 |         20.951 |       -0.057 | 0.866 | -2.933 |    -1.199 |    118.643 |   -0.067 |    -0.045 |           -2.856 |
| F3_RSI2        | s5_nofilt_long   |     1680 |         18.069 |       -0.074 | 0.784 | -4.094 |    -1.342 |    128.778 |   -0.074 |   nan     |           -2.828 |
| F3_RSI2        | s10_sma200_both  |     2252 |         24.221 |       -0.061 | 0.806 | -4.110 |    -1.481 |    156.195 |   -0.053 |    -0.071 |           -3.440 |
| F2_ORB         | NY_30m_tpEOS     |     1991 |         21.414 |       -0.079 | 0.870 | -2.343 |    -1.692 |    165.684 |   -0.076 |    -0.082 |           -3.852 |
| F2_ORB         | NY_30m_tp2R      |     1991 |         21.414 |       -0.089 | 0.846 | -3.335 |    -1.910 |    187.027 |   -0.113 |    -0.060 |           -3.777 |
| F2_ORB         | LONDON_60m_tp1R  |     1920 |         20.650 |       -0.093 | 0.754 | -5.365 |    -1.916 |    179.437 |   -0.082 |    -0.106 |           -4.320 |
| F2_ORB         | LONDON_60m_tp2R  |     1920 |         20.650 |       -0.096 | 0.756 | -4.914 |    -1.980 |    187.778 |   -0.095 |    -0.097 |           -4.493 |
| F2_ORB         | LONDON_60m_tpEOS |     1920 |         20.650 |       -0.097 | 0.753 | -4.742 |    -2.011 |    189.919 |   -0.095 |    -0.101 |           -4.581 |
| F3_RSI2        | s10_nofilt_long  |     2855 |         30.706 |       -0.071 | 0.789 | -5.178 |    -2.178 |    206.000 |   -0.071 |   nan     |           -4.775 |
| F2_ORB         | NY_15m_tpEOS     |     2000 |         21.511 |       -0.103 | 0.854 | -2.521 |    -2.224 |    218.220 |   -0.122 |    -0.079 |           -4.839 |
| F2_ORB         | LONDON_30m_tp1R  |     1983 |         21.328 |       -0.114 | 0.765 | -5.611 |    -2.432 |    227.947 |   -0.113 |    -0.115 |           -5.451 |
| F2_ORB         | LONDON_30m_tp2R  |     1983 |         21.328 |       -0.118 | 0.780 | -4.810 |    -2.515 |    236.139 |   -0.114 |    -0.123 |           -5.756 |
| F2_ORB         | NY_30m_tp1R      |     1991 |         21.414 |       -0.127 | 0.753 | -6.090 |    -2.726 |    265.657 |   -0.161 |    -0.085 |           -4.593 |
| F2_ORB         | LONDON_30m_tpEOS |     1983 |         21.328 |       -0.134 | 0.756 | -4.999 |    -2.852 |    265.523 |   -0.125 |    -0.145 |           -6.194 |
| F2_ORB         | NY_15m_tp2R      |     2000 |         21.511 |       -0.137 | 0.792 | -4.809 |    -2.941 |    284.702 |   -0.164 |    -0.101 |           -5.480 |
| F2_ORB         | NY_15m_tp1R      |     2000 |         21.511 |       -0.155 | 0.725 | -7.095 |    -3.330 |    318.676 |   -0.175 |    -0.129 |           -5.446 |
| F3_RSI2        | s5_nofilt_both   |     3590 |         38.612 |       -0.087 | 0.756 | -6.851 |    -3.371 |    320.256 |   -0.074 |    -0.099 |           -6.590 |
| F2_ORB         | LONDON_15m_tp1R  |     1995 |         21.457 |       -0.212 | 0.641 | -9.772 |    -4.554 |    424.292 |   -0.219 |    -0.202 |           -8.060 |
| F2_ORB         | LONDON_15m_tp2R  |     1995 |         21.457 |       -0.216 | 0.679 | -7.964 |    -4.633 |    432.626 |   -0.206 |    -0.230 |           -8.664 |
| F2_ORB         | LONDON_15m_tpEOS |     1995 |         21.457 |       -0.236 | 0.661 | -7.263 |    -5.055 |    472.719 |   -0.237 |    -0.233 |           -8.972 |
| F3_RSI2        | s10_nofilt_both  |     5935 |         63.833 |       -0.089 | 0.746 | -9.233 |    -5.657 |    534.219 |   -0.071 |    -0.105 |          -10.856 |

Seuil « hasard » pour 46 variantes (+2 400 au cycle 3) : t ≈ 2.77 (≈ 3.96 en comptant tout l'historique de recherche).

## 2. Walk-forward par famille (hors échantillon 2022 → 2026-09)

### F1_DONCHIAN

|   test | choice                     |   test_trades |   test_R |   train_R_month |   test_R_month |
|-------:|:---------------------------|--------------:|---------:|----------------:|---------------:|
|   2022 | aucune variante admissible |             0 |     0    |          nan    |         nan    |
|   2023 | aucune variante admissible |             0 |     0    |          nan    |         nan    |
|   2024 | F1_DONCHIAN/tf240_N55_k3   |            25 |    -6.32 |            0.21 |          -0.53 |
|   2025 | F1_DONCHIAN/tf240_N55_k3   |            19 |    15.68 |            0.24 |           1.31 |
|   2026 | F1_DONCHIAN/tf240_N55_k2   |            16 |     0.76 |            0.61 |           0.08 |

### F2_ORB

|   test | choice                     |   test_trades |   test_R |
|-------:|:---------------------------|--------------:|---------:|
|   2022 | aucune variante admissible |             0 |        0 |
|   2023 | aucune variante admissible |             0 |        0 |
|   2024 | aucune variante admissible |             0 |        0 |
|   2025 | aucune variante admissible |             0 |        0 |
|   2026 | aucune variante admissible |             0 |        0 |

### F3_RSI2

|   test | choice                     |   test_trades |   test_R |
|-------:|:---------------------------|--------------:|---------:|
|   2022 | aucune variante admissible |             0 |        0 |
|   2023 | aucune variante admissible |             0 |        0 |
|   2024 | aucune variante admissible |             0 |        0 |
|   2025 | aucune variante admissible |             0 |        0 |
|   2026 | aucune variante admissible |             0 |        0 |

### F4_PULLBACK

|   test | choice                     |   test_trades |   test_R |   train_R_month |   test_R_month |
|-------:|:---------------------------|--------------:|---------:|----------------:|---------------:|
|   2022 | aucune variante admissible |             0 |        0 |          nan    |         nan    |
|   2023 | aucune variante admissible |             0 |        0 |          nan    |         nan    |
|   2024 | aucune variante admissible |             0 |        0 |          nan    |         nan    |
|   2025 | aucune variante admissible |             0 |        0 |          nan    |         nan    |
|   2026 | F4_PULLBACK/tp3R_long      |            40 |        2 |            0.75 |           0.22 |

### F5_COMPRESSION

|   test | choice                      |   test_trades |   test_R |   train_R_month |   test_R_month |
|-------:|:----------------------------|--------------:|---------:|----------------:|---------------:|
|   2022 | aucune variante admissible  |             0 |     0    |          nan    |         nan    |
|   2023 | F5_COMPRESSION/NR7_tp2R     |            31 |    -8.7  |            0.48 |          -0.73 |
|   2024 | F5_COMPRESSION/INSIDE_tp2R  |            40 |     4.74 |            0.21 |           0.39 |
|   2025 | F5_COMPRESSION/INSIDE_tp1R  |            37 |     5.33 |            0.19 |           0.44 |
|   2026 | F5_COMPRESSION/INSIDE_tpEOD |            23 |     3.47 |            0.3  |           0.39 |

### Synthèse walk-forward par famille

| family         |   trades |   trades_month |   expectancy |      pf |   R_month |   max_dd_r |
|:---------------|---------:|---------------:|-------------:|--------:|----------:|-----------:|
| F1_DONCHIAN    |       60 |          1.053 |        0.169 |   1.240 |     0.178 |     11.984 |
| F2_ORB         |        0 |          0.000 |      nan     | nan     |     0.000 |    nan     |
| F3_RSI2        |        0 |          0.000 |      nan     | nan     |     0.000 |    nan     |
| F4_PULLBACK    |       40 |          0.702 |        0.050 |   1.070 |     0.035 |      9.184 |
| F5_COMPRESSION |      131 |          2.299 |        0.037 |   1.114 |     0.085 |      9.843 |

## 3. Portefeuille : toutes les familles en même temps (walk-forward)

- R/mois moyen : **+0.30** ; médiane +0.00 ; mois positifs 20/57 ; meilleur +16.1 R, pire -6.6 R ; drawdown max 14.8 R.
- Mois atteignant 15 R : **1/57** ; mois ≥ 10 R : 1/57.

|                |   mean |   std |   min |   max |
|:---------------|-------:|------:|------:|------:|
| F1_DONCHIAN    |   0.18 |  2.85 | -4.26 | 16.49 |
| F4_PULLBACK    |   0.04 |  1.19 | -5.06 |  5.84 |
| F5_COMPRESSION |   0.08 |  1.27 | -3.05 |  3.45 |
| total          |   0.30 |  3.47 | -6.62 | 16.14 |
