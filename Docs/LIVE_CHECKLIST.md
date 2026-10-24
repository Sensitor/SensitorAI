# Checklist avant tout passage en réel

Chaque case doit être cochée **avec une preuve** (fichier, rapport, capture). Une seule case non cochée
⇒ pas de passage en réel.

## A. Preuve statistique
- [ ] Espérance nette > 0 sur la période de validation **et** sur le test final jamais utilisé pour régler.
- [ ] Profit factor net > 1,1 sur ces deux périodes, avec un nombre de trades suffisant (≥ 100 au total).
- [ ] Résultat positif sous le scénario de coûts « stress » (spread + 0,20 $, slippage ×3, swaps ×2).
- [ ] Pas de dépendance à quelques trades exceptionnels (espérance hors meilleur trade > 0).
- [ ] Nombre de variantes testées documenté ; résultat au-delà du seuil « hasard » des comparaisons multiples.
- [ ] Revalidation sur les **ticks réels du broker** (Strategy Tester, « Chaque tick basé sur les ticks réels »).
- [ ] Drawdown maximal historique accepté par écrit par l'utilisateur (et doublé pour la marge de sécurité).

## B. Exécution
- [ ] Démo ≥ 4 semaines sans anomalie (`Docs/DEMO_PROCEDURE.md`), tous les tests d'incident réussis.
- [ ] Slippage et spreads observés en démo compatibles avec les hypothèses de coûts.
- [ ] Spécifications du symbole du compte réel identiques à celles de la démo (contrat, tick, volumes, commission).
- [ ] Tests MQL5 90/90 sur le terminal réel.

## C. Risque
- [ ] `InpRiskPct` ≤ 1 ; envisager 0,25–0,5 % pour la première période réelle.
- [ ] Limite de perte journalière, nombre de positions et risque total validés.
- [ ] Le capital engagé est un capital dont la perte est supportable.
- [ ] Filtre d'annonces : décision explicite (activé ou non) et testée en démo.

## D. Exploitation
- [ ] VPS opérationnel, démarrage automatique, surveillance du battement de cœur, alertes.
- [ ] Procédure d'arrêt d'urgence connue (désactiver le trading algorithmique, supprimer l'EA, clôturer à la main).
- [ ] Sauvegarde des journaux et du fichier d'état.
- [ ] Revue hebdomadaire planifiée des journaux et des écarts avec la recherche.
