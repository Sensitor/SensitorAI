# Tester Sensitor AI soi-même — guide pas à pas

Trois façons de tester, de la plus rapide à la plus réaliste. **Commencez par l'étape 1 (backtest)**, puis
2 (observation sans ordre), puis 3 (démo avec ordres). Aucune ne met d'argent réel en jeu.

## 0. Préparer MetaTrader 5 (10 minutes, une seule fois)

1. Ouvrez un **compte démo** chez votre broker (ou chez la prop firm visée si elle fournit un MT5 démo).
   Utilisez le même type de compte que celui que vous viserez plus tard (hedging de préférence).
2. Dézippez `SensitorAI_MT5_v0.2.0.zip`.
3. Dans MT5 : **Fichier → Ouvrir le dossier des données**. Copiez le dossier `MQL5` du zip **dans** ce
   dossier (fusionner avec le dossier `MQL5` existant). Vous obtenez :
   - `MQL5\Experts\SensitorAI\SensitorAI.ex5` (l'EA, déjà compilé)
   - `MQL5\Include\SensitorAI\...` (le code source)
   - `MQL5\Scripts\SensitorAI\SensitorTests.ex5` (les tests)
   - `MQL5\Presets\SensitorAI_*.set` (réglages prêts)
4. Redémarrez MT5 (ou clic droit sur *Navigateur → Actualiser*).
5. **Contrôle** : faites glisser le script `SensitorTests` sur n'importe quel graphique. Onglet *Experts*
   (en bas) : vous devez lire `SensitorTests 0.2.0: 90 passed, 0 failed`. Sinon, arrêtez-vous et
   envoyez-moi le message.
6. Si `SensitorAI.ex5` n'apparaît pas ou ne se charge pas (version de MT5 différente) : ouvrez
   `MQL5\Experts\SensitorAI\SensitorAI.mq5` dans MetaEditor (F4) et appuyez sur **F7 (Compiler)**.

## 1. Backtest dans le testeur de stratégie (le plus utile pour commencer)

1. **Affichage → Testeur de stratégie** (Ctrl+R).
2. Réglages :
   | Champ | Valeur |
   |---|---|
   | Expert | `SensitorAI\SensitorAI` |
   | Symbole | l'or de votre broker (`XAUUSD`, `GOLD`, `XAUUSD.m`, …) |
   | Période | **M15** |
   | Dates | par exemple 2023.01.01 → aujourd'hui |
   | Modélisation | **Chaque tick basé sur les ticks réels** (le plus réaliste) |
   | Dépôt / devise / levier | ceux de votre futur compte (ex. 10 000 USD, 1:100) |
3. Onglet **Paramètres** → clic droit → **Charger** → `SensitorAI_tester.set`.
   Si votre broker facture une commission, renseignez `InpCommissionPerLot` (aller-retour par lot).
4. **Démarrer**. Le premier lancement télécharge l'historique de ticks (cela peut prendre du temps).
5. Lisez l'onglet **Backtest** : bénéfice net, facteur de profit, drawdown, nombre de trades.
   Onglet **Graphique** : la courbe. Activez *Mode visuel* pour voir les zones dessinées (OTE bleu, OB
   vert/rouge, FVG doré, entrée blanche, SL rouge pointillé).
6. **Journaux détaillés** : `C:\Users\<vous>\AppData\Roaming\MetaQuotes\Terminal\Common\Files\SensitorAI\`
   (fichiers `XAUUSD_20250101_trades.csv`, `_setups.csv`, `_decisions.csv`, `_events.csv`, `_orders.csv`,
   `_errors.csv`). Envoyez-les-moi : je compare chaque setup avec la référence Python et je vérifie
   l'exécution (c'est la validation qui n'a pas pu être faite sans compte).

Comparer les méthodes de runner : relancez avec `SensitorAI_runner_A_structure.set`, `_B_liquidity`,
`_C_5R`, `_C_6R`, `_D_trailing` (mêmes dates, même modèle).

> Important : le backtest sur les ticks de **votre** broker est différent de mes tests (données
> Dukascopy). Les deux doivent aller dans le même sens avant de conclure quoi que ce soit.

## 2. Observation en temps réel sans ordre (dry-run, 1 à 2 semaines)

1. Ouvrez un graphique de l'or (n'importe quelle UT). Faites glisser `SensitorAI`.
2. Onglet *Commun* : cochez *Autoriser le trading algorithmique*. Onglet *Paramètres* : **Charger →
   `SensitorAI_dryrun.set`**.
3. Le bouton **Trading algo** de la barre d'outils doit être vert.
4. Le panneau en haut à gauche affiche l'état, le biais H4/H1, les setups. En dry-run, **aucun ordre
   n'est envoyé** : les setups et les ordres « qui auraient été placés » sont écrits dans les journaux.
5. Comparez avec votre propre lecture du graphique : les BOS, OB et zones correspondent-ils ?

## 3. Démo avec ordres réels (4 semaines minimum)

1. Même procédure, mais chargez **`SensitorAI_demo.set`**.
2. Laissez MT5 tourner en continu (idéalement sur un VPS : `Docs/VPS_DEPLOYMENT.md`) : le passage au
   break-even et la prise partielle à +3R sont gérés par l'EA, le SL et le TP sont chez le broker.
3. Cochez la liste de `Docs/DEMO_PROCEDURE.md` (ordres conformes, pas de doublon, BE, partielle,
   redémarrage du terminal, coupure réseau…).

## 4. Si vous visez une prop firm

- Vérifiez dans **leurs règles** : EA autorisés, trading pendant les annonces, maintien des positions le
  week-end, perte journalière maximale, drawdown maximal, mode de calcul (balance ou equity).
- Réglez l'EA **sous** leurs limites : par exemple `InpDailyLossLimitPct` = 3 si leur limite est 5 %,
  et un risque par trade réduit (`InpRiskPct` = 0,5) tant que le drawdown historique n'est pas compatible
  avec leur drawdown maximal.
- Faites d'abord tourner l'EA sur leur compte d'essai gratuit, s'ils en proposent un.

## 5. Ce que je peux faire de votre côté de test

Envoyez-moi : le rapport du testeur (clic droit dans l'onglet *Backtest* → *Rapport* → HTML), les fichiers
CSV du dossier `Common\Files\SensitorAI\` et l'onglet *Journal* en cas d'erreur. Je vérifie l'exécution
trade par trade et la concordance avec la recherche.
