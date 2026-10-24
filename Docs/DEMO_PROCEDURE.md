# Procédure de lancement en démo

Objectif : valider **l'exécution technique** (cohérence signaux/ordres, gestion, incidents), pas la
rentabilité — une démo de quelques semaines ne contient pas assez de trades pour cela.

## Étape 0 — Prérequis
- [ ] Tests MQL5 90/90 sur le terminal du broker.
- [ ] Compte démo du **même broker et même type de compte** (hedging/netting, commission) que le futur réel.
- [ ] Ligne `INIT` (spécifications du symbole) vérifiée.

## Étape 1 — Dry-run (1 semaine)
Preset `SensitorAI_demo.set` avec `InpDryRun=true`.
- [ ] Les setups apparaissent dans `setups.csv` ; les décisions de rejet sont lisibles dans `decisions.csv`.
- [ ] Comparer quelques setups avec une lecture manuelle du graphique (zones dessinées : OTE bleu,
      OB vert/rouge, FVG doré, entrée blanche, SL rouge).
- [ ] Comparer avec la référence Python sur les mêmes barres (export du broker → `run_research`), si souhaité.

## Étape 2 — Démo réelle (≥ 4 semaines, `InpDryRun=false`)
Vérifier pour chaque trade dans `events.csv` / `orders.csv` / `trades.csv` :
- [ ] Ordre limite au prix et au SL prévus (`setups.csv`), volume ≤ risque 1 % (`risk_nominal_money`).
- [ ] Aucun doublon d'ordre pour un même `setup_id`.
- [ ] Annulations avec raison (`INV_*`), aucune entrée au marché de rattrapage.
- [ ] BE déclenché à +1R, au prix réel d'entrée, confirmé par le serveur.
- [ ] Partielle exécutée **une seule fois** à +3R, volume correct.
- [ ] Méthode de runner conforme au paramètre.
- [ ] TP ajusté au prix d'exécution réel (méthodes B/C).

## Étape 3 — Tests d'incident (en démo, marché ouvert)
- [ ] Fermer le terminal avec un ordre en attente → relancer : ordre rattaché, pas de doublon.
- [ ] Fermer le terminal avec une position ouverte → relancer : 1R, BE, partielle reconstruits (`RESTORE` dans `events.csv`).
- [ ] Couper le réseau 10 minutes → reconnexion sans erreur ni doublon.
- [ ] Supprimer manuellement un ordre de l'EA → l'EA le constate (`INVALIDATED`, « removed outside the EA »).
- [ ] Retirer manuellement le SL d'une position → l'EA le restaure.
- [ ] Changer d'UT du graphique / recharger l'EA → état conservé.
- [ ] Simuler `ERROR_SAFE` (ex. `InpMaxConsecErrors=1` et un symbole fermé) → plus d'entrée, gestion maintenue.
- [ ] Vérifier la suspension journalière (abaisser `InpDailyLossLimitPct` temporairement).

## Étape 4 — Bilan
Rédiger un rapport (écarts signal/ordre, slippage observé, spreads, erreurs serveur, incidents) avant
toute discussion d'un passage en réel. **L'EA ne passe jamais seul en réel.**
