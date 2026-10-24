# Rapport de compilation (Phase 4)

| Élément | Valeur |
|---|---|
| Compilateur | MetaEditor64 (MetaTrader 5 **build 6283**), compilateur MQL5 officiel, `cpu='X64 Regular'` |
| Plateforme | Linux + Wine 11.0 (WineHQ) + Xvfb, mode portable |
| Commande | `Tools/compile_mql5.sh` (copie `MQL5/` dans le dossier de données puis `MetaEditor64.exe /portable /compile:<fichier> /log:<log>`) |
| Logs complets | `Reports/compile/*.log` |
| Version du code | voir `git log` (rapport régénéré à chaque compilation) |

## Résultats

| Fichier | Erreurs | Avertissements | Remarque |
|---|---|---|---|
| `Experts/SensitorAI/SensitorAI.mq5` (+ 13 `.mqh`) | **0** | 1 | Avertissement 68 : format de `#property version` exigé uniquement pour la publication sur le MQL5 Market. Sans effet sur l'exécution. |
| `Scripts/SensitorAI/SensitorTests.mq5` | **0** | 0 | Tests unitaires + parité |
| `Scripts/SensitorAI/ImportCustomSymbol.mq5` | **0** | 0 | Import des données de recherche en symbole personnalisé |

Avertissements corrigés au cours du développement : variables `ob`/`zone` potentiellement non
initialisées dans `SignalEngine.mqh` (initialisation explicite ajoutée).

## Vérifications effectuées sur les appels de trading (revue de code)

| Point | Implémentation |
|---|---|
| Volume | `OrderCalcProfit` (perte par lot au SL dans la devise du compte), arrondi **vers le bas** au pas, refus si < volume min, plafonds `VOLUME_MAX`/`VOLUME_LIMIT`, `OrderCalcMargin` (≤ 90 % de la marge libre) |
| Prix | normalisation au `TRADE_TICK_SIZE` ; ordre limite refusé s'il serait marketable (jamais de poursuite du prix) ; distance minimale `STOPS_LEVEL` pour l'entrée, le SL et le TP |
| Pré-validation | `OrderCheck` avant `OrderSend`, avec essai des modes de remplissage autorisés (`RETURN`, `FOK`, `IOC`) |
| Expiration | `GTC` si autorisé, sinon `DAY` avec ré-envoi contrôlé si le setup reste valide |
| Résultat | retcode classé (succès / transitoire / incertain / définitif) ; relecture de l'ordre ou de la position ; recherche par commentaire en cas de `TIMEOUT`/`CONNECTION` |
| Modification de SL | respect de `STOPS_LEVEL` et `FREEZE_LEVEL` ; jamais d'élargissement du risque (`TighterSL`) ; relecture du SL chez le serveur |
| Clôture partielle | volume valide garanti (`PartialCloseVolume`), vérification par baisse du volume de la position ; une seule exécution (drapeau persisté + déduction depuis le volume) |
| Netting / hedging | détecté via `ACCOUNT_MARGIN_MODE` ; en netting, une seule position/ordre à la fois |

## Ce qui n'a PAS pu être vérifié ici

- Exécution réelle des ordres contre un serveur de trading (Strategy Tester ou démo) : un compte est
  nécessaire. Le comportement d'`OrderCheck`/`OrderSend` face à un vrai serveur (modes de remplissage,
  expiration, niveaux de gel) reste à valider en démo (`Docs/DEMO_PROCEDURE.md`).
