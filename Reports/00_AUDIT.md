# Phase 0 — Audit de l'environnement et du dépôt

Date : 2026-10-24. Environnement : conteneur Linux (Ubuntu 24.04, 4 vCPU, 15 Go RAM), session Claude Code.

## 1. Dépôt

| Constat | Détail |
|---|---|
| État initial | Dépôt `Sensitor/SensitorAI` **vide** (aucun commit, aucun fichier). |
| Conventions existantes | Aucune : l'arborescence proposée dans le cahier des charges a été adoptée, avec `MQL5/` reproduisant l'arborescence d'un dossier de données MT5 (`Experts/`, `Include/`, `Scripts/`, `Presets/`). |
| Branche | `claude/sensitor-ai-trading-system-l1ahmr`. |

## 2. Outils disponibles

| Outil | Disponible ? | Remarque |
|---|---|---|
| MetaTrader 5 / MetaEditor | **Non** au départ → **installé** | MT5 build 6283 téléchargé depuis `download.mql5.com`, exécuté sous **Wine 11.0** (WineHQ) + Xvfb. Wine 9.0 (Ubuntu) déclenchait la protection anti-débogueur de MT5. |
| Compilateur MQL5 officiel | **Oui** (via MetaEditor64 `/compile`) | Compilation réelle, logs dans `Reports/compile/`. |
| Exécution de scripts MQL5 | **Oui** | Terminal lancé en mode portable avec un fichier `[StartUp]` ; le script de tests écrit son résultat dans `Common\Files`. |
| Strategy Tester MT5 | **Non utilisable** | « tester not started because the account is not specified » : un compte (démo) est requis. Aucun compte n'a été ouvert (inscription auprès d'un tiers avec données personnelles = décision de l'utilisateur). |
| Python | 3.13, numpy 2.5, pandas 3.0 ; installés : pytest, pyarrow, scipy, matplotlib, tabulate | Pas de scikit-learn / LightGBM (non nécessaires avant la phase 9). |
| Réseau | Sortant ouvert via proxy | Téléchargements Dukascopy limités en débit (~1 fichier/s). |

## 3. Données historiques

| Source | Statut |
|---|---|
| Données dans le dépôt | Aucune. |
| **Dukascopy** (bougies M1 Bid **et** Ask, XAUUSD) | Accessible. Téléchargement reproductible : `Research/scripts/download_dukascopy.py` (2018-01 → 2026-09, ≈ 5 500 fichiers journaliers). Le spread réel minute par minute est disponible. |
| Yahoo / autres | Limités (HTTP 429) ou de moindre qualité (contrats à terme, données journalières). |
| Ticks réels du broker | **Non disponibles** : nécessitent un compte chez le broker final. |

Limites : Dukascopy n'est pas le broker d'exécution final (spreads, horaires, fuseau, barres H4,
qualité des ticks). Les résultats de recherche devront être revalidés sur les ticks réels du broker.

## 4. Ce qui peut être compilé / testé ici

| Élément | Possible ? |
|---|---|
| Compilation de l'EA et des scripts MQL5 | Oui (fait) |
| Tests unitaires MQL5 (moteur, zones, risque, parité avec Python) | Oui, exécutés dans le terminal MT5 |
| Tests unitaires Python | Oui |
| Backtests de recherche (Python, M1 Bid/Ask) | Oui |
| Backtest de l'EA dans le Strategy Tester | Non (compte requis) — procédure et outils fournis |
| Test en démo / réel | Non (compte, VPS, broker requis) — procédure fournie |

## 5. Plan de travail retenu

1. Spécification formelle (`Docs/SPECIFICATION.md`) séparant règles [U], hypothèses [H], paramètres [C].
2. Référence exécutable en Python (moteur de structure/signaux + simulateur Bid/Ask M1) + tests unitaires.
3. Portage 1:1 en MQL5, compilation réelle, tests MQL5 + parité champ par champ avec Python.
4. Plan d'expérience pré-enregistré, puis backtests DEV → VAL → TEST (test final exécuté une seule fois).
5. Documentation d'installation, VPS, démo, checklist réel, limites.
