# Rapport de tests (Phase 2 et 4)

## 1. Tests Python — `python3 -m pytest Tests/python -q`

**91 tests, 91 réussis.** Les résultats attendus sont calculés à la main (commentaires dans les tests) et
ont été écrits avant l'exécution.

| Fichier | Couverture |
|---|---|
| `test_indicators.py` | True Range, ATR (moyenne simple MT5), RSI (algorithme exact MT5, amorçage, pas de Wilder), règle RSI sur 5 bougies (égalité 70/30 incluse), données insuffisantes ⇒ blocage |
| `test_structure.py` | Pivots (égalités), fenêtre incomplète, confirmation différée, BOS par clôture, **mèche = sweep et non cassure**, CHoCH et modes de bascule, sweeps haut/bas, table de combinaison H4/H1, **invariance par troncature (absence de lookahead)** |
| `test_zones.py` | OTE achat/vente (exemples de référence 2000/2010), convention de retracement, FVG haussier/baissier, absence de FVG, taille minimale, OB (mèche/corps/fenêtre), intersection cas A/B/vide/contact, profondeur d'entrée 0/0,5/1, arrondi qui reste dans la zone, zone plus étroite qu'un tick, SL (3 ancrages, arrondi vers l'extérieur, spread des ventes), états des zones achat/vente |
| `test_risk.py` | Volume (exemple de référence 10 000 $ / 1 % / SL 5 $), commission, jamais d'arrondi supérieur, refus du lot minimal, plafonds, entrées invalides, sécurité flottante, volumes partiels (0,20 / 0,15 / 0,03 / lot minimal), repli `KEEP_ALL`, R initial, BE jamais élargi |
| `test_setups.py` | Scénario d'achat complet calculé à la main (BOS, impulsion, OTE, FVG, OB, cas B, entrée 100,48, SL 98,90, 1R 1,58), **miroir exact en vente**, spread du SL vente, profondeurs, invalidations (clôture au-delà, mèche vs clôture, échec profond, vente), contradiction H4/H1 ⇒ aucun setup, changement de biais ⇒ annulation, filtre RSI, ancrage `BOS_BAR`, « déjà touché avant placement », SL trop serré, **invariance par troncature du moteur complet** |
| `test_simulator.py` | Remplissage sur l'Ask, amélioration de prix sur gap, SL avec slippage, BE puis sortie au BE, partielle + TP 5R / 6R, ambiguïté intra-bougie pessimiste, bougie d'exécution, annulation avant exécution, jamais de poursuite, vente miroir (SL déclenché par l'Ask), runner A (cassure), runner D (stop suiveur qui ne recule jamais), runner B, commission et swap (mercredi triple) en R |

Incidents honnêtement consignés : lors de la première exécution, **2 tests sur 91 ont échoué à cause
d'erreurs dans les valeurs attendues que j'avais écrites** (un scénario de vente « doublement miroir »
et une lecture de la mauvaise bougie M1). Les attendus ont été corrigés après vérification manuelle ;
le code testé n'a pas été modifié pour ces deux cas.

## 2. Tests MQL5 dans le terminal MetaTrader 5 — `Tools/run_mql5_tests.sh`

Script `MQL5/Scripts/SensitorAI/SensitorTests.mq5` exécuté dans MT5 build 6283 (Wine).
**90 vérifications, 90 réussies** (`SensitorTests 0.1.0: 90 passed, 0 failed`).

| Groupe | Contenu |
|---|---|
| Indicateurs | ATR, RSI (y compris extension incrémentale barre par barre), règle 70/30 |
| Structure | pivots, BOS, sweep sur mèche, combinaison des biais |
| Zones | OTE, FVG, OB, intersection, profondeur, arrondi, SL, états |
| Risque | volume, partielle, R, SL jamais élargi |
| Annonces | fenêtre avant/après |
| Scénario | même scénario d'achat calculé à la main que les tests Python |
| **Parité** | 2 jeux de données aléatoires × 3 configurations (dont `BOS_BAR`, `GATE_PLACEMENT`, `CONTINUOUS`, `WICK`, `H4_LEADS`, `NEUTRAL_ON_CHOCH`, `BODY`, `OB_DISTAL`, `IMPULSE_ORIGIN`, buffers ATR) : **567 setups** produits par le moteur Python (`Research/scripts/gen_mql5_fixtures.py`) comparés champ par champ (identifiant, statut, raison de rejet, barres de confirmation/placement/invalidation, raison d'invalidation, OB, FVG, OTE, entrée, SL, 1R, cible de liquidité) : **identiques**. |

Incident consigné : la première exécution a révélé 4 échecs de parité dus uniquement à une
convention différente pour un champ non calculé (`tp_liquidity` = `NaN` en Python, `0` en MQL5 pour
les rejets précoces). La convention MQL5 a été alignée (`EMPTY_VALUE`).

## 3. Ce qui n'est pas couvert par ces tests

- Interaction réelle avec un serveur de trading (envoi, rejets, remplissages partiels, reconnexions) :
  à valider en démo.
- Concordance entre les barres du broker et celles de Dukascopy.
