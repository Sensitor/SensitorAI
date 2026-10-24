# Sensitor AI

Système de trading algorithmique pour **XAU/USD sur MetaTrader 5** : biais de structure H4/H1, BOS de
confirmation en M15/M5, entrée par **ordre limite dans l'intersection Order Block ∩ OTE (62–79 %)**
avec FVG, filtre d'exclusion RSI, risque nominal 1 %, break-even à +1R, 50 % à +3R et quatre méthodes
de gestion du runner.

> **Statut : version de validation (v0.1.0). Aucune rentabilité n'est supposée.** Lire
> `Reports/07_FINAL_SUMMARY.md` avant toute utilisation. Démo uniquement tant que
> `Docs/LIVE_CHECKLIST.md` n'est pas entièrement validée.

## Arborescence

```
MQL5/
  Experts/SensitorAI/SensitorAI.mq5      Expert Advisor (orchestration, inputs documentés)
  Include/SensitorAI/                    Modules : Types, Config, Indicators, Zones, StructureEngine,
                                         SignalEngine, MarketData, RiskManager, ExecutionManager,
                                         PositionManager, TradeLogger, StateStore, NewsFilter, Dashboard
  Include/SensitorAI/Tests/Fixtures.mqh  Fixtures de parité générées depuis la référence Python
  Scripts/SensitorAI/SensitorTests.mq5   Tests unitaires + parité MQL5 (90 vérifications)
  Scripts/SensitorAI/ImportCustomSymbol.mq5  Symbole personnalisé à partir des données de recherche
  Presets/*.set                          Presets démo / dry-run / runners A-D / testeur
Research/
  sensitor/                              Référence Python : structure, zones, setups, simulateur
                                         Bid/Ask M1, risque, portefeuille, métriques, pipeline
  scripts/                               Téléchargement des données, expériences, export MT5,
                                         analyse des journaux de l'EA, fixtures, filtre IA (verrouillé)
  EXPERIMENT_PLAN.md                     Plan d'expérience pré-enregistré
Tests/python/                            91 tests unitaires (pytest)
Tools/                                   Compilation MetaEditor, exécution des tests MQL5, watchdog VPS
Docs/                                    Spécification, hypothèses, machine à états, installation,
                                         VPS, démo, checklist réel, limites, changelog
Reports/                                 Audit, compilation, tests, backtests, comparaison des runners,
                                         validation, test final, bilan
```

## Démarrage rapide

```bash
# tests Python
pip install numpy pandas pyarrow pytest tabulate
python3 -m pytest Tests/python -q

# données (Dukascopy M1 Bid/Ask, ~5 500 fichiers) puis expériences
python3 Research/scripts/download_dukascopy.py --start 2018-01-01 --end 2026-10-01
python3 Research/scripts/run_research.py dev     # puis val, puis test (une seule fois)

# MQL5 (Windows : MetaEditor ; Linux : Wine 10+)
Tools/compile_mql5.sh && Tools/run_mql5_tests.sh
```

Installation sur MT5 : `Docs/INSTALL_MT5.md`. Stratégie implémentée : `Docs/SPECIFICATION.md`.

## Principes

- Règles de l'utilisateur [U], hypothèses de développement [H] et paramètres à confirmer [C] sont
  séparés partout (`Docs/ASSUMPTIONS.md`).
- Le moteur MQL5 est un portage 1:1 de la référence Python ; la parité est vérifiée champ par champ
  dans le terminal MT5.
- Aucune décision n'utilise une bougie non clôturée ; absence de lookahead testée par troncature.
- Aucun appel d'IA dans le chemin d'exécution ; pas de martingale ni d'augmentation du risque.
- Un ordre n'est jamais supposé exécuté : retcodes, relecture serveur, transactions.
