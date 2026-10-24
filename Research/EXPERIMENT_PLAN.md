# Sensitor AI — Plan d'expérience pré-enregistré (v1)

> Rédigé et commité **avant** l'exécution de tout backtest sur données réelles.
> Toute déviation ultérieure à ce plan doit être signalée comme telle dans les rapports.

## 1. Données

| Élément | Valeur |
|---|---|
| Source | Dukascopy, XAU/USD, bougies **M1 Bid et Ask** (spread réel minute par minute) |
| Couverture téléchargée | 2018-01-01 → 2026-09-30 |
| Préchauffage moteur | 2018 (aucun trade compté) |
| Heure serveur simulée | UTC+2 / UTC+3 (heure d'été US), convention « New York close » |
| Limite connue | Le flux Dukascopy n'est **pas** celui du broker final (spreads, ticks, horaires, barres H4 différents). |

## 2. Découpage chronologique (aucun mélange)

| Période | Dates (par date d'exécution du trade) | Usage |
|---|---|---|
| **DEV** — développement | 2019-01-01 → 2022-12-31 | Comparaisons de variantes, choix des paramètres |
| **VAL** — validation | 2023-01-01 → 2024-06-30 | Vérification de la sélection faite sur DEV ; aucun nouveau réglage n'est autorisé après lecture des résultats VAL, sauf à déclarer un nouveau cycle |
| **TEST** — final | 2024-07-01 → 2026-09-30 | **Exécuté une seule fois** avec la configuration gelée ; résultat rapporté quel qu'il soit |

Le moteur de signaux est causal (testé : invariance par troncature), il peut donc être exécuté sur toute la
période ; seuls les trades sont répartis par période. Aucun paramètre n'est estimé sur VAL ou TEST.

## 3. Coûts (identiques pour toutes les variantes)

| Coût | Hypothèse de base | Stress |
|---|---|---|
| Spread | Réel Dukascopy (Bid/Ask M1) | + 0,20 $ par transaction |
| Commission | 7 $ / lot aller-retour | 10,5 $ |
| Slippage sur stop / sortie marché | 0,10 $ | 0,30 $ |
| Slippage sur prise partielle locale | 0,05 $ | 0,15 $ |
| Swap long / court | −40 $ / −15 $ par lot et par nuit, ×3 le mercredi | ×2 |
| Ordres limites | exécutés uniquement si l'Ask (achat) / le Bid (vente) atteint le prix ; ambiguïtés intra-minute tranchées **contre** la stratégie | — |

## 4. Configuration de référence (baseline)

Valeurs par défaut de `Research/sensitor/config.py` / `MQL5/Include/SensitorAI/Config.mqh` :
UT d'entrée M15, swings 3/3 (H1/H4) et 2/2 (entrée), biais H4+H1 requis, RSI `AT_SETUP` sur l'UT
d'entrée, entrée au milieu de la zone OB∩OTE (0,5), SL structurel + 0,10 ATR, BE +1R, 50 % à +3R,
runner `FIXED_R` 5R, risque 1 %.

## 5. Expériences (sur DEV uniquement)

| ID | Question | Variantes |
|---|---|---|
| E1 | Entonnoir des signaux de la baseline, distribution des R | 1 |
| E2 | Méthodes de runner sur **les mêmes signaux** | A `STRUCTURE`, B `LIQUIDITY`, C 5R, C 6R, D `TRAILING` (5) |
| E3 | Apport du filtre RSI | `OFF`, `AT_SETUP`, `GATE_PLACEMENT`, `CONTINUOUS` (4) |
| E4 | Niveau d'entrée dans la zone | profondeur 0 ; 0,5 ; 1 (3) |
| E5 | UT d'entrée | M15 ; M5 (2) |
| E6 | Sensibilité (un facteur à la fois) | sweeps `LOG_ONLY` ; invalidation `WICK` ; biais `H4_LEADS` ; `NEUTRAL_ON_CHOCH` ; impulsion `BOS_BAR` ; swings d'entrée 3/3 ; buffer SL 0,25 ATR (7) |

Nombre de configurations de signaux : 1 + 3 + 2 + 1 + 7 = **14**, chacune croisée avec les 5 méthodes de
runner ⇒ **70 variantes** au plus. Ce nombre est reporté dans tous les rapports.

## 6. Règle de sélection (fixée à l'avance)

1. Métrique principale : **espérance nette par trade en R** (coûts inclus) sur DEV.
2. Contraintes : ≥ 100 trades sur DEV ; profit factor (R) ≥ 1,10 ; résultat non dépendant d'un seul
   trade (espérance hors meilleur trade > 0).
3. Une variante ne remplace la baseline que si son avantage est **cohérent par année** (positif ≥ 3 des
   4 années de DEV) et que l'intervalle de confiance bootstrap de la différence appariée (mêmes signaux)
   exclut 0 pour les variantes de runner ; sinon la variante la plus simple / la baseline est conservée.
4. Le profit total et la plus belle courbe ne sont **pas** des critères.
5. La sélection est appliquée telle quelle à VAL. Si l'espérance VAL est ≤ 0, la conclusion est
   « pas d'avantage démontré » ; il n'y a pas de second essai sur VAL.

## 7. Walk-forward (complément)

Ancré, annuel, 2020 → 2024 : pour chaque année Y, la combinaison {méthode de runner × profondeur
d'entrée} (15 combinaisons) ayant la meilleure espérance sur [2019, Y−1] est appliquée à Y. Les résultats
hors échantillon concaténés mesurent la valeur de la procédure de sélection elle-même.

## 8. Incertitude et comparaisons multiples

- IC bootstrap à 95 % de l'espérance, statistique t, P(espérance ≤ 0).
- Avec N variantes, le meilleur t attendu **par pur hasard** est d'environ √(2 ln N) (≈ 2,9 pour N = 70).
  Un résultat DEV n'est considéré comme une indication sérieuse que si t dépasse ce seuil ; sinon il est
  qualifié de « compatible avec le hasard ».

## 9. Critères avant démo / réel (aucun passage automatique)

Démo envisageable seulement si : espérance > 0 sur VAL **et** TEST, profit factor > 1,1, résultat
positif sous le scénario de coûts « stress », drawdown compatible avec la tolérance de l'utilisateur.
Sinon : poursuite de la recherche, pas de démo à visée de validation de rentabilité (une démo technique
de l'EA reste utile pour valider l'exécution).

---

## Cycle 2 — règle Order Block confirmée par l'utilisateur (enregistré avant exécution)

Retour de l'utilisateur après revue des graphiques (2026-10-24) :
- BOS confirmé par **clôture du corps** au-delà du swing : conforme à l'implémentation ([U] confirmé).
- OTE 62–79 % : conforme ([U] confirmé).
- **Nouvelle règle [U]** : l'Order Block doit créer le FVG **immédiatement** — la bougie OB est la première
  des trois bougies du FVG (OB → bougie d'impulsion → bougie suivante, gap entre l'extrême de l'OB et la
  3ᵉ bougie). Implémentation : `ObMaxDistBars = 0`. Tous les autres paramètres sont inchangés.

Protocole :
- Une seule configuration nouvelle (baseline + `ObMaxDistBars = 0`), runner principal C 5R ; les 5 runners
  sont rapportés à titre d'information.
- Évaluée **une seule fois** sur DEV, VAL et TEST, résultats rapportés tels quels.
- **Limite** : les données 2019-2026 ont déjà été vues au cycle 1. Ce cycle n'est donc pas une
  validation indépendante ; il mesure l'effet d'une règle fournie par l'utilisateur (non choisie sur les
  données). Une validation indépendante exigera des données nouvelles (forward / démo).
- Nombre cumulé de variantes évaluées : 70 (cycle 1) + 5 (cycle 2) = 75.

---

## Cycle 3 — recherche de paramètres demandée par l'utilisateur (enregistré avant exécution)

Demande : « trouve le réglage le plus rentable » ; objectif exprimé : 10–15 R par mois.

Espace de recherche (règles [U] conservées : BOS par clôture du corps, OTE 62–79 %, OB qui crée le FVG,
ordre limite, RSI comme filtre d'exclusion ou absent pour comparaison) — **400 configurations tirées au
hasard** (graine fixe 2026) parmi :
UT d'entrée {M15, M5} ; swings d'entrée {2, 3, 5} ; swings H1/H4 {2, 3, 5} ; mode après CHoCH
{FLIP, NEUTRAL} ; sweeps opposés {BLOCK, LOG_ONLY} ; RSI {OFF, AT_SETUP sur UT d'entrée, AT_SETUP sur H1,
GATE sur UT d'entrée} ; profondeur d'entrée {0 ; 0,5 ; 1} ; invalidation {CLOSE, WICK} ; impulsion
{SWING_CONFIRM, BOS_BAR} ; buffer SL {0,1 ; 0,3 ATR} ; taille minimale du FVG {0 ; 0,3 ; 0,6 ATR} ;
« déjà touché » {rejet, accepté}.

Gestion (6 variantes, toutes simulées sur les mêmes signaux) :
M0 BE +1R, 50 % à +3R, TP 5R (**règles de l'utilisateur**) ; M1 sans BE, 50 % à +3R, TP 5R ;
M2 BE +2R, 50 % à +3R, TP 5R ; M3 sans BE ni partielle, TP 3R ; M4 sans BE ni partielle, TP 2R ;
M5 BE +1R, sans partielle, TP 3R. M1–M5 **dérogent** aux règles de l'utilisateur et sont signalées comme telles.

Total : 2 400 variantes. Coûts de base du plan v1. R calculés par trade (sans limites de portefeuille).

Mesure principale (honnête) : **walk-forward glissant** — fenêtre d'entraînement de 3 ans, test sur l'année
suivante : 2022, 2023, 2024, 2025, 2026 (jan–sept). Sur chaque fenêtre d'entraînement on retient la
variante maximisant le R net total sous contraintes (≥ 30 trades, PF ≥ 1,1) ; on l'applique à l'année de
test. Le R/mois **hors échantillon** concaténé est le chiffre de référence. Variante secondaire du critère
(rapportée aussi) : maximiser la statistique t.

Rapporté également, avec avertissement : la meilleure variante sur l'ensemble 2019-2026 (in-sample,
biaisée à la hausse) et l'écart entre in-sample et walk-forward.
