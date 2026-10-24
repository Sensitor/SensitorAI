# Sensitor AI — Bilan honnête (v0.1.0)

## 1. En une phrase

Le système complet (spécification, EA MQL5 compilé et testé, référence Python, simulateur Bid/Ask,
protocole de validation) est construit et vérifié ; **avec les définitions provisoires actuelles, la
stratégie ne montre aucun avantage statistique** : légèrement négative en développement, négative en
validation hors échantillon, et négative également sur le test final jamais utilisé pour régler. **Aucun passage en réel n'est justifié.**

## 2. Résultats (coûts inclus, runner C 5R, configuration de référence)

| Période | Trades | Taux de réussite | Espérance nette | IC 95 % | Profit factor | Compte 10 000 $ (1 %) |
|---|---|---|---|---|---|---|
| DEV 2019-2022 | 84 | 15,5 % | −0,090 R | [−0,43 ; +0,29] | 0,87 | −789 $, DD max 13,6 % |
| VAL 2023-01 → 2024-06 | 43 | 20,9 % | −0,343 R | [−0,75 ; +0,13] | 0,58 | −1 344 $, DD max 14,8 % |
| TEST 2024-07 → 2026-09 (exécuté une fois) | 59 | 18,6 % | −0,089 R | [−0,40 ; +0,23] | 0,82 | −578 $, DD max 13,7 % |

- 70 variantes évaluées sur DEV (14 configurations de signaux × 5 runners) : meilleur t = 0,33, très en
  dessous du seuil de hasard √(2 ln 70) ≈ 2,9. Aucune variante ne satisfait les critères pré-enregistrés.
- **Méthodes de runner** (mêmes signaux) : A −0,15R, B −0,13R, C5 −0,09R, C6 −0,13R, D −0,13R ; toutes les
  différences appariées ont un IC contenant 0 → **indiscernables** (elles ne diffèrent que sur ~15 % des
  trades, ceux qui atteignent +3R). Le choix ne doit pas se faire sur ces chiffres.
- **Filtre RSI** : sans RSI −0,17R (122 trades) ; `AT_SETUP` −0,09R (84) ; `GATE`/`CONTINUOUS` −0,12R (107).
  Le filtre réduit les pertes mais pas de manière statistiquement établie.
- **M5 vs M15** : M5 −0,40R sur 198 trades (t ≈ −4,3) : seul résultat statistiquement net, et **négatif**.
- **Coûts** : à coût nul la baseline DEV est à +0,006R ; les coûts de base la font passer à −0,09R et le
  scénario stress à −0,37R. La stratégie est **très sensible aux coûts**.
- Walk-forward (choix annuel runner × profondeur d'entrée) : −0,01R sur 89 trades hors échantillon.
- TEST, coûts stress : −0,24R. TEST, autres runners (information seulement, non sélectionnés) : A +0,07R,
  B −0,03R, C6 −0,06R, D −0,03R — tous compatibles avec le hasard (|t| < 0,4) ; les classements entre
  méthodes changent d'une période à l'autre (C5 était le moins mauvais sur DEV, A l'est sur TEST), ce qui
  confirme qu'aucune méthode de runner ne se distingue.

## 3. Pourquoi (diagnostic descriptif, non utilisé pour régler)

1. **Échelle de la structure et coûts** : sur DEV, avec des swings 2/2 en M15, le 1R médian est de
   **1,89 $** alors que vos SL manuels sont de l'ordre de 5 à 8 $, et le spread représente en moyenne
   **19 % du risque**. Certains BOS portent sur des swings très mineurs (cf. `Reports/figures/`).
   Cependant, sur TEST (or plus cher et plus volatil), le 1R médian atteint **4,38 $** (spread ≈ 15 % du
   risque) et le résultat reste négatif : l'échelle n'explique donc pas tout.
2. **Gestion** : 42 % des trades atteignent +1R mais seulement 15,5 % atteignent +3R ; 22 des 35 trades
   passés par +1R reviennent au BE avant +3R. Le gain dépend presque entièrement des ~15 % de trades à 5R.
3. **Peu de trades** (~20/an) : intervalles de confiance larges ; même un vrai petit avantage serait
   difficile à démontrer.

## 4. Livrables

| # | Livrable | Statut |
|---|---|---|
| 1 | Code source de l'EA | ✅ `MQL5/Experts/SensitorAI/SensitorAI.mq5` — compilé, 0 erreur |
| 2 | Fichiers `.mqh` | ✅ 13 modules `MQL5/Include/SensitorAI/` |
| 3 | Configuration documentée | ✅ inputs commentés [U]/[H]/[C], `Docs/SPECIFICATION.md`, `Docs/ASSUMPTIONS.md`, presets `.set` |
| 4 | Scripts Python d'analyse et de backtest | ✅ `Research/` (pipeline, expériences, analyse des journaux de l'EA, export MT5, graphiques) |
| 5 | Tests unitaires et données synthétiques | ✅ 97 tests Python + 90 vérifications MQL5 exécutées dans MT5 (dont parité de 567 setups) |
| 6 | Document de stratégie | ✅ `Docs/SPECIFICATION.md` |
| 7 | Rapport de compilation | ✅ `Reports/01_COMPILATION.md` (+ `Reports/compile/*.log`) |
| 8 | Rapport de backtest | ✅ `Reports/03_BACKTEST_DEV.md` (simulateur de recherche Python) |
| 9 | Comparaison des 4 méthodes de runner | ✅ `Reports/04_RUNNER_COMPARISON.md` |
| 10 | Validation hors échantillon | ✅ `Reports/05_VALIDATION.md`, `Reports/06_FINAL_TEST.md`, walk-forward dans le rapport DEV |
| 11 | Guide d'installation MT5 | ✅ `Docs/INSTALL_MT5.md` |
| 12 | Guide VPS | ✅ `Docs/VPS_DEPLOYMENT.md` + `Tools/watchdog.ps1` |
| 13 | Procédure démo | ✅ `Docs/DEMO_PROCEDURE.md` |
| 14 | Checklist avant réel | ✅ `Docs/LIVE_CHECKLIST.md` |
| 15 | Limites et hypothèses | ✅ `Docs/LIMITATIONS.md`, `Docs/ASSUMPTIONS.md` |
| — | Filtre IA (phase 9) | ⛔ volontairement non exécuté : verrou `Research/scripts/ml_filter.py` fermé (pas d'avantage validé) |
| — | Dashboard | ✅ panneau informatif sur le graphique (n'intervient pas dans le risque) |

## 5. Testé / non testé

| Élément | Statut |
|---|---|
| Moteur de signaux MQL5 (structure, BOS, sweeps, OB, FVG, OTE, entrée, SL, RSI, invalidations) | **Testé** dans MT5, identique à la référence Python sur 567 setups |
| Calculs de volume, partielle, R, BE (fonctions pures) | **Testés** (Python et MQL5) |
| Envoi/modification/annulation d'ordres, remplissages, reconnexion, redémarrage | **Non testé contre un serveur** : relu, compilé, mais le Strategy Tester exige un compte. À valider en démo. |
| Backtests | Simulateur Python M1 Bid/Ask Dukascopy (pessimiste intra-minute) ; **pas** de backtest de l'EA dans le Strategy Tester ni sur ticks réels du broker |
| Filtre d'annonces | Logique de fenêtre testée ; effet non backtesté |

## 6. Transparence sur le déroulement

- Trois tests ont initialement échoué à cause d'**erreurs dans mes valeurs attendues**, pas du code ;
  ils ont été corrigés après vérification (`Reports/02_TESTS.md`).
- La parité MQL5/Python a révélé une différence de convention (champ non calculé) ; corrigée.
- Une revue de code a révélé un vrai défaut de robustesse au redémarrage (spread courant utilisé pour
  rejouer l'historique ⇒ annulation possible d'ordres légitimes) ; corrigé avant tout backtest.
- Deux décisions de spécification prises avant les backtests et consignées dans `Docs/CHANGELOG.md`.
- Le walk-forward pré-enregistré (2020 → 2024) déborde sur 2023 (période VAL) : il affiche donc une
  statistique VAL d'une variante. La sélection étant déjà mécanique, aucune décision n'en a dépendu.
- `BIAS_H4_LEADS` donne exactement les mêmes résultats que la baseline : en mode `FLIP_ON_CHOCH`, une UT
  n'est jamais neutre après sa première cassure, donc les deux règles coïncident (ce n'est pas un bug).
- Le test final a été exécuté **une seule fois** (verrou `Reports/.test_stage_done`).

## 7. Recommandations (décisions qui vous appartiennent)

1. **Ne pas trader cette version en réel.** Une démo **technique** (dry-run puis ordres) reste utile pour
   valider l'exécution (`Docs/DEMO_PROCEDURE.md`).
2. **Revue visuelle** des setups (`Reports/figures/`, mode dry-run + zones dessinées) pour confirmer ou
   corriger les définitions, en priorité : UT d'entrée, taille des swings structurels, UT du RSI, niveau
   d'entrée dans la zone, réaction aux sweeps (`Docs/ASSUMPTIONS.md`, section C).
3. Avec vos réponses, lancer un **nouveau cycle pré-enregistré**. Les données 2019-2026 ayant déjà été
   vues, ce cycle devra être jugé d'abord sur des données nouvelles (démo/forward ou période non encore
   utilisée) pour éviter le surapprentissage.
4. Si un avantage apparaît un jour, revalider sur les **ticks réels du broker** dans le Strategy Tester
   avant toute démo à visée de performance, puis seulement envisager la phase IA.
