# Limites connues et hypothèses restantes

## 1. Stratégie
- La traduction algorithmique d'une méthode discrétionnaire (BOS, OB, FVG, sweeps) repose sur des
  définitions **proposées** (`Docs/ASSUMPTIONS.md`). Elles peuvent différer de la lecture visuelle de
  l'utilisateur ; une revue graphique de setups (dry-run, zones dessinées) est indispensable.
- Une seule définition de swing (fractal) est implémentée ; les variantes zigzag/ATR ne le sont pas.
- Le filtre RSI, l'UT d'entrée et la profondeur d'entrée sont des paramètres provisoires [C].
- La classification des sweeps (compatible / prudence) est une proposition non validée.

## 2. Données et simulation de recherche
- Données Dukascopy (Bid/Ask M1) ≠ données du broker final : spreads, ticks, horaires, fuseau serveur
  (donc bougies H4), gaps du week-end et coupures journalières peuvent différer.
- Résolution M1 : l'ordre des prix à l'intérieur d'une minute est inconnu. Le simulateur tranche
  systématiquement **contre** la stratégie (SL avant TP, pas de déclenchement dans la bougie
  d'exécution) — résultats potentiellement pessimistes sur les stops serrés.
- Le spread utilisé pour les décisions est celui de l'ouverture de la minute suivante ; l'EA utilise le
  spread du premier tick.
- Les ordres limites sont supposés exécutés au prix limite dès que l'Ask (achat) / le Bid (vente) l'atteint ;
  aucune file d'attente ni refus du broker n'est modélisé. Aucun remplissage partiel simulé.
- Les commissions et swaps sont des **hypothèses constantes** (7 $/lot, −40/−15 $/lot/nuit) : les swaps
  réels de l'or ont fortement varié avec les taux d'intérêt entre 2019 et 2026.
- La couche « portefeuille » utilise la balance (pas l'equity) comme base de risque, n'annule pas
  rétroactivement les ordres en attente lorsque la limite journalière est atteinte et ignore le P&L latent
  dans la limite journalière (l'EA, lui, les prend en compte).
- Le filtre d'annonces n'est pas backtesté (pas d'historique de calendrier ; indisponible dans le
  Strategy Tester).

## 3. Statistique
- Le nombre de trades par an est faible (quelques dizaines) : les intervalles de confiance sont larges et
  la puissance statistique limitée. Un résultat positif sur quelques dizaines de trades peut être dû au
  hasard.
- 70 variantes ont été évaluées sur DEV : le meilleur résultat est biaisé à la hausse (biais de sélection).
- Le régime de marché de la période de test (2024–2026, forte hausse et volatilité de l'or) diffère de
  celui de la période de développement.
- Un backtest positif ne prouve pas une rentabilité future.

## 4. Exécution (EA)
- Le risque de 1 % est **nominal** : gaps (ouverture du dimanche, annonces), slippage et exécution
  dégradée peuvent produire des pertes supérieures.
- Un stop au break-even ne garantit pas un résultat nul (commission, swap, slippage).
- BE, partielle, sortie A et stop suiveur D dépendent du terminal : en cas de coupure, seuls SL/TP serveur
  protègent la position.
- Au redémarrage, la reconstruction de l'état dépend de l'historique accessible ; si l'historique est
  incomplet et que le fichier d'état est perdu, le SL initial peut être inconnu ⇒ `ERROR_SAFE`.
- Le rejeu de warm-up utilise le spread courant pour les barres passées : pour un setup de vente formé
  pendant une coupure, le SL recalculé peut différer légèrement de celui envoyé à l'origine (l'ordre déjà
  présent chez le broker fait foi).
- Compte netting : une seule position/ordre à la fois (simplification volontaire).
- Le Strategy Tester n'a pas pu être exécuté dans l'environnement de développement (compte requis) : la
  couche d'exécution (envoi, remplissage, modifications) n'est validée que par revue de code et doit
  l'être en démo.

## 5. IA (phase 9)
- Non activée. Un filtre d'apprentissage automatique n'a de sens que si la stratégie de base montre un
  avantage hors échantillon ; sinon il risque surtout de sur-apprendre le bruit (`Research/scripts/ml_filter.py`).
