# Test final sur données jamais utilisées (TEST 2024-07 → 2026-09)

- Généré le 2026-10-24 13:05 UTC, code `1d9eef6`
- Données : Dukascopy XAUUSD M1 Bid/Ask, 2018-01-01 → 2026-09-30 (3,100,386 minutes)
- Coûts de base : {"contract_size": 100.0, "commission_per_lot_rt": 7.0, "stop_slippage": 0.1, "partial_slippage": 0.05, "swap_long_per_lot": -40.0, "swap_short_per_lot": -15.0, "triple_swap_weekday": 2, "extra_spread": 0.0}
- Périodes : {"WARMUP": ["2018-01-01", "2019-01-01"], "DEV": ["2019-01-01", "2023-01-01"], "VAL": ["2023-01-01", "2024-07-01"], "TEST": ["2024-07-01", "2026-10-01"]}
- Configuration gelée : `BASE` / `C_FIXED_5R` sélectionnée sur DEV (code d14a658)
- Variantes testées en amont : 70

> Résultats de simulation sur données historiques d'un fournisseur qui n'est pas le broker final. Ils ne constituent ni une preuve ni une promesse de rentabilité future.

## Résultat principal (C_FIXED_5R)

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|
|       59 |      0.186 |       2.120 |       -0.595 |         -0.089 |     -0.097 |   1.257 |   -0.545 |     -0.398 |       0.234 |         0.717 |             0.816 |    -5.258 |     15.136 |    3.987 |    -1.181 |


## Entonnoir

|   setups_evaluated |   rejected_at_confirmation |   missed_before_placement |   orders_placed |   missed_at_placement |   cancelled_unfilled |   filled |   fill_rate |   invalidated_share_of_placed |
|-------------------:|---------------------------:|--------------------------:|----------------:|----------------------:|---------------------:|---------:|------------:|------------------------------:|
|               1662 |                       1503 |                        11 |             148 |                     0 |                   89 |       59 |       0.399 |                         0.601 |


## Compte simulé (10 000 $, 1 %)

```
{
  "trades": 59,
  "rejected_by_limits": 0,
  "net_profit": -578.2460000000485,
  "final_balance": 9421.753999999952,
  "profit_factor": 0.7709377968519916,
  "max_dd": 1370.399999999956,
  "max_dd_pct": 13.70399999999956,
  "reject_reasons": {
    "PLACED": 148
  }
}
```

## Coûts « stress »

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|
|       58 |      0.155 |       2.201 |       -0.687 |         -0.239 |     -0.332 |   1.253 |   -1.451 |     -0.544 |       0.096 |         0.924 |             0.589 |   -13.844 |     22.376 |    3.975 |    -1.383 |


## Autres méthodes de runner (information, non utilisées pour décider)

|   trades |   win_rate |   avg_win_r |   avg_loss_r |   expectancy_r |   median_r |   std_r |   t_stat |   ci95_low |   ci95_high |   p_mean_le_0 |   profit_factor_r |   total_r |   max_dd_r |   best_r |   worst_r | variant     | config   | period   |   placed |   fill_rate |   avg_cost_r |   avg_hold_h |
|---------:|-----------:|------------:|-------------:|---------------:|-----------:|--------:|---------:|-----------:|------------:|--------------:|------------------:|----------:|-----------:|---------:|----------:|:------------|:---------|:---------|---------:|------------:|-------------:|-------------:|
|       59 |      0.186 |       2.986 |       -0.595 |          0.072 |     -0.097 |   1.836 |    0.303 |     -0.347 |       0.563 |         0.394 |             1.150 |     4.274 |     14.650 |    8.801 |    -1.181 | A_STRUCTURE | BASE     | TEST     |      148 |       0.399 |       -0.039 |        6.306 |
|       59 |      0.186 |       2.431 |       -0.595 |         -0.031 |     -0.097 |   1.425 |   -0.167 |     -0.378 |       0.336 |         0.581 |             0.936 |    -1.831 |     15.136 |    5.985 |    -1.181 | B_LIQUIDITY | BASE     | TEST     |      148 |       0.399 |       -0.038 |        5.475 |
|       59 |      0.186 |       2.120 |       -0.595 |         -0.089 |     -0.097 |   1.257 |   -0.545 |     -0.398 |       0.234 |         0.717 |             0.816 |    -5.258 |     15.136 |    3.987 |    -1.181 | C_FIXED_5R  | BASE     | TEST     |      148 |       0.399 |       -0.039 |        5.394 |
|       59 |      0.186 |       2.256 |       -0.595 |         -0.064 |     -0.097 |   1.343 |   -0.364 |     -0.390 |       0.282 |         0.656 |             0.868 |    -3.758 |     15.136 |    4.487 |    -1.181 | C_FIXED_6R  | BASE     | TEST     |      148 |       0.399 |       -0.039 |        5.402 |
|       59 |      0.186 |       2.437 |       -0.595 |         -0.030 |     -0.097 |   1.411 |   -0.164 |     -0.375 |       0.335 |         0.578 |             0.938 |    -1.772 |     13.813 |    6.112 |    -1.181 | D_TRAILING  | BASE     | TEST     |      148 |       0.399 |       -0.038 |        5.573 |


## Ventilations

**Par year**

|   year |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|-------:|---------:|-----------:|---------------:|----------:|-------:|
|   2024 |       16 |      0.062 |         -0.517 |    -8.268 |  0.148 |
|   2025 |       28 |      0.214 |         -0.061 |    -1.696 |  0.870 |
|   2026 |       15 |      0.267 |          0.314 |     4.706 |  1.806 |


**Par session**

| session        |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| ASIA           |       15 |      0.200 |         -0.214 |    -3.214 |  0.578 |
| LATE           |        6 |      0.000 |         -0.637 |    -3.824 |  0.000 |
| LDN_NY_OVERLAP |       11 |      0.364 |          0.052 |     0.569 |  1.108 |
| LONDON         |       16 |      0.062 |         -0.298 |    -4.774 |  0.455 |
| NEW_YORK       |       11 |      0.273 |          0.544 |     5.985 |  2.921 |


**Par side**

| side   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------|---------:|-----------:|---------------:|----------:|-------:|
| BUY    |       37 |      0.162 |         -0.255 |    -9.442 |  0.537 |
| SELL   |       22 |      0.227 |          0.190 |     4.184 |  1.511 |


**Par vol_regime**

| vol_regime   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:-------------|---------:|-----------:|---------------:|----------:|-------:|
| LOW_VOL      |       20 |      0.100 |         -0.436 |    -8.718 |  0.249 |
| MID_VOL      |       19 |      0.158 |         -0.343 |    -6.508 |  0.384 |
| HIGH_VOL     |       20 |      0.300 |          0.498 |     9.968 |  2.557 |


**Par exit_reason**

| exit_reason    |   trades |   win_rate |   expectancy_r |   total_r |    pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|--------:|
| BE             |       30 |      0.267 |          0.322 |     9.658 |   6.605 |
| GAP_THROUGH_SL |        1 |      0.000 |         -0.546 |    -0.546 |   0.000 |
| SL             |       25 |      0.000 |         -1.052 |   -26.307 |   0.000 |
| TP             |        3 |      1.000 |          3.979 |    11.936 | inf     |


**Par s_entry_case**

| s_entry_case   |   trades |   win_rate |   expectancy_r |   total_r |   pf_r |
|:---------------|---------:|-----------:|---------------:|----------:|-------:|
| B              |       59 |      0.186 |         -0.089 |    -5.258 |  0.816 |


**Par mois** : 10 mois positifs / 25 ; meilleur 3.99R, pire -4.29R

**Coûts moyens** (R/trade) : commission -0.018, swap -0.020 ; spread moyen à l'exécution 0.626 $ ; 1R moyen 5.19 $ ; détention moyenne 5.4 h
