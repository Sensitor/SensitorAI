# Journal des modifications de la stratégie et du code

Toute modification de la stratégie implémentée est consignée ici (date, nature, raison, impact).

## v0.1.0 — 2026-10-24 — première version

- Création de la spécification formelle, de la référence Python, de l'EA MQL5 et des tests.
- Décision en cours de développement (avant tout backtest) : un FVG entièrement comblé à la confirmation
  du setup **n'est plus** un motif de rejet (seule une clôture au-delà de son bord distal l'invalide).
  Raison : pour un achat l'OB se situe sous le FVG ; le retracement vers l'OB comble mécaniquement le
  FVG, et le moment de la confirmation (fin du swing) est arbitraire. Hypothèse H10.
- Arrondi des prix d'entrée aligné sur `MathRound` (demi vers le haut) dans la référence Python pour
  garantir la parité exacte EA/recherche (Python `round()` arrondit les égalités au pair).
- Champs non calculés d'un setup = `EMPTY_VALUE` en MQL5 (équivalent du `NaN` Python).

## v0.2.0 — 2026-10-24 — retour de l'utilisateur

- Confirmé par l'utilisateur : BOS = clôture du corps au-delà du swing ; OTE 62–79 %.
- **Règle [U]** : l'Order Block crée le FVG immédiatement (bougie OB = 1ʳᵉ bougie du FVG).
  `ObMaxDistBars` passe de 5 (hypothèse) à 0 (règle) dans Python, MQL5 et tous les presets.
- Évaluation : cycle 2 pré-enregistré dans `Research/EXPERIMENT_PLAN.md`, rapport `Reports/09_CYCLE2_OB_RULE.md`.
