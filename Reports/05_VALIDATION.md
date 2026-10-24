# Validation hors échantillon (VAL 2023-01 → 2024-06)

- Généré le 2026-10-24 11:39 UTC, code `cafc0a2`
- Données : Dukascopy XAUUSD M1 Bid/Ask, 2018-01-01 → 2024-07-19 (2,321,256 minutes)
- Coûts de base : {"contract_size": 100.0, "commission_per_lot_rt": 7.0, "stop_slippage": 0.1, "partial_slippage": 0.05, "swap_long_per_lot": -40.0, "swap_short_per_lot": -15.0, "triple_swap_weekday": 2, "extra_spread": 0.0}
- Périodes : {"WARMUP": ["2018-01-01", "2019-01-01"], "DEV": ["2019-01-01", "2023-01-01"], "VAL": ["2023-01-01", "2024-07-01"], "TEST": ["2024-07-01", "2026-10-01"]}
- Configuration gelée : `BASE` / `C_FIXED_5R` sélectionnée sur DEV (code d14a658)
- Variantes testées en amont : 70

> Résultats de simulation sur données historiques d'un fournisseur qui n'est pas le broker final. Ils ne constituent ni une preuve ni une promesse de rentabilité future.

## Résultat principal (C_FIXED_5R)

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|
|       43 |      0.209 |       2.279 |       -1.037 |         -0.343 |     -1.068 |   1.486 |   -1.515 |     -0.746 |       0.132 |         0.931 |             0.582 |   -14.755 |     16.649 |    3.955 |    -1.269 |


## Entonnoir

|   setups_evaluated |   rejected_at_confirmation |   missed_before_placement |   orders_placed |   missed_at_placement |   cancelled_unfilled |   filled |   fill_rate |   invalidated_share_of_placed |
|-------------------:|---------------------------:|--------------------------:|----------------:|----------------------:|---------------------:|---------:|------------:|------------------------------:|
|               1096 |                       1002 |                         9 |              85 |                     0 |                   42 |       43 |       0.506 |                         0.494 |


## Compte simulé (10 000 $, 1 %)

```
{
  "trades": 43,
  "rejected_by_limits": 0,
  "net_profit": -1344.3999999997968,
  "final_balance": 8655.600000000202,
  "profit_factor": 0.5829585005863323,
  "max_dd": 1509.2599999998401,
  "max_dd_pct": 14.8478188583004,
  "reject_reasons": {
    "PLACED": 85
  }
}
```

## Coûts « stress »

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|
|       43 |      0.233 |       2.132 |       -1.199 |         -0.424 |     -1.163 |   1.540 |   -1.806 |     -0.842 |       0.059 |         0.961 |             0.539 |   -18.238 |     20.265 |    3.914 |    -1.568 |


## Autres méthodes de runner (information, non utilisées pour décider)

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r | variant     | config   | period   |   placed |   fill_rate |   avg_cost_r |   avg_hold_h |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|:------------|:---------|:---------|---------:|------------:|-------------:|-------------:|
|       43 |      0.209 |       2.603 |       -1.037 |         -0.275 |     -1.068 |   1.629 |   -1.108 |     -0.711 |       0.240 |         0.865 |             0.664 |   -11.836 |     13.073 |    5.342 |    -1.269 | A_STRUCTURE | BASE     | VAL      |       85 |       0.506 |       -0.041 |        2.296 |
|       43 |      0.209 |       2.716 |       -1.037 |         -0.252 |     -1.068 |   1.657 |   -0.996 |     -0.698 |       0.262 |         0.841 |             0.693 |   -10.820 |     13.103 |    4.320 |    -1.269 | B_LIQUIDITY | BASE     | VAL      |       85 |       0.506 |       -0.041 |        2.099 |
|       43 |      0.209 |       2.279 |       -1.037 |         -0.343 |     -1.068 |   1.486 |   -1.515 |     -0.746 |       0.132 |         0.931 |             0.582 |   -14.755 |     16.649 |    3.955 |    -1.269 | C_FIXED_5R  | BASE     | VAL      |       85 |       0.506 |       -0.041 |        2.153 |
|       43 |      0.209 |       2.446 |       -1.037 |         -0.308 |     -1.068 |   1.591 |   -1.271 |     -0.734 |       0.202 |         0.894 |             0.624 |   -13.255 |     16.149 |    4.455 |    -1.269 | C_FIXED_6R  | BASE     | VAL      |       85 |       0.506 |       -0.041 |        2.163 |
|       43 |      0.209 |       2.669 |       -1.037 |         -0.261 |     -1.068 |   1.675 |   -1.023 |     -0.710 |       0.267 |         0.843 |             0.681 |   -11.244 |     12.765 |    5.817 |    -1.269 | D_TRAILING  | BASE     | VAL      |       85 |       0.506 |       -0.041 |        2.270 |


## Ventilations

**Par year**

|   year |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|-------:|---------:|-----------:|---------------:|----------:|-------:|
|   2023 |       28 |      0.250 |         -0.129 |    -3.598 |  0.830 |
|   2024 |       15 |      0.133 |         -0.744 |   -11.156 |  0.208 |


**Par session**

| session        |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| ASIA           |       16 |      0.188 |         -0.624 |    -9.983 |  0.302 |
| LATE           |        1 |      0.000 |         -1.081 |    -1.081 |  0.000 |
| LDN_NY_OVERLAP |       10 |      0.200 |         -0.124 |    -1.240 |  0.813 |
| LONDON         |       10 |      0.300 |          0.171 |     1.712 |  1.225 |
| NEW_YORK       |        6 |      0.167 |         -0.694 |    -4.162 |  0.261 |


**Par side**

| side   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------|---------:|-----------:|---------------:|----------:|-------:|
| BUY    |       24 |      0.167 |         -0.389 |    -9.329 |  0.536 |
| SELL   |       19 |      0.263 |         -0.286 |    -5.426 |  0.642 |


**Par vol_regime**

| vol_regime   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------------|---------:|-----------:|---------------:|----------:|-------:|
| LOW_VOL      |       15 |      0.067 |         -0.878 |   -13.167 |  0.098 |
| MID_VOL      |       14 |      0.214 |         -0.189 |    -2.648 |  0.779 |
| HIGH_VOL     |       14 |      0.357 |          0.076 |     1.061 |  1.122 |


**Par exit_reason**

| exit_reason   |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:--------------|---------:|-----------:|---------------:|----------:|--------:|
| BE            |        8 |      0.750 |          1.055 |     8.440 |  38.199 |
| SL            |       32 |      0.000 |         -1.095 |   -35.038 |   0.000 |
| TP            |        3 |      1.000 |          3.948 |    11.844 | inf     |


**Par s_entry_case**

| s_entry_case   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| A              |        2 |      0.000 |         -1.095 |    -2.191 |  0.000 |
| B              |       41 |      0.220 |         -0.306 |   -12.564 |  0.620 |


**Par mois** : 5 mois positifs / 16 ; meilleur 2.62R, pire -3.43R

**Coûts moyens** (R/trade) : commission -0.036, swap -0.005 ; spread moyen à l'exécution 0.351 $ ; 1R moyen 2.35 $ ; détention moyenne 2.2 h
